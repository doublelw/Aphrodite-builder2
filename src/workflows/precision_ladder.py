"""
Multi-precision escalation pipeline.

Molecules pass through increasingly accurate (and expensive) calculations:
    GFN-xTB (seconds) -> r2SCAN-3c (hours) -> DLPNO-CCSD(T) (days)

Only molecules passing thresholds at each tier advance to the next.
This filters out unpromising candidates early, saving 90%+ compute.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Callable

from ..quantum.precision_manager import PrecisionManager, PipelineStage
from ..core.property_predictor import BatteryProperties


@dataclass
class TierResult:
    molecule_name: str
    tier: str
    passed: bool
    properties: Dict[str, float] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    walltime_seconds: float = 0.0


@dataclass
class TierThreshold:
    metric: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None


# Default thresholds calibrated against known organic battery materials
DEFAULT_THRESHOLDS = {
    'xtb': [
        TierThreshold('gap', min_val=1.0, max_val=6.0),
        TierThreshold('homo', max_val=-3.0),
    ],
    'dft': [
        TierThreshold('gap', min_val=1.5, max_val=5.0),
        TierThreshold('homo', min_val=-6.5, max_val=-3.5),
        TierThreshold('lumo', min_val=-3.0, max_val=-0.5),
    ],
    'dlpno': [
        TierThreshold('gap', min_val=1.5, max_val=4.5),
        TierThreshold('voltage', min_val=2.0, max_val=4.5),
    ],
}


class PrecisionLadder:
    """
    Multi-tier precision escalation pipeline.

    Usage:
        ladder = PrecisionLadder(workdir='./precision_run')
        results = ladder.escalate(
            molecules={'mol_a': xyz_string_a, 'mol_b': xyz_string_b},
            targets=[TierThreshold('voltage', min_val=3.0)]
        )
    """

    TIERS = ['xtb', 'dft', 'dlpno']

    def __init__(self, workdir: str = './precision_run',
                 thresholds: Dict[str, List[TierThreshold]] = None):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.precision_mgr = PrecisionManager()

    def _check_thresholds(self, properties: Dict[str, float],
                          tier: str) -> tuple:
        """Check if molecule properties pass tier thresholds."""
        thresholds = self.thresholds.get(tier, [])
        for th in thresholds:
            val = properties.get(th.metric)
            if val is None:
                continue
            if th.min_val is not None and val < th.min_val:
                return False, f"{th.metric}={val:.3f} < {th.min_val}"
            if th.max_val is not None and val > th.max_val:
                return False, f"{th.metric}={val:.3f} > {th.max_val}"
        return True, None

    def _run_xtb(self, xyz: str, name: str) -> Dict[str, float]:
        """Run GFN-xTB for rapid screening."""
        import subprocess, tempfile, os

        mol_dir = self.workdir / 'xtb' / name
        mol_dir.mkdir(parents=True, exist_ok=True)
        xyz_file = mol_dir / f"{name}.xyz"
        xyz_file.write_text(xyz)

        try:
            result = subprocess.run(
                ['xtb', str(xyz_file), '--gfn', '2', '--vtb', '--esp'],
                capture_output=True, text=True,
                cwd=str(mol_dir), timeout=120
            )
            output = result.stdout
            props = {}
            for line in output.split('\n'):
                if 'HOMO' in line and 'eV' in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        try:
                            props['homo'] = float(p)
                            break
                        except ValueError:
                            continue
                if 'LUMO' in line and 'eV' in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        try:
                            props['lumo'] = float(p)
                            break
                        except ValueError:
                            continue
            if 'homo' in props and 'lumo' in props:
                props['gap'] = props['lumo'] - props['homo']
            props['success'] = True
            return props
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _run_dft(self, xyz: str, name: str) -> Dict[str, float]:
        """Run DFT (r2SCAN-3c/def2-SVP) for accurate screening."""
        from ..quantum.orca_input_generator import ORCAInputGenerator, ORCAConfig
        from ..quantum.result_extractor import ResultExtractor
        import subprocess

        mol_dir = self.workdir / 'dft' / name
        mol_dir.mkdir(parents=True, exist_ok=True)

        config = ORCAConfig(
            method='r2SCAN-3c', basis='def2-SVP',
            charge=0, multiplicity=1,
            solvent='CPCM(water)', nproc=4, maxcore=4000,
        )
        gen = ORCAInputGenerator(config)
        inp_path = mol_dir / f"{name}.inp"
        gen.write_input(xyz, str(inp_path))

        try:
            subprocess.run(
                ['orca', str(inp_path)],
                capture_output=True, text=True,
                cwd=str(mol_dir), timeout=7200
            )
            out_path = mol_dir / f"{name}.out"
            if out_path.exists():
                extractor = ResultExtractor()
                return extractor.extract(str(out_path))
            return {'success': False, 'error': 'No output'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _run_dlpno(self, xyz: str, name: str) -> Dict[str, float]:
        """Run DLPNO-CCSD(T) for production-grade validation."""
        from ..quantum.orca_input_generator import ORCAInputGenerator, ORCAConfig
        from ..quantum.result_extractor import ResultExtractor
        import subprocess

        mol_dir = self.workdir / 'dlpno' / name
        mol_dir.mkdir(parents=True, exist_ok=True)

        config = ORCAConfig(
            method='DLPNO-CCSD(T)', basis='def2-TZVPP',
            charge=0, multiplicity=1,
            solvent='CPCM(water)', nproc=8, maxcore=6000,
            aux_basis='def2/J def2-TZVPP/C',
        )
        gen = ORCAInputGenerator(config)
        inp_path = mol_dir / f"{name}.inp"
        gen.write_input(xyz, str(inp_path))

        try:
            subprocess.run(
                ['orca', str(inp_path)],
                capture_output=True, text=True,
                cwd=str(mol_dir), timeout=86400
            )
            out_path = mol_dir / f"{name}.out"
            if out_path.exists():
                extractor = ResultExtractor()
                return extractor.extract(str(out_path))
            return {'success': False, 'error': 'No output'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    TIER_RUNNERS = {
        'xtb': '_run_xtb',
        'dft': '_run_dft',
        'dlpno': '_run_dlpno',
    }

    def escalate(self, molecules: Dict[str, str],
                 target_tier: str = 'dlpno') -> Dict[str, List[TierResult]]:
        """
        Run multi-tier precision escalation.

        Args:
            molecules: {name: xyz_string} dict
            target_tier: highest tier to reach ('xtb', 'dft', 'dlpno')

        Returns:
            {name: [TierResult, ...]} for each molecule
        """
        target_idx = self.TIERS.index(target_tier)
        all_results = {}
        candidates = dict(molecules)

        for tier_idx, tier in enumerate(self.TIERS[:target_idx + 1]):
            if not candidates:
                break

            survivors = {}
            for name, xyz in candidates.items():
                runner = getattr(self, self.TIER_RUNNERS[tier])
                props = runner(xyz, name)

                success = props.pop('success', False)
                if not success:
                    tr = TierResult(
                        molecule_name=name, tier=tier, passed=False,
                        rejection_reason=props.get('error', 'Calculation failed'),
                    )
                    all_results.setdefault(name, []).append(tr)
                    continue

                passed, reason = self._check_thresholds(props, tier)
                tr = TierResult(
                    molecule_name=name, tier=tier, passed=passed,
                    properties=props,
                    rejection_reason=reason,
                )
                all_results.setdefault(name, []).append(tr)

                if passed:
                    survivors[name] = xyz

            candidates = survivors

        self._save_report(all_results)
        return all_results

    def _save_report(self, results: Dict[str, List[TierResult]]):
        """Save escalation report."""
        lines = ["=" * 60, "PRECISION LADDER REPORT", "=" * 60, ""]

        for tier in self.TIERS:
            tier_results = [
                (name, tr) for name, trs in results.items()
                for tr in trs if tr.tier == tier
            ]
            passed = sum(1 for _, tr in tier_results if tr.passed)
            total = len(tier_results)
            lines.append(f"  {tier.upper()}: {passed}/{total} passed")
            for name, tr in tier_results:
                status = "PASS" if tr.passed else "FAIL"
                reason = f" ({tr.rejection_reason})" if tr.rejection_reason else ""
                lines.append(f"    [{status}] {name}{reason}")
            lines.append("")

        report = "\n".join(lines)
        (self.workdir / "precision_report.txt").write_text(report)
