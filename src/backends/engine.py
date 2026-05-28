"""
Unified quantum chemistry backend.

Provides a single interface to multiple quantum chemistry engines:
  - PySCF (pure Python, DFT/MP2/CCSD)
  - ORCA (external binary, DFT/DLPNO-CCSD(T)/TD-DFT)
  - ASE (wraps any engine with unified API)
  - cclib (output parsing from any engine)

Auto-selects the best available backend for each calculation type.
"""
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from enum import Enum


class Backend(Enum):
    PYSCF = "pyscf"
    ORCA = "orca"
    ASE = "ase"


class CalcType(Enum):
    SINGLE_POINT = "sp"
    GEOMETRY_OPT = "opt"
    FREQUENCY = "freq"
    TD_DFT = "tdDft"
    DLPNO_CCSD_T = "dlpno"
    HESSIAN = "hessian"


@dataclass
class MoleculeSpec:
    """Molecular specification for quantum calculation."""
    charge: int = 0
    multiplicity: int = 1
    atoms: List[tuple] = field(default_factory=list)  # [(symbol, x, y, z), ...]
    smiles: str = ""
    name: str = "mol"

    def to_xyz(self) -> str:
        lines = [f"{len(self.atoms)}", self.name]
        for sym, x, y, z in self.atoms:
            lines.append(f"{sym}  {x:.6f}  {y:.6f}  {z:.6f}")
        return "\n".join(lines)

    def to_pyscf_format(self) -> str:
        lines = []
        for sym, x, y, z in self.atoms:
            lines.append(f"{sym}  {x:.6f}  {y:.6f}  {z:.6f}")
        return "\n".join(lines)


@dataclass
class CalcResult:
    """Unified calculation result."""
    success: bool = False
    energy_hartree: float = 0.0
    homo_eV: float = 0.0
    lumo_eV: float = 0.0
    gap_eV: float = 0.0
    dipole_debye: float = 0.0
    frequencies: List[float] = field(default_factory=list)
    excited_states: List[Dict] = field(default_factory=list)
    orbital_energies: List[float] = field(default_factory=list)
    mulliken_charges: List[float] = field(default_factory=list)
    raw_output: str = ""
    backend: str = ""
    method: str = ""
    basis: str = ""
    walltime_s: float = 0.0
    error: str = ""


@dataclass
class CalcConfig:
    """Calculation configuration."""
    method: str = "B3LYP"
    basis: str = "6-31G*"
    solvent: str = ""
    nproc: int = 4
    maxcore: int = 4000
    charge: int = 0
    multiplicity: int = 1
    convergence: str = "tight"
    max_iterations: int = 100


