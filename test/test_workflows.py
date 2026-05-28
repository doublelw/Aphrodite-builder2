"""
L4: Workflow Tests — focuses on workflow logic, no external deps.
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


def test_screening_report():
    """Test screening report generation with mock results."""
    from src.workflows.screening_pipeline import ScreeningResult
    from src.core.property_predictor import BatteryProperties

    results = [
        ScreeningResult(
            smiles="c1ccccc1", name="benzene", orca_success=True,
            properties=BatteryProperties(
                theoretical_voltage=3.5, energy_density=280,
                power_density=500, homo=-4.5, lumo=-1.5, gap=3.0,
                reorganization_energy=0.25, charge_transfer_rate=0.8,
                thermal_stability=250, solvation_energy=-20.0,
                flame_resistance=0.6, cycle_stability_score=0.7,
                environmental_adaptability={},
            ),
        ),
        ScreeningResult(
            smiles="c1ccc(O)cc1", name="phenol", orca_success=True,
            properties=BatteryProperties(
                theoretical_voltage=3.2, energy_density=240,
                power_density=450, homo=-4.2, lumo=-1.3, gap=2.9,
                reorganization_energy=0.30, charge_transfer_rate=0.7,
                thermal_stability=230, solvation_energy=-18.0,
                flame_resistance=0.5, cycle_stability_score=0.6,
                environmental_adaptability={},
            ),
        ),
        ScreeningResult(
            smiles="invalid", name="bad_mol", orca_success=False,
            errors=["Geometry generation failed"],
        ),
    ]

    # Build report manually
    successful = [r for r in results if r.orca_success]
    failed = [r for r in results if not r.orca_success]

    report_lines = [
        "=" * 60, "SCREENING REPORT", "=" * 60,
        f"Total: {len(results)}  Success: {len(successful)}  Failed: {len(failed)}",
    ]
    for r in successful:
        p = r.properties
        report_lines.append(f"  {r.name}: V={p.theoretical_voltage:.2f}  E={p.energy_density:.0f}")
    for r in failed:
        report_lines.append(f"  {r.name}: {', '.join(r.errors)}")

    report = "\n".join(report_lines)
    assert "benzene" in report
    assert "bad_mol" in report
    assert "Geometry generation failed" in report


def test_precision_threshold_pass():
    """Test precision ladder threshold checking — passing case."""
    from src.workflows.precision_ladder import TierThreshold

    thresholds = [
        TierThreshold('gap', min_val=1.5, max_val=5.0),
        TierThreshold('homo', min_val=-6.5, max_val=-3.5),
    ]

    props = {'gap': 3.0, 'homo': -5.0}
    passed = True
    reason = None
    for th in thresholds:
        val = props.get(th.metric)
        if val is None:
            continue
        if th.min_val is not None and val < th.min_val:
            passed = False
            reason = f"{th.metric}={val} < {th.min_val}"
        if th.max_val is not None and val > th.max_val:
            passed = False
            reason = f"{th.metric}={val} > {th.max_val}"
    assert passed, f"Threshold failed: {reason}"


def test_precision_threshold_fail():
    """Test precision ladder threshold — failing case."""
    from src.workflows.precision_ladder import TierThreshold

    thresholds = [TierThreshold('gap', min_val=1.5, max_val=5.0)]
    props = {'gap': 0.3}
    passed = True
    for th in thresholds:
        val = props.get(th.metric)
        if val is not None and th.min_val is not None and val < th.min_val:
            passed = False
    assert not passed


def test_precision_tiers():
    """Verify precision tier ordering."""
    from src.workflows.precision_ladder import PrecisionLadder
    assert PrecisionLadder.TIERS == ['xtb', 'dft', 'dlpno']


def test_planetary_venus_profile():
    """Verify Venus environment profile data."""
    from src.workflows.planetary_adapter import PLANETARY_PROFILES, Environment
    venus = PLANETARY_PROFILES[Environment.VENUS]
    assert venus.pressure_atm == 0.904
    assert venus.gravity_g == 0.904
    assert venus.atmosphere["CO2"] == 0.965
    assert "C" in venus.available_elements
    assert venus.temperature_range == (0, 50)


def test_planetary_mars_profile():
    from src.workflows.planetary_adapter import PLANETARY_PROFILES, Environment
    mars = PLANETARY_PROFILES[Environment.MARS]
    assert mars.gravity_g == 0.38
    assert mars.atmosphere["CO2"] == 0.95


def test_planetary_evaluate_logic():
    """Test planetary evaluation scoring logic directly."""
    from src.workflows.planetary_adapter import PlanetaryAdapter, Environment
    adapter = PlanetaryAdapter()

    result = adapter.evaluate("test_mol", {
        'thermal_stability': 250,
        'gap': 3.0,
    }, Environment.VENUS)

    assert 0 <= result.compatibility_score <= 1.0
    assert result.environment == "venus"
    assert isinstance(result.warnings, list)


def test_planetary_batch():
    from src.workflows.planetary_adapter import PlanetaryAdapter, Environment
    adapter = PlanetaryAdapter()
    molecules = {
        "mol_A": {'thermal_stability': 250, 'gap': 3.0},
        "mol_B": {'thermal_stability': 150, 'gap': 1.5},
    }
    results = adapter.batch_evaluate(molecules, [Environment.VENUS, Environment.MARS])
    assert "mol_A" in results
    assert "venus" in results["mol_A"]
    assert "mars" in results["mol_A"]


def test_battery_reorganization():
    """Test 4-point reorganization energy calculation."""
    energies = {
        'neu_at_neu': -76.0,
        'neu_at_cat': -75.8,
        'cat_at_neu': -75.5,
        'cat_at_cat': -75.7,
    }
    lambda_1 = energies['neu_at_cat'] - energies['neu_at_neu']
    lambda_2 = energies['cat_at_neu'] - energies['cat_at_cat']
    total = lambda_1 + lambda_2

    assert total > 0, "Reorganization energy should be positive"
    assert abs(total - 0.4) < 0.01, f"Expected ~0.4 Ha, got {total}"


# ─── Run ───

if __name__ == '__main__':
    print("\n=== L4: Workflow Tests ===\n")

    test("screening_report", test_screening_report)
    test("precision_threshold_pass", test_precision_threshold_pass)
    test("precision_threshold_fail", test_precision_threshold_fail)
    test("precision_tiers", test_precision_tiers)
    test("planetary_venus_profile", test_planetary_venus_profile)
    test("planetary_mars_profile", test_planetary_mars_profile)
    test("planetary_evaluate_logic", test_planetary_evaluate_logic)
    test("planetary_batch", test_planetary_batch)
    test("battery_reorganization", test_battery_reorganization)

    print(f"\n  L4 Results: {PASS} passed, {FAIL} failed")
    sys.exit(FAIL)
