"""
Example: Screen molecules for Venus atmospheric conditions.

Demonstrates environment-first design — evaluating molecular
stability and performance in Venus-specific conditions.
"""
from aphrodite.core import design_for_targets, PerformanceTarget

# Venus needs: CO2-derived organics, stable at 50km altitude
targets = [
    PerformanceTarget(metric="voltage", operator=">", value=2.5, unit="V"),
    PerformanceTarget(metric="thermal_stability", operator=">", value=100, unit="C"),
    PerformanceTarget(metric="flame_resistance", operator=">", value=0.8, unit="score"),
    PerformanceTarget(metric="operating_temperature", operator="range", value=0, unit="50C"),
]

# Design for Venus environment
candidates = design_for_targets(
    targets=targets,
    environment="venus_altitude_50km",
    n_candidates=100,
)

print(f"Found {len(candidates)} candidates for Venus conditions:")
for mol in candidates[:5]:
    print(f"  {mol.smiles}")
    print(f"    V={mol.predicted_properties.get('voltage', 0):.2f}V")
    print(f"    Thermal={mol.predicted_properties.get('thermal_stability', 0):.0f}C")
    print(f"    Flame={mol.predicted_properties.get('flame_resistance', 0):.2f}")
    print()
