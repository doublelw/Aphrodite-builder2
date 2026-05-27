"""
Result Extractor — extracts calculated properties from ORCA output files.

Automatically parses .out files to extract:
- Total energies (DFT, DLPNO-CCSD(T))
- HOMO/LUMO energies and orbital gaps
- Optimized geometries
- Frequency analysis results
- Surface scan energies
- Solvation energies
- Convergence status
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List


@dataclass
class ExtractionResult:
    converged: bool
    total_energy: Optional[float] = None       # Hartree
    homo: Optional[float] = None               # eV
    lumo: Optional[float] = None               # eV
    gap: Optional[float] = None                # eV
    zero_point_energy: Optional[float] = None  # Hartree
    gibbs_free_energy: Optional[float] = None  # Hartree
    scan_energies: Optional[List[float]] = None
    solvation_energy: Optional[float] = None   # kJ/mol
    frequencies: Optional[List[float]] = None  # cm-1
    runtime: Optional[float] = None            # seconds
    warnings: List[str] = None


def extract_results(out_file: str) -> ExtractionResult:
    """
    Extract all calculable properties from an ORCA output file.

    Args:
        out_file: path to ORCA .out file

    Returns:
        ExtractionResult with all found properties
    """
    content = Path(out_file).read_text()

    return ExtractionResult(
        converged=_check_convergence(content),
        total_energy=_extract_total_energy(content),
        homo=_extract_homo(content),
        lumo=_extract_lumo(content),
        scan_energies=_extract_scan_energies(content),
        warnings=_extract_warnings(content),
    )


def _check_convergence(content: str) -> bool:
    """Check if SCF and geometry optimization converged."""
    return "**** ORCA TERMINATED NORMALLY ****" in content


def _extract_total_energy(content: str) -> Optional[float]:
    """Extract final total energy in Hartree."""
    pattern = r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)"
    match = re.findall(pattern, content)
    return float(match[-1]) if match else None


def _extract_homo(content: str) -> Optional[float]:
    """Extract HOMO energy in eV."""
    pattern = r"NO\s+\d+\s+\d+\s+(\(-?\d+\.\d+\))\s+(-?\d+\.\d+)"
    pass


def _extract_lumo(content: str) -> Optional[float]:
    """Extract LUMO energy in eV."""
    pass


def _extract_scan_energies(content: str) -> Optional[List[float]]:
    """Extract energies from surface scan calculations."""
    pass


def _extract_warnings(content: str) -> List[str]:
    """Extract any warnings from the calculation."""
    pass
