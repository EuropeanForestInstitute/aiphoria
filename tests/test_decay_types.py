# Tests for stock lifetimes and decay stock types (Simple, LandfillDecayWood, LandfillDecayPaper)
import os
import warnings

import numpy as np
import openpyxl
import pytest

from aiphoria.core import FlowSolver
from aiphoria.core.datachecker import DataChecker
from aiphoria.core.dataprovider import DataProvider
from aiphoria.lib.odym.modules.dynamic_stock_model import DynamicStockModel


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


# ****************************************
# * Simple decay compared with IPCC HWP  *
# ****************************************
def solve_simple_dsm(inflow: np.ndarray, lifetime: int) -> DynamicStockModel:
    """
    Build and solve DynamicStockModel with Simple decay (k = 1 / lifetime).
    """
    dsm = DynamicStockModel(t=np.arange(len(inflow)), i=inflow, lt={"Type": "Simple", "Mean": [lifetime]})
    dsm.compute_s_c_inflow_driven()
    dsm.compute_o_c_from_s_c()
    dsm.compute_stock_total()
    dsm.compute_outflow_total()
    return dsm


def ipcc_first_order_decay(inflow: np.ndarray, half_life: float) -> np.ndarray:
    """
    IPCC first-order decay for HWP (IPCC 2006 Vol. 4 Ch. 12, Eq. 12.1):
    C(i+1) = exp(-k) * C(i) + [(1 - exp(-k)) / k] * Inflow(i), with k = ln(2) / half-life
    Returns stock at the end of each year.
    """
    k = np.log(2) / half_life
    stock = 0.0
    result = []
    for value in inflow:
        stock = np.exp(-k) * stock + (1 - np.exp(-k)) / k * value
        result.append(stock)
    return np.array(result)


def test_simple_decay_uses_mean_lifetime():
    # Share of an inflow still in stock after t years is exp(-t / Lifetime)
    lifetime = 50
    inflow = np.zeros(100)
    inflow[0] = 1.0
    dsm = solve_simple_dsm(inflow, lifetime)
    np.testing.assert_allclose(dsm.s, np.exp(-np.arange(100) / lifetime))


@pytest.mark.parametrize("half_life", [35, 25])
def test_simple_decay_with_converted_half_life_close_to_ipcc(half_life):
    # Half-life converted to mean lifetime (Lifetime = half-life / ln(2), rounded)
    # gives stocks within 2% of the IPCC equation for long lifetimes (here 50 and 36 years).
    # Short lifetimes are not tested: aiphoria adds the whole inflow at once while IPCC spreads it over the year, so the stock differs by about 1 / (2 x Lifetime), ~20% for 2-3 years.
    lifetime = int(round(half_life / np.log(2)))
    inflow = np.ones(200)
    aiphoria_stock = solve_simple_dsm(inflow, lifetime).s
    ipcc_stock = ipcc_first_order_decay(inflow, half_life)
    np.testing.assert_allclose(aiphoria_stock[10:], ipcc_stock[10:], rtol=0.02)