class QuantumEngine:
    """
    Unified quantum chemistry engine with multi-backend support.

    Usage:
        engine = QuantumEngine()
        result = engine.calculate(mol_spec, CalcType.SINGLE_POINT, config)
    """

    def __init__(self, preferred: Backend = None):
        self.preferred = preferred
        self._available = self._detect_backends()

    def _detect_backends(self) -> Dict[Backend, bool]:
        available = {}
        try:
            import pyscf
            available[Backend.PYSCF] = True
        except ImportError:
            available[Backend.PYSCF] = False

        try:
            import subprocess
            subprocess.run(['orca'], capture_output=True, timeout=5)
            available[Backend.ORCA] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            available[Backend.ORCA] = False

        try:
            import ase
            available[Backend.ASE] = True
        except ImportError:
            available[Backend.ASE] = False

        return available

    def available_backends(self) -> List[str]:
        return [b.value for b, ok in self._available.items() if ok]

    def _select_backend(self, calc_type: CalcType) -> Backend:
        if self.preferred and self._available.get(self.preferred):
            return self.preferred

        # High-accuracy methods require ORCA
        if calc_type == CalcType.DLPNO_CCSD_T:
            return Backend.ORCA

        # PySCF is fastest for routine calculations
        if self._available.get(Backend.PYSCF):
            return Backend.PYSCF

        if self._available.get(Backend.ORCA):
            return Backend.ORCA

        return Backend.ASE

    def calculate(self, mol: MoleculeSpec, calc_type: CalcType,
                  config: CalcConfig = None) -> CalcResult:
        """Run quantum calculation with auto-selected backend."""
        config = config or CalcConfig()
        backend = self._select_backend(calc_type)

        if not self._available.get(backend):
            return CalcResult(
                success=False,
                error=f"Backend {backend.value} not available. "
                      f"Install: pip install {backend.value}",
            )

        if backend == Backend.PYSCF:
            return self._run_pyscf(mol, calc_type, config)
        elif backend == Backend.ORCA:
            return self._run_orca(mol, calc_type, config)
        elif backend == Backend.ASE:
            return self._run_ase(mol, calc_type, config)

        return CalcResult(success=False, error="No backend available")

    def _run_pyscf(self, mol: MoleculeSpec, calc_type: CalcType,
                   config: CalcConfig) -> CalcResult:
        """Run calculation using PySCF."""
        try:
            from pyscf import gto, dft, scf
        except ImportError:
            return CalcResult(success=False, error="PySCF not installed")

        import time
        t0 = time.time()

        try:
            pyscf_mol = gto.M(
                atom=mol.to_pyscf_format(),
                basis=config.basis,
                charge=config.charge,
                spin=config.multiplicity - 1,
                verbose=0,
            )

            if config.multiplicity == 1:
                mf = dft.RKS(pyscf_mol)
            else:
                mf = dft.UKS(pyscf_mol)

            mf.xc = config.method.lower()

            if config.solvent:
                mf = mf.ddCOSMO()

            energy = mf.kernel()

            # Extract orbital energies
            mo_energy = mf.mo_energy
            n_occ = pyscf_mol.nelectron // 2

            homo = -mo_energy[n_occ - 1] * 27.2114  # Ha to eV
            lumo = -mo_energy[n_occ] * 27.2114 if n_occ < len(mo_energy) else 0.0

            result = CalcResult(
                success=True,
                energy_hartree=energy,
                homo_eV=homo,
                lumo_eV=lumo,
                gap_eV=lumo - homo,
                orbital_energies=(-mo_energy * 27.2114).tolist(),
                dipole_debye=mf.dip_moment()[0] if hasattr(mf, 'dip_moment') else 0.0,
                backend="pyscf",
                method=config.method,
                basis=config.basis,
                walltime_s=time.time() - t0,
            )

            # Frequency calculation
            if calc_type == CalcType.FREQUENCY:
                from pyscf import hessian
                h = mf.Hessian()
                freq = h.kernel()
                result.frequencies = freq

            # TD-DFT for excited states
            if calc_type == CalcType.TD_DFT:
                from pyscf import tdscf
                td = tdscf.TDA(mf)
                td.nstates = 10
                td.kernel()
                result.excited_states = [
                    {"energy_eV": e * 27.2114, "oscillator_strength": f}
                    for e, f in zip(td.e, td.oscillator_strength())
                ]

            return result

        except Exception as e:
            return CalcResult(
                success=False,
                error=str(e),
                backend="pyscf",
                walltime_s=time.time() - t0,
            )

    def _run_orca(self, mol: MoleculeSpec, calc_type: CalcType,
                  config: CalcConfig) -> CalcResult:
        """Run calculation using ORCA."""
        from ..quantum.orca_input_generator import ORCAInputGenerator, ORCAConfig
        from ..quantum.result_extractor import ResultExtractor
        import subprocess, tempfile, time

        t0 = time.time()

        method_map = {
            CalcType.SINGLE_POINT: config.method,
            CalcType.GEOMETRY_OPT: f"! {config.method} Opt",
            CalcType.FREQUENCY: f"! {config.method} NumFreq",
            CalcType.TD_DFT: f"! {config.method} TD(NStates=10)",
            CalcType.DLPNO_CCSD_T: "DLPNO-CCSD(T)",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            orca_config = ORCAConfig(
                method=method_map.get(calc_type, config.method),
                basis=config.basis,
                charge=config.charge,
                multiplicity=config.multiplicity,
                solvent=f"CPCM({config.solvent})" if config.solvent else "",
                nproc=config.nproc,
                maxcore=config.maxcore,
            )

            gen = ORCAInputGenerator(orca_config)
            inp_path = f"{tmpdir}/mol.inp"
            gen.write_input(mol.to_xyz(), inp_path)

            try:
                subprocess.run(
                    ['orca', inp_path],
                    capture_output=True, text=True,
                    cwd=tmpdir, timeout=86400,
                )

                out_path = f"{tmpdir}/mol.out"
                if not Path(out_path).exists():
                    return CalcResult(
                        success=False, error="No ORCA output",
                        backend="orca", walltime_s=time.time() - t0,
                    )

                extractor = ResultExtractor()
                raw = extractor.extract(out_path)

                return CalcResult(
                    success=raw.get('success', False),
                    energy_hartree=raw.get('total_energy', 0.0),
                    homo_eV=raw.get('homo', 0.0),
                    lumo_eV=raw.get('lumo', 0.0),
                    gap_eV=raw.get('gap', 0.0),
                    backend="orca",
                    method=config.method,
                    basis=config.basis,
                    walltime_s=time.time() - t0,
                )

            except FileNotFoundError:
                return CalcResult(
                    success=False, error="ORCA not in PATH",
                    backend="orca", walltime_s=time.time() - t0,
                )
            except Exception as e:
                return CalcResult(
                    success=False, error=str(e),
                    backend="orca", walltime_s=time.time() - t0,
                )

    def _run_ase(self, mol: MoleculeSpec, calc_type: CalcType,
                 config: CalcConfig) -> CalcResult:
        """Run calculation using ASE as wrapper."""
        try:
            from ase import Atoms
            from ase.calculators.pyscf import PySCF
        except ImportError:
            return CalcResult(success=False, error="ASE not installed")

        import time
        t0 = time.time()

        try:
            symbols = [a[0] for a in mol.atoms]
            positions = [[a[1], a[2], a[3]] for a in mol.atoms]
            atoms = Atoms(symbols=symbols, positions=positions)

            calc = PySCF(
                basis=config.basis,
                xc=config.method,
            )
            atoms.calc = calc

            energy = atoms.get_potential_energy()

            return CalcResult(
                success=True,
                energy_hartree=energy / 27.2114,
                backend="ase",
                method=config.method,
                basis=config.basis,
                walltime_s=time.time() - t0,
            )

        except Exception as e:
            return CalcResult(
                success=False, error=str(e),
                backend="ase", walltime_s=time.time() - t0,
            )


from pathlib import Path
