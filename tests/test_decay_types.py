# Tests for stock lifetimes and decay stock types (Simple, LandfillDecayWood, LandfillDecayPaper)
import os
import warnings

import openpyxl
import pytest

from aiphoria.core import FlowSolver
from aiphoria.core.datachecker import DataChecker
from aiphoria.core.dataprovider import DataProvider


def get_path_to_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")


def solve_with_construction_stock(tmp_path, lifetime, distribution_type, distribution_params):
    """
    Copy the example scenario (10 years, 2021-2030), change the stock of process Construction,
    solve the baseline scenario and return the total stock of Construction for each year.
    """
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    wb = openpyxl.load_workbook(get_path_to_reference_scenario(), data_only=True)
    for row in wb["Processes"].iter_rows():
        if row[1].value == "Construction":
            row[5].value = lifetime
            row[6].value = distribution_type
            row[7].value = distribution_params

    path = os.path.join(tmp_path, "scenario_decay.xlsx")
    wb.save(path)

    datachecker = DataChecker(DataProvider(path))
    scenarios = datachecker.build_scenarios()
    datachecker.check_for_errors()
    flow_solver = FlowSolver(scenario=scenarios[0])
    flow_solver.solve_timesteps()
    return flow_solver.get_baseline_dynamic_stocks()["Construction:FI"].s


@pytest.mark.parametrize("distribution_type, distribution_params", [
    ("Simple", None),
    ("Normal", "stddev=1"),
    ("Fixed", None),
])
def test_lifetime_longer_than_simulation(tmp_path, distribution_type, distribution_params):
    # Lifetime 50 in a 10-year simulation is allowed for all distribution types
    stock = solve_with_construction_stock(tmp_path, 50, distribution_type, distribution_params)
    assert stock[-1] > 0


def test_negative_lifetime_is_error(tmp_path):
    # Negative lifetime must still stop the run
    with pytest.raises(Exception, match="negative stock lifetime"):
        solve_with_construction_stock(tmp_path, -5, "Simple", None)


@pytest.mark.parametrize("distribution_type", ["LandfillDecayWood", "LandfillDecayPaper"])
def test_landfill_condition_changes_decay(tmp_path, distribution_type):
    # Faster decay in Wet and Managed landfills -> less stock left than in Dry
    dry = solve_with_construction_stock(tmp_path, 0, distribution_type, "condition=Dry")[-1]
    wet = solve_with_construction_stock(tmp_path, 0, distribution_type, "condition=Wet")[-1]
    managed = solve_with_construction_stock(tmp_path, 0, distribution_type, "condition=Managed")[-1]
    assert dry > wet > managed
