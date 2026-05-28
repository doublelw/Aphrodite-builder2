"""
Battery cell architecture design and electrode engineering.

Designs complete battery cells from molecular candidates:
  - Electrode formulation (active material / conductive additive / binder ratios)
  - Electrolyte selection and optimization
  - Separator selection
  - Cell format (coin, pouch, cylindrical)
  - Performance prediction (energy density, power density, cycle life)
  - Cost estimation at lab / pilot / production scale
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class CellFormat(Enum):
    COIN_2032 = "coin_2032"
    COIN_2025 = "coin_2025"
    POUCH = "pouch"
    CYLINDRICAL_18650 = "18650"
    SWAGELOK = "swagelok"


class ElectrolyteType(Enum):
    ORGANIC_LIQUID = "organic_liquid"
    IONIC_LIQUID = "ionic_liquid"
    SOLID_POLYMER = "solid_polymer"
    AQUEOUS = "aqueous"
    CO2_DERIVED = "co2_derived"  # Venus-specific


@dataclass
class ElectrodeDesign:
    """Cathode or anode electrode design."""
    active_material: str
    active_material_pct: float = 70.0
    conductive_additive: str = "Super P"
    conductive_pct: float = 20.0
    binder: str = "PVDF"
    binder_pct: float = 10.0
    solvent: str = "NMP"
    loading_mg_cm2: float = 2.0
    thickness_um: float = 100.0
    porosity_pct: float = 30.0


@dataclass
class ElectrolyteDesign:
    """Electrolyte composition."""
    type: ElectrolyteType
    solvent: str = "EC:DMC (1:1)"
    salt: str = "LiPF6"
    salt_concentration: str = "1.0M"
    additives: List[str] = field(default_factory=list)
    ionic_conductivity_ms_cm: float = 10.0
    voltage_window: tuple = (0.0, 4.5)
    notes: str = ""


@dataclass
class CellDesign:
    """Complete battery cell design."""
    name: str
    format: CellFormat
    cathode: ElectrodeDesign
    anode: ElectrodeDesign
    electrolyte: ElectrolyteDesign
    separator: str = "Celgard 2400"
    voltage_avg: float = 0.0
    voltage_max: float = 0.0
    capacity_mAh_g: float = 0.0
    energy_density_wh_kg: float = 0.0
    power_density_w_kg: float = 0.0
    estimated_cycles: int = 0
    cost_usd_kwh: float = 0.0
    assembly_notes: List[str] = field(default_factory=list)


# Standard electrode formulations
STANDARD_CATHODE = ElectrodeDesign(
    active_material="organic_cathode",
    active_material_pct=70,
    conductive_additive="Super P + CNT",
    conductive_pct=20,
    binder="PVDF",
    binder_pct=10,
    loading_mg_cm2=2.0,
)

STANDARD_ANODES = {
    "lithium_metal": ElectrodeDesign(
        active_material="Li metal foil",
        active_material_pct=100,
        loading_mg_cm2=5.0,
    ),
    "graphite": ElectrodeDesign(
        active_material="Graphite",
        active_material_pct=90,
        conductive_additive="Super P",
        conductive_pct=5,
        binder="CMC+SBR",
        binder_pct=5,
        loading_mg_cm2=3.0,
    ),
    "lithium_titanate": ElectrodeDesign(
        active_material="Li4Ti5O12",
        active_material_pct=85,
        conductive_additive="Super P",
        conductive_pct=10,
        binder="PVDF",
        binder_pct=5,
        loading_mg_cm2=4.0,
    ),
}

STANDARD_ELECTROLYTES = {
    "standard": ElectrolyteDesign(
        type=ElectrolyteType.ORGANIC_LIQUID,
        solvent="EC:DMC (1:1)",
        salt="LiPF6",
        salt_concentration="1.0M",
        ionic_conductivity_ms_cm=10.0,
        voltage_window=(0.0, 4.5),
    ),
    "high_voltage": ElectrolyteDesign(
        type=ElectrolyteType.ORGANIC_LIQUID,
        solvent="EC:EMC (3:7)",
        salt="LiPF6",
        salt_concentration="1.2M",
        additives=["VC 2wt%", "FEC 5wt%"],
        ionic_conductivity_ms_cm=8.0,
        voltage_window=(0.0, 5.0),
    ),
    "aqueous": ElectrolyteDesign(
        type=ElectrolyteType.AQUEOUS,
        solvent="H2O",
        salt="Li2SO4",
        salt_concentration="2.0M",
        ionic_conductivity_ms_cm=50.0,
        voltage_window=(0.0, 1.23),
        notes="Limited voltage window, safe and cheap",
    ),
    "venus_co2": ElectrolyteDesign(
        type=ElectrolyteType.CO2_DERIVED,
        solvent="Supercritical CO2 + ionic liquid",
        salt="CO2-derived ionic species",
        salt_concentration="variable",
        voltage_window=(0.0, 3.5),
        notes="Designed for Venus atmosphere (96.5% CO2). "
              "Organic electrolyte synthesized from atmospheric carbon.",
    ),
}


class CellArchitect:
    """
    Design complete battery cells from molecular candidates.

    Usage:
        architect = CellArchitect()
        cell = architect.design_cell(
            molecule_name="quinone_A",
            voltage=3.7,
            capacity_mAh_g=250,
            format=CellFormat.COIN_2032,
        )
    """

    def design_cell(
        self,
        molecule_name: str,
        voltage: float,
        capacity_mAh_g: float,
        molecular_weight: float = 200.0,
        format: CellFormat = CellFormat.COIN_2032,
        anode_type: str = "lithium_metal",
        electrolyte_type: str = "standard",
        environment: str = "earth",
    ) -> CellDesign:
        """Design a complete battery cell."""
        cathode = ElectrodeDesign(
            active_material=molecule_name,
            active_material_pct=70,
            conductive_additive="Super P + CNT",
            conductive_pct=20,
            binder="PVDF",
            binder_pct=10,
            loading_mg_cm2=2.0,
        )

        anode = STANDARD_ANODES.get(anode_type, STANDARD_ANODES["lithium_metal"]).__class__(
            **{**STANDARD_ANODES[anode_type].__dict__,
               "active_material": STANDARD_ANODES[anode_type].active_material}
        )

        if environment == "venus":
            electrolyte = STANDARD_ELECTROLYTES["venus_co2"]
        elif environment == "aqueous":
            electrolyte = STANDARD_ELECTROLYTES["aqueous"]
        else:
            electrolyte = STANDARD_ELECTROLYTES.get(electrolyte_type, STANDARD_ELECTROLYTES["standard"])

        # Performance estimation
        energy_density = voltage * capacity_mAh_g / 1000 * 0.7  # 70% active material
        power_density = energy_density * 50  # rough estimate

        cycle_estimate = self._estimate_cycle_life(voltage, capacity_mAh_g)
        cost = self._estimate_cost(voltage, capacity_mAh_g, molecular_weight)

        return CellDesign(
            name=f"{molecule_name}_cell",
            format=format,
            cathode=cathode,
            anode=anode,
            electrolyte=electrolyte,
            voltage_avg=voltage,
            voltage_max=voltage * 1.1,
            capacity_mAh_g=capacity_mAh_g,
            energy_density_wh_kg=energy_density,
            power_density_w_kg=power_density,
            estimated_cycles=cycle_estimate,
            cost_usd_kwh=cost,
            assembly_notes=self._assembly_protocol(format),
        )

    def _estimate_cycle_life(self, voltage: float, capacity: float) -> int:
        rough_cycles = 500
        if voltage > 4.0:
            rough_cycles *= 0.5  # high voltage degrades faster
        if capacity > 300:
            rough_cycles *= 0.7  # high capacity often less stable
        return int(rough_cycles)

    def _estimate_cost(self, voltage: float, capacity: float, mw: float) -> float:
        # Active material cost (scales with molecular weight)
        material_cost = mw * 0.01  # $/g rough estimate
        cell_cost = material_cost / (voltage * capacity / 1000) * 1000  # $/kWh
        return round(cell_cost, 2)

    def _assembly_protocol(self, format: CellFormat) -> List[str]:
        protocols = {
            CellFormat.COIN_2032: [
                "1. Prepare cathode slurry: active material + Super P + PVDF in NMP (7:2:1)",
                "2. Coat on Al foil, dry at 80C/12h, then 120C/vacuum/6h",
                "3. Cut 14mm discs, weigh active material loading",
                "4. Assemble CR2032 in Ar glovebox: cathode + separator + electrolyte + Li anode",
                "5. Rest 12h before first cycle",
                "6. Formation: 3 cycles at C/20, then standard testing at C/5",
            ],
            CellFormat.POUCH: [
                "1. Cathode: coat on Al foil (active:Super P:PVDF = 7:2:1)",
                "2. Anode: coat on Cu foil (graphite:Super P:CMC = 9:0.5:0.5)",
                "3. Z-fold stacking with separator",
                "4. Tab welding and pouch sealing",
                "5. Electrolyte filling in Ar glovebox",
                "6. Vacuum seal, rest 24h",
            ],
        }
        return protocols.get(format, ["Assemble per standard cell format procedure"])

    def compare_designs(self, designs: List[CellDesign]) -> str:
        """Generate comparison table of cell designs."""
        lines = [
            f"{'Name':<20} {'V_avg':>6} {'mAh/g':>8} {'Wh/kg':>8} {'Cycles':>7} {'$/kWh':>8}",
            "-" * 60,
        ]
        for d in designs:
            lines.append(
                f"{d.name:<20} {d.voltage_avg:>5.2f}V {d.capacity_mAh_g:>7.0f} "
                f"{d.energy_density_wh_kg:>7.0f} {d.estimated_cycles:>7} {d.cost_usd_kwh:>7.2f}"
            )
        return "\n".join(lines)
