//! Command router — maps natural language to platform capabilities.

use crate::config::ProviderConfig;
use colored::Colorize;

pub struct CommandRouter;

impl CommandRouter {
    pub fn system_prompt(project_name: &str) -> String {
        format!(
r#"You are BatteryFold AI — an expert assistant for organic battery design.

Current project: {project}

You help users with the full battery design chain:

## Core Capabilities

### 1. Molecular Design
- Design organic battery molecules from performance targets
- Predict properties: voltage, energy density, HOMO/LUMO, reorganization energy
- Multi-objective optimization (voltage vs cycle life vs cost)
- Planetary environment adaptation (Venus/Mars/Orbital)

### 2. Quantum Chemistry (via Python backends)
- PySCF: DFT (B3LYP, r2SCAN), MP2, CCSD calculations
- ORCA: DFT, DLPNO-CCSD(T), TD-DFT for production accuracy
- cclib: Parse output from any quantum chemistry software
- Multi-precision pipeline: xTB → DFT → DLPNO-CCSD(T)

### 3. Synthesis Planning
- Reaction route selection (Suzuki, Knoevenagel, Friedel-Crafts, etc.)
- Reagent cost estimation
- Yield prediction and scalability scoring
- Detailed experimental protocols with safety notes

### 4. Cell Engineering
- Electrode formulation (active material / carbon / binder ratios)
- Electrolyte selection (organic, ionic liquid, aqueous, CO2-derived)
- Cell architecture (coin CR2032, pouch, 18650)
- Energy/power density and cycle life estimation

### 5. BMS Algorithms
- SOC estimation (Coulomb counting, OCV, Extended Kalman Filter)
- SOH degradation tracking for organic batteries
- Cell balancing strategies (passive/active)
- Thermal management

### 6. Experimental Methods
- Electrochemical: CV, GCD, EIS, rate capability, cycle life
- Characterization: XRD, SEM, TEM, XPS, FTIR, Raman
- Thermal: TGA, DSC
- Complete test protocols with parameters and expected results

### 7. Manufacturing
- Lab scale (50K CAPEX, $500/kWh)
- Pilot scale ($5M CAPEX, $80/kWh)
- Industrial ($100M CAPEX, $35/kWh)
- Process design for each scale

## Response Style
- Be specific and quantitative when possible
- Give concrete numbers (voltages, costs, yields)
- Suggest next steps
- Reference relevant chemistry principles
- When discussing synthesis, include safety considerations
"#,
            project = project_name,
        )
    }

    /// Check if input is a built-in command.
    pub fn handle_builtin(input: &str, project_name: &str) -> Option<String> {
        let cmd = input.trim().to_lowercase();

        if cmd == "/help" || cmd == "help" {
            return Some(Self::help_text());
        }

        if cmd == "/status" || cmd == "status" {
            return Some(format!("Project: {}\nUse /memory to see stored knowledge.", project_name));
        }

        if cmd == "/capabilities" || cmd == "caps" {
            return Some(Self::capabilities_text());
        }

        if cmd == "/workflow" || cmd == "workflows" {
            return Some(Self::workflows_text());
        }

        if cmd == "/quit" || cmd == "exit" || cmd == "/exit" {
            return Some("__QUIT__".into());
        }

        None
    }

    fn help_text() -> String {
        format!(
            "\n{} BatteryFold Commands\n{}\n",
            "╔══════════════════════════════════════╗".cyan(),
            "╚══════════════════════════════════════╝".cyan(),
        ) + r#"
General:
  /help          Show this help
  /status        Current project status
  /capabilities  Show all platform capabilities
  /workflows     List available workflows
  /projects      Switch to different project
  /config        Reconfigure AI provider
  /quit          Exit BatteryFold

Design Commands (natural language):
  "Design a molecule with >3.5V voltage"
  "Plan synthesis for this quinone"
  "Compare cell architectures"
  "Estimate manufacturing cost"
  "Generate CV test protocol"
  "Analyze this molecule for Venus"

Context Commands:
  /memory        Show project memory/knowledge base
  /history       Show recent conversation context
  /save <text>   Save important finding to project memory
"#
    }

