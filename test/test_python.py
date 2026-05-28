"""
L3: Python Unit Tests — all modules, no external dependencies.

Tests synthesis planner, cell architect, BMS algorithms,
experimental methods, integration process, backends, AI interface.
"""
import sys
import os
import json
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PASS = 0
FAIL = 0
RESULTS = []


def test(name, func):
    global PASS, FAIL
    try:
        func()
        PASS += 1
        RESULTS.append(('PASS', name))
        print(f"  ::ok {name}")
    except Exception as e:
        FAIL += 1
        RESULTS.append(('FAIL', name, str(e)))
        print(f"  ::fail {name} — {e}")


# ─── Synthesis Planner ───

def test_synthesis_plan_quinone():
    from src.synthesis.planner import SynthesisPlanner
    planner = SynthesisPlanner()
    routes = planner.plan("O=c1ccccc1O", scale="lab")
    assert len(routes) > 0, "No routes found for quinone"
    assert routes[0].total_yield > 0, "Yield should be > 0"
    assert routes[0].cost_per_gram_usd > 0, "Cost should be > 0"


def test_synthesis_protocol():
    from src.synthesis.planner import SynthesisPlanner
    planner = SynthesisPlanner()
    routes = planner.plan("O=c1ccccc1O")
    protocol = planner.generate_protocol(routes[0])
    assert "Reagents:" in protocol
    assert "Characterization:" in protocol
    assert "NMR" in protocol


def test_synthesis_scale_factor():
    from src.synthesis.planner import SynthesisPlanner
    planner = SynthesisPlanner()
    lab_routes = planner.plan("O=c1ccccc1O", scale="lab")
    ind_routes = planner.plan("O=c1ccccc1O", scale="industrial")
    assert lab_routes[0].total_cost_usd > ind_routes[0].total_cost_usd


# ─── Cell Architect ───

def test_cell_design_basic():
    from src.cell_design.architect import CellArchitect, CellFormat
    arch = CellArchitect()
    cell = arch.design_cell("quinone_A", voltage=3.7, capacity_mAh_g=250)
    assert cell.voltage_avg == 3.7
    assert cell.energy_density_wh_kg > 0
    assert cell.estimated_cycles > 0


def test_cell_design_venus():
    from src.cell_design.architect import CellArchitect
    arch = CellArchitect()
    cell = arch.design_cell("venin_A", voltage=3.2, capacity_mAh_g=180,
                            environment="venus")
    assert "CO2" in cell.electrolyte.solvent or "CO2" in cell.electrolyte.notes


def test_cell_compare():
    from src.cell_design.architect import CellArchitect, CellFormat
    arch = CellArchitect()
    cells = [
        arch.design_cell(f"mol_{i}", voltage=3.0 + i * 0.3, capacity_mAh_g=200 + i * 30)
        for i in range(3)
    ]
    report = arch.compare_designs(cells)
    assert "mol_0" in report
    assert "mol_2" in report


def test_electrolyte_types():
    from src.cell_design.architect import STANDARD_ELECTROLYTES
    assert "standard" in STANDARD_ELECTROLYTES
    assert "venus_co2" in STANDARD_ELECTROLYTES
    assert "aqueous" in STANDARD_ELECTROLYTES


# ─── BMS ───

def test_soc_coulomb():
    from src.bms.algorithms import SOCEstimator, BMSConfig
    config = BMSConfig(cell_capacity_mAh=250)
    est = SOCEstimator(config)
    soc = est.coulomb_counting(0.5, 0.1, 1.0)  # 100mA for 1h
    assert 0 < soc < 1.0


def test_soc_ocv():
    from src.bms.algorithms import SOCEstimator, BMSConfig
    config = BMSConfig()
    est = SOCEstimator(config)
    soc = est.ocv_to_soc(3.8, "organic")
    assert 0 < soc < 1.0


def test_soh_degradation():
    from src.bms.algorithms import SOHTracker, BMSConfig
    config = BMSConfig()
    tracker = SOHTracker(config)
    soh = tracker.update_soh(1.0, 100)
    assert soh < 1.0
    assert soh > 0.9


def test_soh_remaining_cycles():
    from src.bms.algorithms import SOHTracker, BMSConfig
    config = BMSConfig()
    tracker = SOHTracker(config)
    remaining = tracker.remaining_cycles(0.95)
    assert remaining > 0


def test_cell_balancing():
    from src.bms.algorithms import CellBalancer, CellState, BMSConfig
    config = BMSConfig(balance_threshold_mV=50)
    balancer = CellBalancer(config)
    cells = [
        CellState(cell_id=0, voltage=3.7, current=0, temperature=25, soc=0.5, soh=1.0, internal_resistance=50),
        CellState(cell_id=1, voltage=3.8, current=0, temperature=25, soc=0.6, soh=1.0, internal_resistance=50),
        CellState(cell_id=2, voltage=3.6, current=0, temperature=25, soc=0.4, soh=1.0, internal_resistance=50),
    ]
    actions = balancer.check_balance(cells)
    assert len(actions) > 0


