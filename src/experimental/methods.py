"""
Experimental methods for organic battery characterization.

Generates detailed experimental protocols for:
  - Electrochemical testing (CV, GCD, EIS, rate capability)
  - Material characterization (XRD, SEM, TEM, XPS, FTIR, Raman)
  - Thermal analysis (TGA, DSC)
  - Structural analysis (NMR, mass spec)
  - Performance testing (cycle life, self-discharge, leakage current)

Each method includes: equipment, parameters, expected results, data analysis.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class TestType(Enum):
    CV = "cyclic_voltammetry"
    GCD = "galvanostatic_charge_discharge"
    EIS = "electrochemical_impedance_spectroscopy"
    RATE = "rate_capability"
    CYCLE = "cycle_life"
    SELF_DISCHARGE = "self_discharge"
    XRD = "xrd"
    SEM = "sem"
    TEM = "tem"
    XPS = "xps"
    FTIR = "ftir"
    RAMAN = "raman"
    TGA = "tga"
    DSC = "dsc"
    NMR = "nmr"


@dataclass
class ExperimentalMethod:
    """Complete experimental method specification."""
    name: str
    test_type: TestType
    equipment: List[str]
    parameters: Dict[str, str]
    procedure: List[str]
    expected_results: List[str]
    data_analysis: List[str]
    safety_notes: List[str] = field(default_factory=list)
    estimated_time: str = ""
    estimated_cost_usd: float = 0.0


class ExperimentalDesigner:
    """
    Design experimental protocols for organic battery testing.

    Usage:
        designer = ExperimentalDesigner()
        protocol = designer.design_battery_test_suite("quinone_A", voltage=3.7)
    """

    def design_battery_test_suite(self, molecule_name: str,
                                  voltage: float = 3.5,
                                  capacity: float = 200.0) -> List[ExperimentalMethod]:
        """Generate complete test suite for a new organic battery material."""
        methods = [
            self._cv_method(molecule_name, voltage),
            self._gcd_method(molecule_name, capacity),
            self._eis_method(molecule_name),
            self._rate_method(molecule_name, capacity),
            self._cycle_method(molecule_name),
            self._material_characterization(molecule_name),
        ]
        return methods

    def _cv_method(self, name: str, voltage: float) -> ExperimentalMethod:
        return ExperimentalMethod(
            name=f"CV_{name}",
            test_type=TestType.CV,
            equipment=[
                "Potentiostat (BioLogic VMP3 or Gamry)",
                "Three-electrode cell (working: glassy carbon, "
                "counter: Pt wire, reference: Ag/AgCl)",
                "Electrolyte: 0.1M TBAPF6 in anhydrous ACN",
            ],
            parameters={
                "scan_rate": "0.1, 0.5, 1.0, 2.0, 5.0 mV/s",
                "voltage_range": f"{voltage - 1.0:.1f}V to {voltage + 0.5:.1f}V vs Ag/AgCl",
                "scan_direction": "first cathodic, then anodic",
                "cycles": "3-5 cycles for stabilization",
            },
            procedure=[
                f"1. Dissolve 1-2mg {name} in 10mL electrolyte",
                "2. Degas solution with Ar for 15 min",
                "3. Polish glassy carbon electrode with 0.05um alumina",
                "4. Run CV at each scan rate sequentially",
                "5. Record peak potentials and currents",
            ],
            expected_results=[
                f"Reversible redox couple near {voltage:.1f}V",
                "Peak separation < 100mV for fast kinetics",
                "Linear i_p vs sqrt(v) indicates diffusion control",
                "Peak current ratio close to 1.0 for reversibility",
            ],
            data_analysis=[
                "Extract E1/2 = (Epa + Epc) / 2",
                "Calculate diffusion coefficient from Randles-Sevcik equation",
                "Evaluate reversibility from ΔEp and ipa/ipc ratio",
                "Plot Laviron analysis for electron transfer rate",
            ],
            estimated_time="4 hours",
            estimated_cost_usd=50,
        )

    def _gcd_method(self, name: str, capacity: float) -> ExperimentalMethod:
        return ExperimentalMethod(
            name=f"GCD_{name}",
            test_type=TestType.GCD,
            equipment=[
                "Battery cycler (Neware BTS or Arbin)",
                f"Coin cell (CR2032) with {name} cathode",
                "Reference: Li metal anode",
            ],
            parameters={
                "charge_rate": "C/10",
                "discharge_rate": "C/10",
                "voltage_range": "2.5V - 4.2V vs Li/Li+",
                "formation_cycles": "3 cycles at C/20",
            },
            procedure=[
                "1. Assemble coin cells in Ar glovebox",
                "2. Rest 12h after assembly",
                "3. Formation: 3 cycles at C/20",
                "4. GCD testing at C/10",
                "5. Record charge/discharge curves",
            ],
            expected_results=[
                f"Theoretical capacity: {capacity:.0f} mAh/g",
                "Flat plateau indicates two-phase reaction",
                "Sloping curve indicates single-phase insertion",
                "Coulombic efficiency > 99% after formation",
            ],
            data_analysis=[
                "Calculate specific capacity from discharge curve",
                "Measure coulombic efficiency = discharge/charge capacity",
                "Extract voltage hysteresis",
                "Calculate energy density = integral(V*dQ)/mass",
            ],
            estimated_time="48 hours",
            estimated_cost_usd=100,
        )

    def _eis_method(self, name: str) -> ExperimentalMethod:
        return ExperimentalMethod(
            name=f"EIS_{name}",
            test_type=TestType.EIS,
            equipment=[
                "Potentiostat with EIS module",
                "Coin cell or three-electrode cell",
            ],
            parameters={
                "frequency_range": "100 kHz to 10 mHz",
                "amplitude": "5 mV",
                "dc_offset": "at OCV and various SOC levels",
            },
            procedure=[
                "1. Charge cell to target SOC",
                "2. Rest 2h for equilibrium",
                "3. Run EIS at OCV",
                "4. Repeat at 25%, 50%, 75%, 100% SOC",
            ],
            expected_results=[
                "Semicircle at high frequency: charge transfer resistance",
                "Semicircle at mid frequency: SEI resistance",
                "Warburg tail at low frequency: diffusion",
            ],
            data_analysis=[
                "Fit equivalent circuit: Rs-(Rct||CPE)-W",
                "Extract Rct vs SOC relationship",
                "Calculate Li+ diffusion coefficient from Warburg",
                "Track Rct evolution over cycling for degradation",
            ],
            estimated_time="8 hours",
            estimated_cost_usd=50,
        )

    def _rate_method(self, name: str, capacity: float) -> ExperimentalMethod:
        return ExperimentalMethod(
            name=f"Rate_{name}",
            test_type=TestType.RATE,
            equipment=["Battery cycler", "Coin cells (minimum 3 cells)"],
            parameters={
                "rates": "C/20, C/10, C/5, C/2, 1C, 2C, 5C",
                "cycles_per_rate": "5 cycles",
                "voltage_range": "2.5V - 4.2V",
            },
            procedure=[
                "1. Formation at C/20 (3 cycles)",
                "2. Test at C/20 (5 cycles), record capacity",
                "3. Increase to C/10, then C/5, C/2, 1C, 2C, 5C",
                "4. Return to C/20 to check recovery",
            ],
            expected_results=[
                f"Capacity retention > 80% at 2C vs C/20",
                "Full recovery at C/20 after high-rate testing",
                "Voltage drop at high rates indicates Rct contribution",
            ],
            data_analysis=[
                "Plot capacity vs C-rate",
                "Calculate capacity retention at each rate",
                "Fit rate capability to Cottrell equation",
            ],
            estimated_time="7 days",
            estimated_cost_usd=200,
        )

    def _cycle_method(self, name: str) -> ExperimentalMethod:
        return ExperimentalMethod(
            name=f"Cycle_{name}",
            test_type=TestType.CYCLE,
            equipment=["Battery cycler (long-term)", "Temperature chamber (25C)"],
            parameters={
                "charge_rate": "C/5 CC-CV (CV to C/20 cutoff)",
                "discharge_rate": "C/5",
                "voltage_range": "2.5V - 4.2V",
                "target_cycles": "500 or 80% capacity retention",
                "temperature": "25C +/- 1C",
            },
            procedure=[
                "1. Formation at C/20 (3 cycles)",
                "2. Long-term cycling at C/5",
                "3. Record capacity and CE every cycle",
                "4. EIS every 50 cycles",
                "5. Stop at 80% capacity retention or 500 cycles",
            ],
            expected_results=[
                "Initial coulombic efficiency > 95%",
                "Stable CE > 99.5% after formation",
                "Gradual capacity fade < 0.1%/cycle",
            ],
            data_analysis=[
                "Plot capacity retention vs cycle number",
                "Fit fade model: Q(n) = Q0 * exp(-kn)",
                "Examine capacity drop mechanism from dQ/dV",
            ],
            estimated_time="30-60 days",
            estimated_cost_usd=500,
        )

    def _material_characterization(self, name: str) -> ExperimentalMethod:
        return ExperimentalMethod(
            name=f"Characterization_{name}",
            test_type=TestType.XRD,
            equipment=[
                "XRD (Cu K-alpha, 2theta: 5-80 deg)",
                "SEM + EDS",
                "FTIR (KBr pellet, 400-4000 cm-1)",
                "TGA (N2 atmosphere, RT-800C, 10C/min)",
                "1H/13C NMR (DMSO-d6 or CDCl3)",
                "HRMS (ESI or MALDI)",
            ],
            parameters={
                "xrd_range": "2theta = 5-80 deg, step 0.02 deg",
                "tga_range": "RT to 800C at 10C/min under N2",
                "ftir_resolution": "4 cm-1",
                "nmr_frequency": "400 MHz",
            },
            procedure=[
                "1. Record XRD of pristine material",
                "2. SEM imaging at 1kx, 10kx, 50kx",
                "3. FTIR for functional group identification",
                "4. TGA for thermal stability and decomposition",
                "5. NMR for structural confirmation",
                "6. HRMS for molecular weight verification",
            ],
            expected_results=[
                "XRD: crystal structure and phase purity",
                "SEM: particle morphology and size distribution",
                "FTIR: functional group peaks matching DFT predictions",
                f"TGA: thermal decomposition > 200C for battery safety",
                "NMR: structure matches designed molecule",
            ],
            data_analysis=[
                "Index XRD peaks and refine lattice parameters",
                "Measure particle size from SEM statistics",
                "Assign all FTIR peaks to molecular vibrations",
                "Compare TGA onset with DFT-predicted stability",
            ],
            estimated_time="3 days",
            estimated_cost_usd=300,
            safety_notes=[
                "Handle organic materials in fume hood",
                "TGA: use N2 purge, avoid air decomposition products",
                "NMR: standard solvent safety precautions",
            ],
        )

    def generate_protocol_document(self, methods: List[ExperimentalMethod]) -> str:
        """Generate complete experimental protocol document."""
        lines = [
            "BATTERY EXPERIMENTAL PROTOCOL",
            "=" * 60,
            "",
            f"Total estimated time: {self._total_time(methods)}",
            f"Total estimated cost: ${self._total_cost(methods):.0f}",
            "",
        ]

        for method in methods:
            lines.append(f"## {method.name}")
            lines.append(f"Type: {method.test_type.value}")
            lines.append(f"Time: {method.estimated_time}")
            lines.append(f"Cost: ${method.estimated_cost_usd:.0f}")
            lines.append("")

            lines.append("Equipment:")
            for eq in method.equipment:
                lines.append(f"  - {eq}")

            lines.append("\nParameters:")
            for k, v in method.parameters.items():
                lines.append(f"  {k}: {v}")

            lines.append("\nProcedure:")
            for step in method.procedure:
                lines.append(f"  {step}")

            lines.append("\nExpected Results:")
            for r in method.expected_results:
                lines.append(f"  - {r}")

            if method.safety_notes:
                lines.append("\nSafety:")
                for s in method.safety_notes:
                    lines.append(f"  WARNING: {s}")

            lines.append("\n" + "-" * 60 + "\n")

        return "\n".join(lines)

    def _total_time(self, methods: List[ExperimentalMethod]) -> str:
        return "See individual methods"

    def _total_cost(self, methods: List[ExperimentalMethod]) -> float:
        return sum(m.estimated_cost_usd for m in methods)
