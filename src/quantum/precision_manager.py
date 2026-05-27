"""
Precision Manager — manages multi-tier calculation strategies.

Provides cost-accuracy trade-off management:
- Quick tier: GFN-xTB for initial screening (seconds per molecule)
- Screening tier: r2SCAN-3c for property evaluation (minutes per molecule)
- Validation tier: DLPNO-CCSD(T) for gold-standard accuracy (hours per molecule)
- Excited state tier: TD-DFT for thermal and optical properties
"""
from dataclasses import dataclass
from typing import List


@dataclass
class CalculationStage:
    name: str
    method: str
    estimated_time: str      # per molecule
    accuracy: str             # qualitative
    cost_cpu_hours: float     # approximate CPU-hours per molecule


PIPELINE_STAGES = {
    "full_pipeline": [
        CalculationStage("quick_screen", "GFN-xTB", "~10s", "rough", 0.01),
        CalculationStage("geometry_opt", "r2SCAN-3c/def2-mTZVPP", "~30min", "good", 4),
        CalculationStage("electronic_structure", "r2SCAN-3c/def2-mTZVPP", "~10min", "good", 2),
        CalculationStage("solvation", "r2SCAN-3c + CPCM", "~5min/solvent", "good", 1),
        CalculationStage("high_accuracy", "DLPNO-CCSD(T)/def2-TZVP", "~8h", "gold standard", 64),
        CalculationStage("thermal", "TD-DFT/r2SCAN-3c", "~20min", "good", 3),
    ],
    "fast_screen": [
        CalculationStage("quick_screen", "GFN-xTB", "~10s", "rough", 0.01),
        CalculationStage("geometry_opt", "r2SCAN-3c/def2-mTZVPP", "~30min", "good", 4),
        CalculationStage("electronic_structure", "r2SCAN-3c/def2-mTZVPP", "~10min", "good", 2),
    ],
    "validation_only": [
        CalculationStage("high_accuracy", "DLPNO-CCSD(T)/def2-TZVP", "~8h", "gold standard", 64),
    ],
}


class PrecisionManager:
    """Manages calculation precision tiers and resource allocation."""

    def __init__(self, pipeline: str = "full_pipeline"):
        self.stages = PIPELINE_STAGES[pipeline]

    def estimate_total_cost(self, n_molecules: int) -> dict:
        """Estimate total CPU-hours and wall time for n molecules."""
        total_cpu = sum(s.cost_cpu_hours for s in self.stages) * n_molecules
        return {
            "n_molecules": n_molecules,
            "total_cpu_hours": total_cpu,
            "stages": len(self.stages),
            "recommended_servers": max(1, int(total_cpu / 200)),
        }
