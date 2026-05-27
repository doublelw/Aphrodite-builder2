"""
Example: Design molecules for a specific target voltage.

Demonstrates how Aphrodite-builder works backwards from a voltage
requirement to derive structural constraints and screen candidates.
"""
from aphrodite.core import design_for_targets, PerformanceTarget

# Define voltage target: >3.7V for a high-voltage organic cathode
targets = [
    PerformanceTarget(metric="voltage", operator=">", value=3.7, unit="V"),
    PerformanceTarget(metric="cycle_life", operator=">", value=500, unit="cycles"),
]

# Design candidates
candidates = design_for_targets(
    targets=targets,
    environment="earth",
    n_candidates=50,
)

# Review top candidates
for i, mol in enumerate(candidates[:10]):
    print(f"#{i+1}: {mol.smiles}")
    print(f"   Voltage: {mol.predicted_properties.get('voltage', '?'):.2f}V")
    print(f"   Fitness: {mol.fitness_score:.3f}")
    print()