    fn capabilities_text() -> String {
        format!(
r#"
{} BatteryFold Full Capabilities

{} Molecular Design
  • Generate candidates from performance targets
  • Predict: voltage, energy density, HOMO/LUMO, λ, thermal stability
  • BatteryFold neural network (AlphaFold3-inspired architecture)
  • Multi-objective Pareto ranking

{} Quantum Chemistry
  • PySCF: B3LYP, r2SCAN, MP2, CCSD
  • ORCA: DLPNO-CCSD(T) gold-standard
  • TD-DFT for excited states
  • Precision ladder: xTB → DFT → DLPNO escalation

{} Synthesis Planning
  • Route selection and cost estimation
  • Reagent availability and pricing
  • Scalability: lab → pilot → industrial
  • Detailed experimental protocols

{} Cell Engineering
  • Electrode formulation (active/carbon/binder)
  • Electrolyte design (organic/IL/aqueous/CO2-derived)
  • Cell format: coin, pouch, 18650
  • Performance prediction

{} BMS Algorithms
  • SOC: Coulomb, OCV, Extended Kalman Filter
  • SOH: degradation tracking, remaining cycle prediction
  • Cell balancing (passive/active)
  • Thermal management

{} Experimental Methods
  • Electrochemical: CV, GCD, EIS, rate, cycle life
  • Materials: XRD, SEM, TEM, XPS, FTIR, Raman, TGA, DSC
  • Complete protocols with parameters

{} Manufacturing
  • Lab ($50K, $500/kWh) → Pilot ($5M, $80/kWh) → Industrial ($100M, $35/kWh)
  • Full process design at each scale

{} Planetary Adaptation
  • Venus: CO2-derived organic batteries
  • Mars: ISRU energy storage
  • Orbital: Starlink battery lifetime optimization
  • Lunar: vacuum-compatible design
"#,
            "═══".cyan(),
            "1.".bright_blue(), "2.".bright_blue(), "3.".bright_blue(),
            "4.".bright_blue(), "5.".bright_blue(), "6.".bright_blue(),
            "7.".bright_blue(), "8.".bright_blue(),
        )
    }

    fn workflows_text() -> String {
        format!(
r#"
{} Available Workflows

1. {} Full Screening Pipeline
   SMILES → 3D geometry → quantum calculation → property extraction → ranking
   Usage: "Screen these molecules: [SMILES list]"

2. {} Multi-Precision Ladder
   xTB (seconds) → DFT (hours) → DLPNO-CCSD(T) (days)
   Usage: "Run precision escalation on these candidates"

3. {} Planetary Environment Evaluation
   Evaluate molecules for Venus, Mars, Lunar, Orbital conditions
   Usage: "Evaluate molecule X for Venus atmosphere"

4. {} Battery Metrics Analysis
   Redox potential, λ (4-point), thermal, flame, solvent, cycle
   Usage: "Analyze reorganization energy for molecule X"

5. {} Synthesis Route Planning
   Reaction selection → cost → yield → protocol
   Usage: "Plan synthesis for this quinone derivative"

6. {} Cell Design
   Electrode + electrolyte + architecture → performance estimate
   Usage: "Design a coin cell with this molecule as cathode"

7. {} BMS Configuration
   SOC/SOH algorithms for organic battery pack
   Usage: "Design BMS for a 4S1P pack with this chemistry"

8. {} Manufacturing Process
   Lab/pilot/industrial process with cost analysis
   Usage: "Estimate manufacturing cost at pilot scale"
"#,
            "═══".cyan(),
            "→".green(), "→".green(), "→".green(), "→".green(),
            "→".green(), "→".green(), "→".green(), "→".green(),
        )
    }
}
