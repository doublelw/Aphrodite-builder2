"""
Organic synthesis route planning for battery materials.

Suggests synthetic routes, estimates costs, evaluates scalability,
and recommends reaction conditions for target organic battery molecules.

Approach:
  1. From target molecular structure, identify key functional groups
  2. Match against known reaction templates (Suzuki, Knoevenagel, etc.)
  3. Search starting materials availability and pricing
  4. Rank routes by cost, yield, and scalability
  5. Generate detailed experimental protocol
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ReactionType(Enum):
    SUZUKI = "suzuki_coupling"
    KNOEVENAGEL = "knoevenagel_condensation"
    FRIEDEL_CRAFTS = "friedel_crafts"
    ESTERIFICATION = "esterification"
    OXIDATION = "oxidation"
    REDUCTION = "reduction"
    CONDENSATION = "condensation"
    ELECTROCHEMICAL = "electrochemical_polymerization"
    CUSTOM = "custom"


@dataclass
class Reagent:
    name: str
    smiles: str
    cas: str = ""
    price_usd_per_gram: float = 0.0
    purity: str = ">=97%"
    supplier: str = ""
    available: bool = True


@dataclass
class ReactionStep:
    step_number: int
    reaction_type: ReactionType
    reagents: List[Reagent]
    catalyst: Optional[Reagent] = None
    solvent: str = ""
    temperature: str = "rt"
    time: str = "12h"
    atmosphere: str = "N2"
    yield_pct: float = 0.0
    purification: str = ""
    notes: str = ""


@dataclass
class SynthesisRoute:
    """A complete synthesis route for a target molecule."""
    target_name: str
    target_smiles: str
    steps: List[ReactionStep]
    total_yield: float = 0.0
    total_cost_usd: float = 0.0
    cost_per_gram_usd: float = 0.0
    scalability: str = "lab"  # lab / pilot / industrial
    difficulty: int = 1  # 1-5
    green_score: float = 0.0  # 0-1
    time_days: float = 0.0


# Common organic battery functional group → reaction templates
BATTERY_REACTION_TEMPLATES = {
    "quinone": {
        "routes": [
            {
                "type": ReactionType.OXIDATION,
                "name": "Hydroquinone oxidation to quinone",
                "reagents": [{"name": "Hydroquinone", "smiles": "Oc1ccc(O)cc1", "price": 0.05}],
                "conditions": "CrO3/H2SO4 or Fremy's salt, 0C to rt",
                "typical_yield": 85,
            },
            {
                "type": ReactionType.FRIEDEL_CRAFTS,
                "name": "Friedel-Crafts acylation",
                "reagents": [{"name": "Benzene", "smiles": "c1ccccc1", "price": 0.02}],
                "conditions": "AlCl3, acyl chloride, DCM, 0C",
                "typical_yield": 70,
            },
        ],
    },
    "aniline": {
        "routes": [
            {
                "type": ReactionType.REDUCTION,
                "name": "Nitro reduction to aniline",
                "reagents": [{"name": "Nitrobenzene", "smiles": "O=[N+]([O-])c1ccccc1", "price": 0.03}],
                "conditions": "H2/Pd-C or SnCl2/HCl",
                "typical_yield": 95,
            },
        ],
    },
    "imide": {
        "routes": [
            {
                "type": ReactionType.CONDENSATION,
                "name": "Anhydride + amine condensation",
                "conditions": "Acetic acid or DMF, 120-180C",
                "typical_yield": 75,
            },
        ],
    },
    "carboxylate": {
        "routes": [
            {
                "type": ReactionType.ESTERIFICATION,
                "name": "Carboxylic acid + alcohol",
                "conditions": "H2SO4 catalyst, reflux",
                "typical_yield": 80,
            },
        ],
    },
}


class SynthesisPlanner:
    """
    Plan synthesis routes for organic battery materials.

    Usage:
        planner = SynthesisPlanner()
        routes = planner.plan("O=c1ccccc1O", target_voltage=3.5)
        for route in routes:
            print(f"Cost: ${route.cost_per_gram_usd:.2f}/g, "
                  f"Yield: {route.total_yield:.0f}%, "
                  f"Difficulty: {route.difficulty}/5")
    """

    # Cost multipliers for scale
    SCALE_FACTORS = {"lab": 1.0, "pilot": 0.3, "industrial": 0.08}

    def plan(self, target_smiles: str, target_voltage: float = 0.0,
             scale: str = "lab") -> List[SynthesisRoute]:
        """
        Generate synthesis routes for target molecule.

        Analyzes molecular structure, identifies functional groups,
        and proposes synthetic routes with cost estimates.
        """
        functional_groups = self._identify_groups(target_smiles)
        routes = []

        for fg in functional_groups:
            templates = BATTERY_REACTION_TEMPLATES.get(fg, {}).get("routes", [])
            for template in templates:
                route = self._build_route(
                    target_smiles, template, scale
                )
                routes.append(route)

        routes.sort(key=lambda r: r.cost_per_gram_usd)

        return routes

    def _identify_groups(self, smiles: str) -> List[str]:
        """Identify functional groups from SMILES."""
        groups = []
        if "=O" in smiles and ("c1" in smiles or "C(" in smiles):
            groups.append("quinone")
        if "NH2" in smiles or "N" in smiles:
            groups.append("aniline")
        if "C(=O)NC" in smiles or "C(=O)N" in smiles:
            groups.append("imide")
        if "C(=O)O" in smiles or "COOH" in smiles:
            groups.append("carboxylate")
        if not groups:
            groups.append("custom")
        return groups

    def _build_route(self, target_smiles: str, template: dict,
                     scale: str) -> SynthesisRoute:
        """Build a SynthesisRoute from a template."""
        reagents = []
        for r in template.get("reagents", []):
            reagents.append(Reagent(
                name=r.get("name", "Unknown"),
                smiles=r.get("smiles", ""),
                price_usd_per_gram=r.get("price", 0.1),
            ))

        catalyst = None
        if "AlCl3" in template.get("conditions", ""):
            catalyst = Reagent(name="AlCl3", smiles="...", price_usd_per_gram=0.02)
        elif "Pd" in template.get("conditions", ""):
            catalyst = Reagent(name="Pd/C", smiles="...", price_usd_per_gram=5.0)

        step = ReactionStep(
            step_number=1,
            reaction_type=template.get("type", ReactionType.CUSTOM),
            reagents=reagents,
            catalyst=catalyst,
            solvent="",
            temperature="rt",
            yield_pct=template.get("typical_yield", 70),
            notes=template.get("conditions", ""),
        )

        total_cost = sum(r.price_usd_per_gram for r in reagents)
        if catalyst:
            total_cost += catalyst.price_usd_per_gram * 0.1  # catalyst loading
        scale_factor = self.SCALE_FACTORS.get(scale, 1.0)
        total_cost *= scale_factor

        return SynthesisRoute(
            target_name=target_smiles[:20],
            target_smiles=target_smiles,
            steps=[step],
            total_yield=step.yield_pct / 100.0,
            total_cost_usd=total_cost,
            cost_per_gram_usd=total_cost / (step.yield_pct / 100.0),
            scalability=scale,
            difficulty=2,
        )

    def generate_protocol(self, route: SynthesisRoute) -> str:
        """Generate detailed experimental protocol."""
        lines = [
            f"Synthesis Protocol: {route.target_name}",
            f"{'=' * 50}",
            f"Target: {route.target_smiles}",
            f"Estimated cost: ${route.cost_per_gram_usd:.2f}/g",
            f"Expected yield: {route.total_yield:.0%}",
            f"Scalability: {route.scalability}",
            f"Difficulty: {'*' * route.difficulty}",
            "",
        ]

        for step in route.steps:
            lines.append(f"Step {step.step_number}: {step.reaction_type.value}")
            lines.append("-" * 30)
            lines.append(f"  Reagents:")
            for r in step.reagents:
                lines.append(f"    - {r.name} (purity {r.purity})")
            if step.catalyst:
                lines.append(f"  Catalyst: {step.catalyst.name}")
            lines.append(f"  Conditions: {step.notes}")
            lines.append(f"  Expected yield: {step.yield_pct:.0f}%")
            lines.append("")

        lines.append("Characterization:")
        lines.append("  - 1H NMR (CDCl3, 400 MHz)")
        lines.append("  - 13C NMR (CDCl3, 100 MHz)")
        lines.append("  - FT-IR (KBr pellet)")
        lines.append("  - HRMS (ESI)")
        lines.append("  - CV (0.1M TBAPF6/ACN, glassy carbon)")

        return "\n".join(lines)
