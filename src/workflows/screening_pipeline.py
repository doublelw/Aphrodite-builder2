"""
Full molecular screening pipeline.

Workflow: SMILES input -> 3D geometry -> quantum calculations ->
          property extraction -> multi-objective ranking -> report

Integrates: RDKit (geometry) + ORCA (quantum) + Multiwfn (analysis)
"""
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

from ..quantum.orca_input_generator import ORCAInputGenerator, ORCAConfig
from ..quantum.result_extractor import ResultExtractor
from ..core.property_predictor import BatteryProperties
from ..core.screening_engine import ScreeningEngine, ScreeningTarget


@dataclass
class ScreeningResult:
    smiles: str
    name: str
    properties: Optional[BatteryProperties] = None
    orca_success: bool = False
    errors: List[str] = field(default_factory=list)
    xyz_geometry: Optional[str] = None


class ScreeningPipeline:
    """
    End-to-end molecular screening workflow.

    Usage:
        pipeline = ScreeningPipeline(workdir='./screening_run')
        results = pipeline.run(molecules={'aniline': 'c1ccccc1N'})
        report = pipeline.generate_report(results)
    """

    def __init__(self, workdir: str = './screening_run',
                 method: str = 'r2SCAN-3c',
                 basis: str = 'def2-SVP',
                 solvent: str = 'CPCM(water)',
                 nproc: int = 4,
                 maxcore: int = 4000):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.method = method
        self.basis = basis
        self.solvent = solvent
        self.nproc = nproc
        self.maxcore = maxcore
        self.extractor = ResultExtractor()
        self.screening_engine = ScreeningEngine()

    def smiles_to_xyz(self, smiles: str, name: str = 'mol') -> Optional[str]:
        """Convert SMILES to 3D XYZ geometry using RDKit + MMFF optimization."""
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
        except ImportError:
            raise ImportError(
                "RDKit required. Install: conda install -c conda-forge rdkit"
            )

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        mol = Chem.AddHs(mol)
        result = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
        if result == -1:
            return None
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)

        conf = mol.GetConformer()
        n_atoms = mol.GetNumAtoms()
        xyz_lines = [f"{n_atoms}", name]
        for i in range(n_atoms):
            atom = mol.GetAtomWithIdx(i)
            pos = conf.GetAtomPosition(i)
            xyz_lines.append(
                f"{atom.GetSymbol()}  {pos.x:.6f}  {pos.y:.6f}  {pos.z:.6f}"
            )
        return "\n".join(xyz_lines)

    def run_orca(self, xyz: str, name: str) -> dict:
        """Run ORCA calculation and extract results."""
        mol_dir = self.workdir / name
        mol_dir.mkdir(exist_ok=True)

        config = ORCAConfig(
            method=self.method, basis=self.basis,
            charge=0, multiplicity=1,
            solvent=self.solvent,
            nproc=self.nproc, maxcore=self.maxcore,
        )
        gen = ORCAInputGenerator(config)
        inp_path = mol_dir / f"{name}.inp"
        gen.write_input(xyz, str(inp_path))

        out_path = mol_dir / f"{name}.out"
        try:
            subprocess.run(
                ['orca', str(inp_path)],
                capture_output=True, text=True,
                cwd=str(mol_dir), timeout=3600
            )
            if out_path.exists():
                return self.extractor.extract(str(out_path))
            return {'success': False, 'error': 'No output file'}
        except FileNotFoundError:
            return {'success': False, 'error': 'ORCA not in PATH'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run(self, molecules: Dict[str, str] = None,
            smiles_list: List[str] = None) -> List[ScreeningResult]:
        """Run full screening pipeline on a set of molecules."""
        if molecules is None and smiles_list is not None:
            molecules = {f"mol_{i}": s for i, s in enumerate(smiles_list)}
        elif molecules is None:
            raise ValueError("Provide either molecules or smiles_list")

        results = []
        for name, smiles in molecules.items():
            sr = ScreeningResult(smiles=smiles, name=name)

            xyz = self.smiles_to_xyz(smiles, name)
            if xyz is None:
                sr.errors.append("Geometry generation failed")
                results.append(sr)
                continue
            sr.xyz_geometry = xyz

            calc_result = self.run_orca(xyz, name)
            if calc_result.get('success', False):
                sr.orca_success = True
                sr.properties = BatteryProperties(
                    theoretical_voltage=calc_result.get('voltage', 0.0),
                    energy_density=calc_result.get('energy_density', 0.0),
                    homo=calc_result.get('homo', 0.0),
                    lumo=calc_result.get('lumo', 0.0),
                    gap=calc_result.get('gap', 0.0),
                    reorganization_energy=calc_result.get('lambda', 0.0),
                    thermal_stability=calc_result.get('thermal_decomp', 0.0),
                    flame_resistance=calc_result.get('flame_resist', 0.0),
                )
            else:
                sr.errors.append(calc_result.get('error', 'Unknown error'))

            results.append(sr)
        return results

    def generate_report(self, results: List[ScreeningResult],
                        targets: List[ScreeningTarget] = None) -> str:
        """Generate ranked screening report."""
        successful = [r for r in results if r.orca_success]
        failed = [r for r in results if not r.orca_success]

        lines = [
            "=" * 60,
            "APHRODITE MOLECULAR SCREENING REPORT",
            "=" * 60,
            f"Total candidates: {len(results)}",
            f"Successful: {len(successful)}",
            f"Failed: {len(failed)}", "",
        ]

        if targets and successful:
            props_list = [r.properties for r in successful]
            names = [r.name for r in successful]
            ranked = self.screening_engine.rank(props_list, targets, names)
            lines.append("RANKED CANDIDATES:")
            lines.append("-" * 40)
            for i, (name, score) in enumerate(ranked):
                r = next(x for x in successful if x.name == name)
                p = r.properties
                lines.append(f"  #{i+1} {name} (score: {score:.3f})")
                lines.append(
                    f"      V={p.theoretical_voltage:.2f}V  "
                    f"E={p.energy_density:.0f}Wh/kg  "
                    f"gap={p.gap:.2f}eV  "
                    f"lambda={p.reorganization_energy:.3f}eV"
                )
            lines.append("")

        if failed:
            lines.append("FAILED CALCULATIONS:")
            for r in failed:
                lines.append(f"  {r.name}: {', '.join(r.errors)}")

        report = "\n".join(lines)
        (self.workdir / "screening_report.txt").write_text(report)
        return report
