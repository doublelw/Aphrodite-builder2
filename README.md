# Aphrodite-builder

**First-principles molecular design platform for organic battery materials.**

Specify performance targets (voltage, energy density, thermal stability, cycle life, flame resistance...), get molecular candidates ranked by multi-objective fitness.

> Aphrodite: Greek name for Venus. This project was born from a question: how do you store energy on a planet where the atmosphere is 96.5% CO2 and there's no lithium, cobalt, or nickel? The answer: design organic battery molecules from first principles, using the planet's own resources.

---

## What it does

Aphrodite-builder is a computational framework that:

1. **Defines battery performance targets** — voltage, energy density, power density, cycle life, flame resistance, temperature range, and more
2. **Generates molecular candidates** — builds organic molecules from structural constraints derived from those targets
3. **Screens with quantum chemistry** — runs DFT, DLPNO-CCSD(T), and TD-DFT calculations to predict actual performance
4. **Ranks by multi-objective fitness** — balances competing requirements (e.g., high voltage vs. long cycle life)
5. **Adapts to any environment** — Earth, Venus, Mars, lunar surface, orbital. Each environment changes the chemistry constraints.

```
Performance Targets → Structural Constraints → Molecular Candidates → Quantum Chemistry → Ranked Results
```

## Architecture

```
Aphrodite-builder/
├── src/
│   ├── core/                    # Property prediction, constraint design, screening engine
│   ├── quantum/                 # ORCA input generation, result extraction, precision management
│   ├── molecular/               # Geometry builder, dimer constructor, conformer generation
│   ├── ai_orchestrator/         # Autonomous pipeline controller, cluster management, self-healing
│   └── analysis/                # Battery metrics, energy profiles, validation reports
├── examples/                    # Usage examples
├── config/                      # Precision tiers, battery targets, environment parameters
└── docs/                        # Methodology and design philosophy
```

## The methodology

We don't guess molecules and test them. We work backwards from the physics.

1. **Start with the environment** — What temperature? What pressure? What materials are available? What radiation exposure? These constraints determine what chemistry is even possible.

2. **Derive molecular requirements** — From the environment and performance targets, derive constraints on molecular properties: HOMO/LUMO levels, reorganization energy, solvation behavior, thermal decomposition temperature, charge transfer rates.

3. **Search chemical space** — Generate candidate molecular structures that satisfy the structural constraints. This is where AI accelerates the search from dozens to millions of candidates.

4. **Validate with quantum chemistry** — Run first-principles calculations (r2SCAN-3c for screening, DLPNO-CCSD(T) for gold-standard validation) to verify predicted properties match actual electronic structure.

5. **Iterate autonomously** — The AI orchestrator manages the entire loop: define problem, generate inputs, deploy to compute cluster, monitor convergence, extract results, feed next iteration. Including self-healing when calculations fail.

## Multi-precision pipeline

| Tier | Method | Use case | Speed |
|------|--------|----------|-------|
| Screening | r2SCAN-3c/def2-mTZVPP | Rapid candidate evaluation | Fast |
| Validation | DLPNO-CCSD(T)/def2-TZVP | Gold-standard energy accuracy | Slow |
| Excited states | TD-DFT/r2SCAN-3c | Thermal stability, optical properties | Medium |
| Quick scan | GFN-xTB | Preliminary geometry screening | Very fast |

## Battery performance metrics

The platform evaluates candidates across multiple dimensions:

| Metric | Unit | Prediction method |
|--------|------|-------------------|
| Theoretical voltage | V | HOMO/LUMO + electrochemical window |
| Energy density | Wh/kg | Molecular weight + redox potential |
| Power density | W/kg | Charge transfer rate (Marcus theory) |
| Cycle stability | cycles | Reorganization energy |
| Thermal stability | C | TD-DFT decomposition analysis |
| Flame resistance | score | Combustion enthalpy estimation |
| Environmental adaptability | score | Solvation modeling in target environment |

## AI orchestration

The platform includes an autonomous compute orchestration system:

- **Pipeline controller**: Defines the computational workflow end-to-end
- **Cluster manager**: Distributes jobs across multiple compute nodes
- **Self-healing system**: Detects failed calculations, diagnoses errors, redeploys with fixes
- **Watchdog + Sentinel + Coordinator**: Three-layer architecture for reliable autonomous operation

This isn't theoretical. The orchestration system runs autonomously, processing molecular design problems while the operator sleeps.

## Planetary environments

Aphrodite-builder is designed to adapt molecular design to different planetary conditions:

| Environment | Key constraints |
|-------------|----------------|
| Venus (50km altitude) | 96.5% CO2, 0.904g, ~1 atm, 0-50C, only CO2-derived organics available |
| Mars surface | CO2 atmosphere, low pressure, -60C avg, perchlorate-rich soil |
| Lunar surface | Vacuum, extreme temperature swings, radiation, no atmosphere |
| Orbital | Thermal cycling (+-200C), radiation, microgravity, long life requirement |
| Earth | Standard conditions, full periodic table available |

## Quick start

```python
from aphrodite import Designer, BatteryTargets, Environment

# Define what you need
targets = BatteryTargets(
    voltage=">3.5V",
    energy_density=">300 Wh/kg",
    cycle_life=">1000 cycles",
    flame_resistance="self-extinguishing",
)

# Specify the environment
env = Environment.venus_altitude_50km()  # or .mars(), .orbital(), .earth()

# Run the design pipeline
designer = Designer(targets=targets, environment=env)
candidates = designer.search(n_candidates=100)

# Get ranked results
for mol in candidates.top(10):
    print(f"{mol.smiles}: V={mol.voltage:.2f}V, ED={mol.energy_density:.0f}Wh/kg")
```

## Design philosophy

**First principles, not iteration.** Don't start with existing battery chemistry and try to improve it. Start with the physics of the target environment and build molecules that work there.

**AI as orchestrator, not oracle.** AI doesn't tell us what molecules to make. AI manages the computational pipeline: generating candidates, deploying calculations, monitoring convergence, extracting results, iterating. The physics comes from quantum chemistry, not from machine learning.

**Environment-first design.** Every planet has different available materials, different temperatures, different radiation levels. Design for where you're going, not where you came from.

## Why "Aphrodite"

Aphrodite is the Greek name for Venus. This project started from a simple question: if humanity is going to become a multi-planetary civilization, every planet needs its own energy storage solution. Venus, with its unlimited CO2 supply, demands organic batteries synthesized from atmospheric carbon. That's the energy loop for a permanent human presence on Venus.

The same first-principles approach works everywhere: Starlink orbital batteries, Starship power systems, Mars ISRU energy. Different environments, same physics. Design for the planet.

## License

MIT

## Author

Wei Liu — Founder and CTO, Jiangsu Pofeclife Technology Co., Ltd.
