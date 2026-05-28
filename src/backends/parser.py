"""
Output parser using cclib.

Reads quantum chemistry output from ORCA, Gaussian, PySCF, Psi4, etc.
Extracts energies, orbitals, frequencies, excited states, and more.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class ParsedOutput:
    """Structured data from quantum chemistry output."""
    source: str = ""
    energy: float = 0.0
    homo: float = 0.0
    lumo: float = 0.0
    gap: float = 0.0
    dipole: List[float] = field(default_factory=list)
    frequencies: List[float] = field(default_factory=list)
    vib_displacement: List[List[float]] = field(default_factory=list)
    excited_states: List[Dict] = field(default_factory=list)
    atomic_charges: Dict[str, List[float]] = field(default_factory=dict)
    mo_energies: List[List[float]] = field(default_factory=list)
    scf_energies: List[float] = field(default_factory=list)
    scf_converged: bool = False
    geoopt_converged: bool = False
    metadata: Dict = field(default_factory=dict)


class OutputParser:
    """
    Parse quantum chemistry output using cclib.

    Supports: ORCA, Gaussian, Psi4, Q-Chem, Molpro, ADF, etc.

    Usage:
        parser = OutputParser()
        result = parser.parse("calculation.out")
    """

    def parse(self, filepath: str) -> ParsedOutput:
        """Parse a quantum chemistry output file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Output file not found: {filepath}")

        try:
            import cclib
            data = cclib.io.ccread(str(path))
        except ImportError:
            return self._parse_manual(filepath)
        except Exception:
            return self._parse_manual(filepath)

        result = ParsedOutput(source=str(path))

        if hasattr(data, 'scfenergies') and data.scfenergies is not None:
            result.energy = float(data.scfenergies[-1])
            result.scf_energies = data.scfenergies.tolist()
            result.scf_converged = True

        if hasattr(data, 'moenergies') and data.moenergies is not None:
            result.mo_energies = [e.tolist() for e in data.moenergies]
            if len(data.moenergies) > 0:
                energies = data.moenergies[0]
                n_alpha = data.homos[0] + 1 if data.homos is not None else 0
                result.homo = float(energies[n_alpha - 1])
                result.lumo = float(energies[n_alpha]) if n_alpha < len(energies) else 0.0
                result.gap = result.lumo - result.homo

        if hasattr(data, 'moments') and data.moments is not None:
            if len(data.moments) > 1:
                result.dipole = data.moments[1].tolist()

        if hasattr(data, 'vibfreqs') and data.vibfreqs is not None:
            result.frequencies = data.vibfreqs.tolist()

        if hasattr(data, 'etenergies') and data.etenergies is not None:
            result.excited_states = [
                {
                    "energy_cm": float(data.etenergies[i]),
                    "osc_strength": float(data.etoscs[i]) if data.etoscs is not None else 0.0,
                }
                for i in range(len(data.etenergies))
            ]

        if hasattr(data, 'atomcharges') and data.atomcharges is not None:
            result.atomic_charges = {
                k: v.tolist() for k, v in data.atomcharges.items()
            }

        if hasattr(data, 'optdone') and data.optdone is not None:
            result.geoopt_converged = bool(data.optdone[-1])

        result.metadata = {
            "n_atoms": data.natom if hasattr(data, 'natom') else 0,
            "charge": data.charge if hasattr(data, 'charge') else 0,
            "multiplicity": data.mult if hasattr(data, 'mult') else 1,
        }

        return result

    def _parse_manual(self, filepath: str) -> ParsedOutput:
        """Fallback manual parser for ORCA output."""
        result = ParsedOutput(source=filepath)

        try:
            content = Path(filepath).read_text(errors='ignore')
        except Exception:
            return result

        result.scf_converged = 'ORCA TERMINATED NORMALLY' in content
        result.geoopt_converged = 'THE OPTIMIZATION HAS CONVERGED' in content

        # Parse HOMO/LUMO
        for line in content.split('\n'):
            if 'HOMO' in line and 'eV' in line and result.homo == 0.0:
                parts = line.split()
                for p in parts:
                    try:
                        val = float(p)
                        if -20 < val < 0:
                            result.homo = val
                            break
                    except ValueError:
                        continue
            if 'LUMO' in line and 'eV' in line and result.lumo == 0.0:
                parts = line.split()
                for p in parts:
                    try:
                        val = float(p)
                        if -5 < val < 5:
                            result.lumo = val
                            break
                    except ValueError:
                        continue

        if result.homo != 0.0 and result.lumo != 0.0:
            result.gap = result.lumo - result.homo

        return result

    def batch_parse(self, directory: str, pattern: str = "*.out") -> List[ParsedOutput]:
        """Parse all output files in a directory."""
        results = []
        for path in Path(directory).rglob(pattern):
            results.append(self.parse(str(path)))
        return results
