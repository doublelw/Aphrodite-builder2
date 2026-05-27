# Aphrodite-builder

**First-principles molecular design platform for organic battery materials.**

Specify performance targets (voltage, energy density, thermal stability, cycle life, flame resistance...), get molecular candidates ranked by multi-objective fitness.

> Aphrodite: Greek name for Venus. This project was born from a question: how do you store energy on a planet where the atmosphere is 96.5% CO2 and there's no lithium, cobalt, or nickel? The answer: design organic battery molecules from first principles, using the planet's own resources.

---

## What it does

Aphrodite-builder is a computational framework that:

1. **Defines battery performance targets** — voltage, energy density, power density, cycle life, flame resistance, temperature range
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
│   ├── ai_interface/            # Claude / GLM / DeepSeek API integration
│   ├── models/                  # BatteryFold neural network (AlphaFold2-inspired)
│   ├── workflows/               # Complete analysis pipelines
│   │   ├── screening_pipeline.py    # SMILES → geometry → ORCA → ranking
│   │   ├── precision_ladder.py      # xTB → DFT → DLPNO escalation
│   │   ├── planetary_adapter.py     # Venus/Mars/Lunar/Orbital evaluation
│   │   └── battery_analysis.py      # Redox/lambda/thermal/flame analysis
│   ├── cli/                     # Command-line interface (batteryfold command)
│   ├── monitoring/              # Pipeline status dashboard
│   └── analysis/                # Battery metrics, energy profiles, validation reports
├── scripts/setup.sh             # Dependency checker and installation guide
├── config/                      # Precision tiers, battery targets, environment parameters
├── docs/                        # Methodology and BatteryFold architecture
├── examples/                    # Usage examples
└── setup.py                     # pip-installable package
```

## BatteryFold: Neural Molecular Design

BatteryFold is an AlphaFold2-inspired neural network adapted for battery molecular design:

| AlphaFold2 | BatteryFold |
|------------|-------------|
| MSA representation | Chemical analog database embeddings |
| Evoformer (attention) | Molecular Transformer (atom+bond attention) |
| Triangle multiplication | 3-body molecular interaction modeling |
| Structure Module | SE(3)-equivariant geometry refinement |
| pLDDT confidence | Per-atom property confidence scores |
| Recycle loop | Precision-tier iterative refinement |

Predicts 9 battery properties from molecular graph:
- Theoretical voltage, energy density, HOMO/LUMO, band gap
- Reorganization energy (lambda), thermal stability, flame resistance, cycle stability

```python
from src.models.batteryfold import BatteryFold, BatteryFoldConfig

model = BatteryFold(BatteryFoldConfig())
properties, confidence = model(atomic_numbers, bond_types, distances, coordinates)
# properties = {'voltage': 3.7, 'energy_density': 310, 'homo': -4.9, ...}
```

## Workflows

### 1. Full Screening Pipeline

```bash
# From SMILES to ranked candidates
batteryfold screen --smiles "c1ccccc1" "C1=CC=C(C=C1)O" --method r2SCAN-3c
```

```python
from src.workflows.screening_pipeline import ScreeningPipeline

pipeline = ScreeningPipeline(method='r2SCAN-3c', solvent='CPCM(water)')
results = pipeline.run(molecules={'aniline': 'c1ccccc1N', 'phenol': 'c1ccccc1O'})
report = pipeline.generate_report(results)
```

### 2. Multi-Precision Ladder

Only molecules passing thresholds at each tier advance, saving 90%+ compute:

```
GFN-xTB (seconds) → r2SCAN-3c (hours) → DLPNO-CCSD(T) (days)
```

```bash
batteryfold ladder --file molecules.txt --tier dlpno
```

### 3. Planetary Environment Evaluation

```bash
batteryfold adapt --file properties.json --environments venus mars orbital
```

| Environment | Key constraints |
|-------------|----------------|
| Venus (50km) | 96.5% CO2, 0.904g, ~1 atm, only CO2-derived organics |
| Mars surface | CO2 atmosphere, low pressure, -60C, ISRU metals |
| Lunar surface | Vacuum, 300C thermal range, radiation |
| Orbital | 90-min thermal cycling, 10+ year lifetime |

### 4. Battery Metrics Analysis

Redox potential, reorganization energy (4-point method), thermal stability, flame resistance, solvent compatibility:

```bash
batteryfold analyze --name quinone_A --xyz geometry.xyz --type full
```

## AI Integration

BatteryFold supports Claude, GLM (Zhipu), and DeepSeek as AI assistants for molecular design reasoning:

```bash
# Interactive AI configuration
batteryfold setup --ai

