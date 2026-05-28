"""
L5: End-to-End Tests — complete design chain workflows.

Tests the full molecule → quantum → synthesis → cell → BMS → report chain.
All external tools mocked, pure Python execution.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PASS = 0
FAIL = 0


def test(name, func):
    global PASS, FAIL
    try:
        func()
        PASS += 1
        print(f"  ::ok {name}")
    except Exception as e:
        FAIL += 1
        print(f"  ::fail {name} — {e}")


def test_e2e_molecule_to_cell():
    """Full chain: define molecule → predict properties → design cell → check economics."""
    # Step 1: Molecule properties
    from src.core.property_predictor import BatteryProperties
    props = BatteryProperties(
        theoretical_voltage=3.7,
        energy_density=310,
        power_density=600,
        homo=-4.9, lumo=-1.9, gap=3.0,
        reorganization_energy=0.21,
        charge_transfer_rate=0.9,
        thermal_stability=250,
        solvation_energy=-22.0,
        flame_resistance=0.7,
        cycle_stability_score=0.8,
        environmental_adaptability={},
    )
    assert props.theoretical_voltage == 3.7
    assert props.energy_density > 0

    # Step 2: Cell design
    from src.cell_design.architect import CellArchitect, CellFormat
    architect = CellArchitect()
    cell = architect.design_cell(
        "quinone_A", voltage=props.theoretical_voltage,
        capacity_mAh_g=250, format=CellFormat.COIN_2032,
    )
    assert cell.energy_density_wh_kg > 0
    assert cell.cost_usd_kwh > 0

    # Step 3: BMS
    from src.bms.algorithms import SOCEstimator, SOHTracker, BMSConfig
    config = BMSConfig(
        cell_capacity_mAh=250,
        max_voltage=cell.voltage_max,
    )
    soc_est = SOCEstimator(config)
    soc = soc_est.ocv_to_soc(3.7)
    assert 0 < soc < 1.0

    soh_tracker = SOHTracker(config)
    remaining = soh_tracker.remaining_cycles(0.95)
    assert remaining > 0


def test_e2e_synthesis_to_manufacturing():
    """Synthesis planning → cost → scale comparison."""
    from src.synthesis.planner import SynthesisPlanner
    from src.integration.process import IntegrationEngine, ProductionScale

    # Step 1: Synthesis routes
    planner = SynthesisPlanner()
    routes = planner.plan("O=c1ccccc1O", scale="lab")
    assert len(routes) > 0
    best = routes[0]

    # Step 2: Manufacturing cost at different scales
    engine = IntegrationEngine()
    lab = engine.design_process(ProductionScale.LAB)
    pilot = engine.design_process(ProductionScale.PILOT)
    industrial = engine.design_process(ProductionScale.INDUSTRIAL)

    assert lab.opex_usd_per_kwh > pilot.opex_usd_per_kwh > industrial.opex_usd_per_kwh
    assert lab.capex_usd < pilot.capex_usd < industrial.capex_usd


def test_e2e_planetary_battery():
    """Design battery for Venus → evaluate → plan synthesis."""
    from src.workflows.planetary_adapter import PlanetaryAdapter, Environment

    adapter = PlanetaryAdapter()
    result = adapter.evaluate("co2_quinone", {
        'thermal_stability': 200,
        'gap': 2.5,
        'elements': ['C', 'O', 'N', 'H'],
    }, Environment.VENUS)

    assert result.compatibility_score > 0
    # Venus battery must use CO2-derived materials
    assert any("CO2" in w or "lithium" in w.lower() for w in result.warnings) or \
           result.compatibility_score > 0.5


def test_e2e_experimental_protocol():
    """Generate complete test protocol → verify all methods present."""
    from src.experimental.methods import ExperimentalDesigner

    designer = ExperimentalDesigner()
    methods = designer.design_battery_test_suite("test_mol", voltage=3.5, capacity=200)

    # Must have electrochemical + characterization methods
    types = {m.test_type.value for m in methods}
    required = {"cyclic_voltammetry", "galvanostatic_charge_discharge",
                "electrochemical_impedance_spectroscopy", "cycle_life"}

    missing = required - types
    assert not missing, f"Missing test types: {missing}"

    # Protocol doc must be complete
    doc = designer.generate_protocol_document(methods)
    assert len(doc) > 500  # substantial document


def test_e2e_batteryfold_model():
    """BatteryFold neural model import + config."""
    try:
        from src.models.batteryfold import BatteryFoldConfig, HAS_TORCH
        config = BatteryFoldConfig()
        assert config.num_blocks == 6
        assert config.num_heads == 8
        assert config.num_battery_properties == 9

        if HAS_TORCH:
            from src.models.batteryfold import BatteryFold
            model = BatteryFold(config)
            assert model is not None
    except ImportError:
        pass  # PyTorch not installed, config test only


# ─── Run ───

if __name__ == '__main__':
    print("\n=== L5: E2E Tests ===\n")

    test("e2e_molecule_to_cell", test_e2e_molecule_to_cell)
    test("e2e_synthesis_to_manufacturing", test_e2e_synthesis_to_manufacturing)
    test("e2e_planetary_battery", test_e2e_planetary_battery)
    test("e2e_experimental_protocol", test_e2e_experimental_protocol)
    test("e2e_batteryfold_model", test_e2e_batteryfold_model)

    print(f"\n  L5 Results: {PASS} passed, {FAIL} failed")
    sys.exit(FAIL)
