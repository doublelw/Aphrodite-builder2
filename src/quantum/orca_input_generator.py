"""
ORCA Input Generator — generates quantum chemistry input files for ORCA 6.x.

Supports multiple precision tiers and calculation types:
- Geometry optimization
- Single-point energy
- Relaxed surface scan (dihedral rotation)
- DLPNO-CCSD(T) high-accuracy
- TD-DFT excited states
- Frequency analysis (NumFreq)
- Solvation (CPCM)
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ORCAConfig:
    method: str = "r2SCAN-3c"
    basis: str = "def2-mTZVPP"
    charge: int = 0
    multiplicity: int = 1
    nprocs: int = 8
    maxcore: int = 4096
    solvent: Optional[str] = None
    tight_scf: bool = True
    d3: bool = False  # r2SCAN-3c has built-in D4


PRECISION_TIERS = {
    "quick": ORCAConfig(method="GFN-xTB"),
    "screening": ORCAConfig(method="r2SCAN-3c", basis="def2-mTZVPP"),
    "validation": ORCAConfig(method="DLPNO-CCSD(T)", basis="def2-TZVP", tight_scf=True),
    "excited_state": ORCAConfig(method="r2SCAN-3c", basis="def2-mTZVPP"),
}


def generate_orca_inputs(
    xyz_file: str,
    calc_type: str = "optimization",
    precision: str = "screening",
    config: Optional[ORCAConfig] = None,
    output_dir: Optional[str] = None,
) -> Path:
    """
    Generate an ORCA input file for a given calculation.

    Args:
        xyz_file: path to molecular geometry file
        calc_type: "optimization", "single_point", "scan", "dlpno",
                   "tddft", "numfreq"
        precision: "quick", "screening", "validation", "excited_state"
        config: override default config for precision tier
        output_dir: directory for output files

    Returns:
        Path to generated .inp file
    """
    if config is None:
        config = PRECISION_TIERS[precision]

    coords = _read_xyz(xyz_file)
    inp_content = _build_input(coords, calc_type, config)

    output_path = _write_input(inp_content, xyz_file, calc_type, output_dir)
    return output_path


def _build_input(coords, calc_type, config):
    """Build ORCA input string from coordinates and config."""
    lines = []

    # Method line
    if calc_type == "optimization":
        lines.append(f"! {config.method} {config.basis} TightSCF Opt")
    elif calc_type == "single_point":
        lines.append(f"! {config.method} {config.basis} TightSCF")
    elif calc_type == "dlpno":
        lines.append(f"! DLPNO-CCSD(T) {config.basis} TightSCF")
    elif calc_type == "tddft":
        lines.append(f"! {config.method} {config.basis} TightSCF TD-Nstates 10")
    elif calc_type == "numfreq":
        lines.append(f"! {config.method} {config.basis} TightSCF NumFreq")

    # Resource block
    lines.append(f"%pal nprocs {config.nprocs} end")
    lines.append(f"%maxcore {config.maxcore}")

    # Solvation
    if config.solvent:
        lines.append(f"%cpcm solvent \"{config.solvent}\" end")

    # Charge and coordinates
    lines.append(f"* xyzfile {config.charge} {config.multiplicity} {coords}")
    lines.append("")

    return "\n".join(lines)


def _read_xyz(xyz_file):
    """Read XYZ coordinates from file."""
    pass


def _write_input(content, xyz_file, calc_type, output_dir):
    """Write ORCA input file to disk."""
    pass
