import os
import warnings

import pytest

from aiphoria.core import FlowSolver
from aiphoria.core.datachecker import DataChecker
from aiphoria.core.dataprovider import DataProvider
from aiphoria.core.flowmodifiersolver import FlowModifierSolver, FlowErrorType
from aiphoria.core.parameters import ParameterScenarioType, ParameterName
from aiphoria.core.utils import build_mfa_system_for_scenario, show_model_parameters, calculate_scenario_mass_balance


def get_path_to_flowsolver_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_flowsolver.xlsx")


def get_path_to_flowsolver_virtual_flows_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_flowsolver_virtual_flows.xlsx")

def get_path_to_output() -> str:
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "test_flowmodifiersolver")


def test_flowsolver():
    # Do not expect Exception
    path_to_scenario = get_path_to_flowsolver_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)
    datachecker.check_for_errors()

    scenarios = datachecker.build_scenarios()
    for scenario_index, scenario in enumerate(scenarios):
        if scenario_index == 0:
            baseline_flow_solver = FlowSolver(scenario=scenario)
            baseline_flow_solver.solve_timesteps()
            scenario.flow_solver = baseline_flow_solver
        else:
            # Get and copy solved scenario data from baseline scenario flow solver
            baseline_scenario_data = scenarios[0].flow_solver.get_solved_scenario_data()
            scenario.copy_from_baseline_scenario_data(baseline_scenario_data)

            # Solve this alternative scenario time steps
            scenario_flow_solver = FlowSolver(scenario=scenario, reset_evaluated_values=False)
            scenario_flow_solver.solve_timesteps()
            scenario.flow_solver = scenario_flow_solver

    # Build MFA systems for the scenarios
    for scenario in scenarios:
        scenario.mfa_system = build_mfa_system_for_scenario(scenario)


def test_flowsolver_virtual_flows():
    path_to_scenario = get_path_to_flowsolver_virtual_flows_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)
    datachecker.check_for_errors()

    scenarios = datachecker.build_scenarios()
    for scenario_index, scenario in enumerate(scenarios):
        if scenario_index == 0:
            baseline_flow_solver = FlowSolver(scenario=scenario)
            baseline_flow_solver.solve_timesteps()
            scenario.flow_solver = baseline_flow_solver
        else:
            # Get and copy solved scenario data from baseline scenario flow solver
            baseline_scenario_data = scenarios[0].flow_solver.get_solved_scenario_data()
            scenario.copy_from_baseline_scenario_data(baseline_scenario_data)

            # Solve this alternative scenario time steps
            scenario_flow_solver = FlowSolver(scenario=scenario, reset_evaluated_values=False)
            scenario_flow_solver.solve_timesteps()
            scenario.flow_solver = scenario_flow_solver

    # Build MFA systems for the scenarios
    for scenario in scenarios:
        scenario.mfa_system = build_mfa_system_for_scenario(scenario)

