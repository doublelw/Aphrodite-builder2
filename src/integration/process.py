"""
Manufacturing integration process for organic battery production.

Covers the full production chain from lab to pilot to industrial scale:
  - Electrode manufacturing (slurry mixing, coating, calendering)
  - Cell assembly (stacking, winding, electrolyte filling)
  - Formation and aging protocols
  - Quality control checkpoints
  - Cost analysis at each scale
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


class ProductionScale(Enum):
    LAB = "lab"
    PILOT = "pilot"
    INDUSTRIAL = "industrial"


@dataclass
class ProcessStep:
    name: str
    equipment: str
    duration: str
    temperature: str = "rt"
    atmosphere: str = "air"
    quality_checks: List[str] = field(default_factory=list)
    cost_per_kwh: float = 0.0
    notes: str = ""


@dataclass
class ManufacturingProcess:
    """Complete manufacturing process specification."""
    scale: ProductionScale
    steps: List[ProcessStep]
    throughput_kwh_per_day: float = 0.0
    labor_per_shift: int = 0
    capex_usd: float = 0.0
    opex_usd_per_kwh: float = 0.0
    yield_pct: float = 0.0
    quality_gates: List[str] = field(default_factory=list)


class IntegrationEngine:
    """
    Design manufacturing processes for organic battery cells.

    Usage:
        engine = IntegrationEngine()
        process = engine.design_process(ProductionScale.LAB)
        report = engine.generate_process_report(process)
    """

    def design_process(self, scale: ProductionScale,
                       electrode_type: str = "organic_cathode",
                       cell_format: str = "pouch") -> ManufacturingProcess:
        """Design manufacturing process for target scale."""
        if scale == ProductionScale.LAB:
            return self._lab_process(electrode_type)
        elif scale == ProductionScale.PILOT:
            return self._pilot_process(electrode_type)
        else:
            return self._industrial_process(electrode_type)

    def _lab_process(self, electrode_type: str) -> ManufacturingProcess:
        return ManufacturingProcess(
            scale=ProductionScale.LAB,
            steps=[
                ProcessStep(
                    name="Slurry Preparation",
                    equipment="Planetary mixer (100mL) or mortar + pestle",
                    duration="2h",
                    notes="Active material:Super P:PVDF = 7:2:1 in NMP, "
                          "mix at 2000rpm until homogeneous",
                    quality_checks=["Viscosity check (Zahn cup #4, 30-60s)"],
                ),
                ProcessStep(
                    name="Electrode Coating",
                    equipment="Doctor blade coater on Al foil (15um)",
                    duration="1h per batch",
                    notes="Target loading: 2-3 mg/cm² active material",
                    quality_checks=["Loading uniformity +/- 5%"],
                ),
                ProcessStep(
                    name="Drying",
                    equipment="Vacuum oven",
                    duration="12h at 80C + 6h at 120C under vacuum",
                    temperature="120C",
                    quality_checks=["Weight consistency", "No cracking"],
                ),
                ProcessStep(
                    name="Calendering",
                    equipment="Lab calender or manual press",
                    duration="30 min",
                    notes="Compress to target porosity (25-35%)",
                    quality_checks=["Thickness measurement", "Porosity check"],
                ),
                ProcessStep(
                    name="Electrode Cutting",
                    equipment="Precision punch (12mm or 14mm disc)",
                    duration="30 min per batch",
                    notes="Cut discs, weigh each for loading calculation",
                    quality_checks=["Weight per disc record"],
                ),
                ProcessStep(
                    name="Cell Assembly",
                    equipment="Ar glovebox (H2O < 0.1ppm, O2 < 0.1ppm)",
                    duration="30 min per cell",
                    atmosphere="Ar (glovebox)",
                    notes="Cathode disc + 30uL electrolyte + separator + Li anode",
                    quality_checks=["Glovebox atmosphere check"],
                ),
                ProcessStep(
                    name="Formation",
                    equipment="Battery cycler",
                    duration="48h",
                    notes="3 cycles at C/20, room temperature",
                    quality_checks=["First cycle CE > 80%", "No abnormal voltage"],
                ),
                ProcessStep(
                    name="Aging",
                    equipment="Temperature chamber",
                    duration="7 days at 25C or 3 days at 45C",
                    temperature="25C",
                    quality_checks=["OCV stability", "No swelling"],
                ),
            ],
            throughput_kwh_per_day=0.001,
            labor_per_shift=1,
            capex_usd=50000,
            opex_usd_per_kwh=500,
            yield_pct=80,
        )

    def _pilot_process(self, electrode_type: str) -> ManufacturingProcess:
        return ManufacturingProcess(
            scale=ProductionScale.PILOT,
            steps=[
                ProcessStep(
                    name="Slurry Mixing (Continuous)",
                    equipment="Continuous mixer (10L/hour)",
                    duration="Continuous",
                    notes="7:2:1 ratio, inline viscosity monitoring",
                    quality_checks=["Inline viscosity", "Particle size distribution"],
                ),
                ProcessStep(
                    name="Slot-Die Coating",
                    equipment="Slot-die coater, 300mm width",
                    duration="Continuous, 5 m/min",
                    notes="Double-side coating, dry between sides",
                    quality_checks=["Coating weight per area", "Edge quality"],
                ),
                ProcessStep(
                    name="Continuous Drying",
                    equipment="Multi-zone convection oven (50m)",
                    duration="2-3 min residence time",
                    temperature="80C → 120C → 150C zones",
                    quality_checks=["Residual solvent < 500ppm"],
                ),
                ProcessStep(
                    name="Calendering",
                    equipment="Two-roll calender, 10 ton",
                    duration="Continuous",
                    notes="Target density 1.8-2.2 g/cm³",
                    quality_checks=["Thickness +/- 2um", "Porosity 28-32%"],
                ),
                ProcessStep(
                    name="Slitting and Notching",
                    equipment="Rotary slitter + laser notcher",
                    duration="Continuous",
                    quality_checks=["Tab position accuracy", "No burrs"],
                ),
                ProcessStep(
                    name="Stack Assembly",
                    equipment="Semi-automatic stacker",
                    duration="30 sec/layer",
                    atmosphere="Dry room (dew point < -40C)",
                    quality_checks=["Stack alignment", "Layer count"],
                ),
                ProcessStep(
                    name="Tab Welding + Packaging",
                    equipment="Ultrasonic welder + pouch sealer",
                    duration="60 sec/cell",
                    quality_checks=["Weld strength", "Seal integrity"],
                ),
                ProcessStep(
                    name="Electrolyte Filling",
                    equipment="Semi-auto dispenser in dry room",
                    duration="30 sec/cell",
                    notes="Precise volume control, vacuum filling",
                    quality_checks=["Fill volume accuracy"],
                ),
                ProcessStep(
                    name="Formation + Grading",
                    equipment="Multi-channel formation cycler (512ch)",
                    duration="48-72h",
                    notes="Formation protocol + grading by capacity and IR",
                    quality_checks=["CE > 95%", "Capacity within grade bins"],
                ),
            ],
            throughput_kwh_per_day=50,
            labor_per_shift=5,
            capex_usd=5_000_000,
            opex_usd_per_kwh=80,
            yield_pct=92,
        )

    def _industrial_process(self, electrode_type: str) -> ManufacturingProcess:
        return ManufacturingProcess(
            scale=ProductionScale.INDUSTRIAL,
            steps=[
                ProcessStep(
                    name="Automated Slurry Production",
                    equipment="Industrial continuous mixer (500L/h)",
                    duration="Continuous, 24/7",
                    notes="Automated dosing, inline QC",
                    quality_checks=["Inline rheology", "Solids content"],
                ),
                ProcessStep(
                    name="High-Speed Coating Line",
                    equipment="Slot-die coater, 1200mm width, 30 m/min",
                    duration="Continuous",
                    notes="Simultaneous double-side coating",
                    quality_checks=["Coating weight per area", "Defect inspection"],
                ),
                ProcessStep(
                    name="Production Calendering",
                    equipment="Production calender, 50 ton",
                    duration="Continuous, 20 m/min",
                    quality_checks=["Inline thickness gauge"],
                ),
                ProcessStep(
                    name="Automated Cell Assembly",
                    equipment="Fully automated production line",
                    duration="3-5 sec/cell",
                    atmosphere="Dry room 1000m2+",
                    quality_checks=["100% visual inspection", "Dimensional check"],
                ),
                ProcessStep(
                    name="Formation System",
                    equipment="Formation system (10000+ channels)",
                    duration="24-48h per batch",
                    quality_checks=["Automated grading and sorting"],
                ),
            ],
            throughput_kwh_per_day=5000,
            labor_per_shift=20,
            capex_usd=100_000_000,
            opex_usd_per_kwh=35,
            yield_pct=97,
        )

    def generate_process_report(self, process: ManufacturingProcess) -> str:
        """Generate manufacturing process report."""
        lines = [
            f"Manufacturing Process: {process.scale.value.upper()}",
            "=" * 60,
            f"Throughput: {process.throughput_kwh_per_day:.1f} kWh/day",
            f"Labor: {process.labor_per_shift} per shift",
            f"CAPEX: ${process.capex_usd:,.0f}",
            f"OPEX: ${process.opex_usd_per_kwh:.1f}/kWh",
            f"Yield: {process.yield_pct:.0f}%",
            "",
        ]

        for i, step in enumerate(process.steps, 1):
            lines.append(f"Step {i}: {step.name}")
            lines.append(f"  Equipment: {step.equipment}")
            lines.append(f"  Duration: {step.duration}")
            if step.temperature != "rt":
                lines.append(f"  Temperature: {step.temperature}")
            if step.atmosphere != "air":
                lines.append(f"  Atmosphere: {step.atmosphere}")
            if step.notes:
                lines.append(f"  Notes: {step.notes}")
            for qc in step.quality_checks:
                lines.append(f"  QC: {qc}")
            lines.append("")

        return "\n".join(lines)

    def scale_comparison(self) -> str:
        """Compare costs across scales."""
        scales = [
            self._lab_process("organic"),
            self._pilot_process("organic"),
            self._industrial_process("organic"),
        ]

        lines = [
            "Scale Comparison for Organic Battery Manufacturing",
            "=" * 60,
            f"{'Scale':<15} {'CAPEX':>15} {'OPEX/kWh':>12} {'Yield':>8} {'kWh/day':>10}",
            "-" * 60,
        ]

        for p in scales:
            lines.append(
                f"{p.scale.value:<15} "
                f"${p.capex_usd:>14,.0f} "
                f"${p.opex_usd_per_kwh:>10.1f} "
                f"{p.yield_pct:>6.0f}% "
                f"{p.throughput_kwh_per_day:>9.1f}"
            )

        return "\n".join(lines)
