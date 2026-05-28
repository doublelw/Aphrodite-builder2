"""
Planetary environment adaptation workflow.

Designs and evaluates molecules for specific extraterrestrial environments:
  - Venus (50-55km altitude): 96.5% CO2, ~1atm, 0-50C, 0.904g
  - Mars surface: 95% CO2, 0.006atm, -60C, 0.38g
  - Lunar surface: vacuum, -173/+127C, 0.165g
  - Orbital (Starlink): vacuum, -170/+120C, microgravity
  - Earth: reference environment

Each environment imposes unique constraints on molecular stability,
electrochemistry, and battery performance.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

try:
    import yaml
except ImportError:
    yaml = None


class Environment(Enum):
    VENUS = "venus"
    MARS = "mars"
    LUNAR = "lunar"
    ORBITAL = "orbital"
    EARTH = "earth"


@dataclass
class EnvironmentProfile:
    name: str
    temperature_range: tuple  # (min_C, max_C)
    pressure_atm: float
    gravity_g: float
    atmosphere: Dict[str, float]  # {gas: fraction}
    radiation_flux: float  # mSv/day
    solar_irradiance: float  # W/m^2
    available_elements: List[str]
    solvent_options: List[str]
    battery_challenges: List[str]


# Pre-defined planetary profiles based on NASA/ESA data
PLANETARY_PROFILES = {
    Environment.VENUS: EnvironmentProfile(
        name="Venus (50-55km altitude)",
        temperature_range=(0, 50),
        pressure_atm=0.904,
        gravity_g=0.904,
        atmosphere={"CO2": 0.965, "N2": 0.035},
        radiation_flux=0.5,
        solar_irradiance=2600,
        available_elements=["C", "O", "N", "H", "S"],
        solvent_options=["supercritical_CO2", "ionic_liquid_CO2_derived"],
        battery_challenges=[
            "No lithium, cobalt, or nickel available",
            "All materials must derive from atmospheric CO2",
            "Sulfuric acid clouds limit exterior exposure",
            "Organic synthesis from CO2 via electrochemistry",
        ],
    ),
    Environment.MARS: EnvironmentProfile(
        name="Mars surface",
        temperature_range=(-60, 20),
        pressure_atm=0.006,
        gravity_g=0.38,
        atmosphere={"CO2": 0.95, "N2": 0.025, "Ar": 0.016},
        radiation_flux=0.67,
        solar_irradiance=590,
        available_elements=["C", "O", "N", "H", "Fe", "Si", "Mg", "Al", "S"],
        solvent_options=["liquid_CO2", "ionic_liquids", "solid_electrolyte"],
        battery_challenges=[
            "Low temperature battery operation",
            "Thin atmosphere limits cooling",
            "ISRU: Fe/S/Mg-based cathode candidates",
            "Dust contamination of contacts",
        ],
    ),
    Environment.LUNAR: EnvironmentProfile(
        name="Lunar surface",
        temperature_range=(-173, 127),
        pressure_atm=0.0,
        gravity_g=0.165,
        atmosphere={},
        radiation_flux=1.3,
        solar_irradiance=1360,
        available_elements=["O", "Si", "Al", "Fe", "Ca", "Mg", "Ti"],
        solvent_options=["solid_electrolyte", "ionic_liquid", "molten_salt"],
        battery_challenges=[
            "Extreme thermal cycling (300C range)",
            "No atmosphere: vacuum-compatible cells",
            "Radiation degradation of organic materials",
            "Low gravity affects electrolyte distribution",
        ],
    ),
    Environment.ORBITAL: EnvironmentProfile(
        name="Low Earth Orbit (Starlink)",
        temperature_range=(-170, 120),
        pressure_atm=0.0,
        gravity_g=0.0,
        atmosphere={},
        radiation_flux=1.0,
        solar_irradiance=1360,
        available_elements=["whatever_is_launched"],
        solvent_options=["solid_electrolyte", "gel_polymer"],
        battery_challenges=[
            "10+ year operational lifetime",
            "Radiation-induced degradation",
            "Thermal cycling every 90 minutes",
            "Mass and volume constraints",
            "No maintenance possible",
        ],
    ),
    Environment.EARTH: EnvironmentProfile(
        name="Earth (reference)",
        temperature_range=(-40, 55),
        pressure_atm=1.0,
        gravity_g=1.0,
        atmosphere={"N2": 0.78, "O2": 0.21, "Ar": 0.009},
        radiation_flux=0.01,
        solar_irradiance=1000,
        available_elements=["all"],
        solvent_options=["water", "organic", "ionic_liquid", "solid"],
        battery_challenges=[],
    ),
}


@dataclass
class AdaptationResult:
    molecule_name: str
    environment: str
    compatibility_score: float  # 0-1
    adapted_properties: Dict[str, float]
    warnings: List[str] = field(default_factory=list)
    modifications: List[str] = field(default_factory=list)


class PlanetaryAdapter:
    """
    Evaluate and adapt molecular designs for planetary environments.

    Usage:
        adapter = PlanetaryAdapter()
        result = adapter.evaluate('quinone_A', properties, Environment.VENUS)
    """

    def __init__(self, config_path: str = None):
        self.profiles = dict(PLANETARY_PROFILES)
        if config_path:
            self._load_custom_profiles(config_path)

    def _load_custom_profiles(self, path: str):
        if yaml is None:
            return
        with open(path) as f:
            custom = yaml.safe_load(f)
        for env_name, data in custom.items():
            self.profiles[Environment(env_name)] = EnvironmentProfile(**data)

    def evaluate(self, molecule_name: str,
                 properties: Dict[str, float],
                 environment: Environment) -> AdaptationResult:
        """
        Evaluate a molecule's suitability for a target environment.

        Checks thermal stability, pressure compatibility, radiation
        resistance, and electrochemical viability under local conditions.
        """
        profile = self.profiles[environment]
        warnings = []
        score = 1.0

        # Thermal compatibility
        thermal = properties.get('thermal_stability', 200)
        t_min, t_max = profile.temperature_range
        if thermal < t_max + 50:
            warnings.append(
                f"Thermal stability ({thermal}C) too close to "
                f"environment max ({t_max}C)"
            )
            score *= 0.5

        # Pressure effects on electrochemistry
        if profile.pressure_atm < 0.01:
            if properties.get('has_volatile_components', False):
                warnings.append("Volatile components unstable in vacuum/near-vacuum")
                score *= 0.3

        # Radiation resistance (approximated by bond dissociation energy)
        if profile.radiation_flux > 0.5:
            gap = properties.get('gap', 3.0)
            if gap < 2.0:
                warnings.append(
                    f"Small band gap ({gap}eV) susceptible to "
                    f"radiation damage at {profile.radiation_flux} mSv/day"
                )
                score *= 0.7

        # Gravity effects on electrolyte
        if profile.gravity_g < 0.01:
            warnings.append("Microgravity: verify electrolyte contact")
            score *= 0.9

        # Element availability
        if environment != Environment.EARTH:
            mol_elements = properties.get('elements', [])
            unavailable = [
                e for e in mol_elements
                if e not in profile.available_elements and e not in ['C', 'H', 'O', 'N']
            ]
            if unavailable:
                warnings.append(
                    f"Elements {unavailable} not locally available "
                    f"for ISRU"
                )
                score *= 0.6

        adapted = self._extrapolate_properties(properties, profile)

        return AdaptationResult(
            molecule_name=molecule_name,
            environment=environment.value,
            compatibility_score=max(0.0, min(1.0, score)),
            adapted_properties=adapted,
            warnings=warnings,
        )

    def _extrapolate_properties(self, props: Dict[str, float],
                                profile: EnvironmentProfile) -> Dict[str, float]:
        """
        Adjust predicted properties for target environment conditions.

        Uses simplified thermodynamic corrections for temperature and
        pressure effects on voltage, energy density, and reaction kinetics.
        """
        adapted = dict(props)

        # Temperature correction on voltage (Nernst-like)
        t_avg = sum(profile.temperature_range) / 2 + 273.15  # K
        t_ref = 298.15
        if 'theoretical_voltage' in adapted:
            dT = t_avg - t_ref
            adapted['theoretical_voltage'] += -0.0001 * dT

        # Pressure effect on energy density
        if 'energy_density' in adapted:
            p_ratio = profile.pressure_atm / 1.0
            adapted['energy_density'] *= max(0.1, min(1.2, 1.0 + 0.05 * (1 - p_ratio)))

        # Kinetic rate modification (Arrhenius-like)
        if 'reorganization_energy' in adapted:
            rate_factor = 1.0
            if t_avg < 273:
                rate_factor = 0.8  # slower at low T
            elif t_avg > 323:
                rate_factor = 1.2  # faster at high T
            adapted['charge_transfer_rate_factor'] = rate_factor

        adapted['environment'] = profile.name
        return adapted

    def batch_evaluate(self, molecules: Dict[str, Dict[str, float]],
                       environments: List[Environment]
                       ) -> Dict[str, Dict[str, AdaptationResult]]:
        """Evaluate multiple molecules across multiple environments."""
        results = {}
        for mol_name, props in molecules.items():
            results[mol_name] = {}
            for env in environments:
                results[mol_name][env.value] = self.evaluate(
                    mol_name, props, env
                )
        return results

    def generate_report(self,
                        results: Dict[str, Dict[str, AdaptationResult]]) -> str:
        """Generate comparative environment report."""
        lines = [
            "=" * 70,
            "PLANETARY ENVIRONMENT ADAPTATION REPORT",
            "=" * 70, "",
        ]

        for env_name in ['venus', 'mars', 'lunar', 'orbital', 'earth']:
            env_results = {
                mol: r[env_name]
                for mol, r in results.items()
                if env_name in r
            }
            if not env_results:
                continue

            lines.append(f"  {env_name.upper()}")
            lines.append("  " + "-" * 40)
            for mol, result in sorted(
                env_results.items(),
                key=lambda x: x[1].compatibility_score,
                reverse=True
            ):
                score_bar = "#" * int(result.compatibility_score * 20)
                lines.append(
                    f"    {mol}: [{score_bar:<20}] "
                    f"{result.compatibility_score:.2f}"
                )
                for w in result.warnings:
                    lines.append(f"      WARNING: {w}")
            lines.append("")

        report = "\n".join(lines)
        return report