# Select provider, enter API key, choose model
# Supports custom base URLs for proxies
```

```python
from src.ai_interface import AIInterface

ai = AIInterface.from_config('config/ai_config.json')

# Ask AI to design molecules meeting specific targets
candidates = ai.design_molecules({
    'voltage': '>3.5V',
    'energy_density': '>300 Wh/kg',
    'environment': 'venus_co2_atmosphere',
})

# Interpret calculation results
analysis = ai.analyze_results(orca_output_text)
```

## Pipeline Monitoring

```bash
# Dashboard view
batteryfold monitor

# Live monitoring (auto-refresh)
python3 -c "from src.monitoring.dashboard import watch_dashboard; watch_dashboard()"
```

```
============================================================
  BatteryFold Pipeline Monitor    2026-05-28 08:00:00
============================================================

  Progress: [##########----------] 48%
  Total: 25  Done: 12  Running: 8  Failed: 2

  Name                     Tier     Status       Progress
  --------------------------------------------------------
  [+] quinone_A_001        dft      completed    100%
  [>] quinone_B_014        dft      running      67%
  [x] quinone_C_007        dft      failed       0%
```

## The methodology

We don't guess molecules and test them. We work backwards from the physics.

1. **Start with the environment** — What temperature? What pressure? What materials are available? These constraints determine what chemistry is possible.

2. **Derive molecular requirements** — From the environment and performance targets, derive constraints on molecular properties: HOMO/LUMO levels, reorganization energy, solvation behavior, thermal decomposition temperature.

3. **Search chemical space** — Generate candidate molecular structures satisfying structural constraints. AI accelerates the search from dozens to millions of candidates.

4. **Validate with quantum chemistry** — Run first-principles calculations (r2SCAN-3c for screening, DLPNO-CCSD(T) for gold-standard validation).

5. **Iterate autonomously** — The AI orchestrator manages the entire loop: define problem, generate inputs, deploy to compute cluster, monitor convergence, extract results, iterate. Including self-healing when calculations fail.

## AI orchestration

The platform includes an autonomous compute orchestration system:

- **Pipeline controller**: Computational workflow end-to-end
- **Cluster manager**: Distributes jobs across multiple compute nodes
- **Self-healing system**: Detects failed calculations, diagnoses errors, redeploys with fixes
- **Watchdog + Sentinel + Coordinator**: Three-layer architecture for reliable autonomous operation

This runs autonomously. The operator gives it a problem, it processes overnight and delivers ranked candidates by morning.

## Setup

```bash
# Clone and install
git clone https://github.com/doublelw/Aphrodite-builder2.git
cd Aphrodite-builder2
pip install -e .

# Check dependencies
bash scripts/setup.sh

# Configure AI
batteryfold setup --ai
```

### Required tools

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.10+ | Runtime | system |
| ORCA | Quantum chemistry (DFT/DLPNO) | [Facility license](https://orcaforum.cec.mpg.de/) |
| RDKit | Molecular toolkit | `conda install -c conda-forge rdkit` |
| xtb | Semi-empirical quick screening | `conda install -c conda-forge xtb` |
| PyTorch | BatteryFold neural model | `pip install torch` |

### Optional tools

| Tool | Purpose | Install |
|------|---------|---------|
| Multiwfn | Wavefunction analysis | [sobereva.com](http://sobereva.com/multiwfn/) |
| Open Babel | Format conversion | `conda install -c conda-forge openbabel` |

## Design philosophy

**First principles, not iteration.** Don't start with existing battery chemistry and try to improve it. Start with the physics of the target environment and build molecules that work there.

**AI as orchestrator, not oracle.** AI doesn't tell us what molecules to make. AI manages the computational pipeline. The physics comes from quantum chemistry, not from machine learning.

**Environment-first design.** Every planet has different available materials, different temperatures, different radiation. Design for where you're going, not where you came from.

## Why "Aphrodite"

Aphrodite is the Greek name for Venus. This project started from a question: if humanity is going to become a multi-planetary civilization, every planet needs its own energy storage. Venus, with its unlimited CO2 supply, demands organic batteries synthesized from atmospheric carbon.

The same approach works everywhere: Starlink orbital batteries, Starship power systems, Mars ISRU energy. Different environments, same physics. Design for the planet.

## License

MIT

## Author

Wei Liu — Founder and CTO, Jiangsu Pofeclife Technology Co., Ltd.