def test_thermal_check():
    from src.bms.algorithms import ThermalManager, CellState, BMSConfig
    config = BMSConfig(max_temperature=55)
    tm = ThermalManager(config)
    cells = [CellState(cell_id=0, voltage=3.7, current=2.0, temperature=60, soc=0.5, soh=1.0, internal_resistance=50)]
    result = tm.check_thermal(cells)
    assert result['status'] == 'critical'


# ─── Experimental Methods ───

def test_experimental_suite():
    from src.experimental.methods import ExperimentalDesigner
    designer = ExperimentalDesigner()
    methods = designer.design_battery_test_suite("quinone_A", voltage=3.7)
    assert len(methods) >= 5
    types = [m.test_type.value for m in methods]
    assert "cyclic_voltammetry" in types
    assert "cycle_life" in types


def test_experimental_protocol_doc():
    from src.experimental.methods import ExperimentalDesigner
    designer = ExperimentalDesigner()
    methods = designer.design_battery_test_suite("mol_A", voltage=3.5)
    doc = designer.generate_protocol_document(methods)
    assert "BATTERY EXPERIMENTAL PROTOCOL" in doc
    assert "Equipment:" in doc
    assert "Safety:" in doc


def test_experimental_cv_params():
    from src.experimental.methods import ExperimentalDesigner
    designer = ExperimentalDesigner()
    methods = designer.design_battery_test_suite("mol_A")
    cv = next(m for m in methods if m.test_type.value == "cyclic_voltammetry")
    assert "scan_rate" in cv.parameters
    assert cv.estimated_cost_usd > 0


# ─── Integration / Manufacturing ───

def test_manufacturing_lab():
    from src.integration.process import IntegrationEngine, ProductionScale
    engine = IntegrationEngine()
    process = engine.design_process(ProductionScale.LAB)
    assert len(process.steps) >= 5
    assert process.opex_usd_per_kwh > 0
    assert process.capex_usd > 0


def test_manufacturing_comparison():
    from src.integration.process import IntegrationEngine
    engine = IntegrationEngine()
    report = engine.scale_comparison()
    assert "lab" in report
    assert "industrial" in report
    assert "$" in report  # has dollar amounts
    assert "50" in report  # has lab CAPEX


def test_manufacturing_industrial_cheaper():
    from src.integration.process import IntegrationEngine, ProductionScale
    engine = IntegrationEngine()
    lab = engine.design_process(ProductionScale.LAB)
    ind = engine.design_process(ProductionScale.INDUSTRIAL)
    assert ind.opex_usd_per_kwh < lab.opex_usd_per_kwh


# ─── Backends ───

def test_backend_detection():
    from src.backends.engine import QuantumEngine
    engine = QuantumEngine()
    backends = engine.available_backends()
    # At minimum, should not crash
    assert isinstance(backends, list)


def test_molecule_spec():
    from src.backends.engine import MoleculeSpec
    mol = MoleculeSpec(
        atoms=[('C', 0, 0, 0), ('O', 1.14, 0, 0)],
        name="test",
    )
    xyz = mol.to_xyz()
    assert "2" in xyz  # 2 atoms
    assert "C" in xyz
    assert "O" in xyz


def test_parser_manual():
    from src.backends.parser import OutputParser
    parser = OutputParser()
    result = parser._parse_manual("/nonexistent/file.out")
    assert result.source == "/nonexistent/file.out"


# ─── AI Interface ───

def test_ai_config_structure():
    from src.ai_interface import AIConfig, PROVIDERS
    config = AIConfig(provider="deepseek")
    assert config.get_effective_model() == "deepseek-chat"
    assert config.provider == "deepseek"
    assert len(PROVIDERS) == 3


def test_ai_config_claude():
    from src.ai_interface import AIConfig
    config = AIConfig(provider="claude")
    assert "claude" in config.get_effective_model()


# ─── Run ───

if __name__ == '__main__':
    print("\n=== L3: Python Unit Tests ===\n")

    test("synthesis_plan_quinone", test_synthesis_plan_quinone)
    test("synthesis_protocol", test_synthesis_protocol)
    test("synthesis_scale_factor", test_synthesis_scale_factor)
    test("cell_design_basic", test_cell_design_basic)
    test("cell_design_venus", test_cell_design_venus)
    test("cell_compare", test_cell_compare)
    test("electrolyte_types", test_electrolyte_types)
    test("soc_coulomb", test_soc_coulomb)
    test("soc_ocv", test_soc_ocv)
    test("soh_degradation", test_soh_degradation)
    test("soh_remaining_cycles", test_soh_remaining_cycles)
    test("cell_balancing", test_cell_balancing)
    test("thermal_check", test_thermal_check)
    test("experimental_suite", test_experimental_suite)
    test("experimental_protocol_doc", test_experimental_protocol_doc)
    test("experimental_cv_params", test_experimental_cv_params)
    test("manufacturing_lab", test_manufacturing_lab)
    test("manufacturing_comparison", test_manufacturing_comparison)
    test("manufacturing_industrial_cheaper", test_manufacturing_industrial_cheaper)
    test("backend_detection", test_backend_detection)
    test("molecule_spec", test_molecule_spec)
    test("parser_manual", test_parser_manual)
    test("ai_config_structure", test_ai_config_structure)
    test("ai_config_claude", test_ai_config_claude)

    print(f"\n  L3 Results: {PASS} passed, {FAIL} failed")
    sys.exit(FAIL)
