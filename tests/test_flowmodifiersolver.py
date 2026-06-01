import os
import warnings

import pytest

from aiphoria.core import FlowSolver
from aiphoria.core.datachecker import DataChecker
from aiphoria.core.dataprovider import DataProvider
from aiphoria.core.flowmodifiersolver import FlowModifierSolver, FlowErrorType
from aiphoria.core.parameters import ParameterScenarioType, ParameterName
from aiphoria.core.utils import build_mfa_system_for_scenario, show_model_parameters, calculate_scenario_mass_balance


def get_path_to_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario.xlsx")


def get_path_to_stock_lt_override_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_stock_lt_override.xlsx")


def get_path_to_fms_unconstrained_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_unconstrained.xlsx")


def get_path_to_fms_unconstrained_1_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_unconstrained_1.xlsx")


def get_path_to_fms_unconstrained_abs_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_unconstrained_abs.xlsx")


def get_path_to_fms_unconstrained_rel_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_unconstrained_rel.xlsx")


def get_path_to_fms_constrained_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_constrained.xlsx")

def get_path_to_fms_constrained_abs_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_constrained_abs.xlsx")


def get_path_to_fms_constrained_rel_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_fms_constrained_rel.xlsx")


def get_path_to_output() -> str:
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "test_flowmodifiersolver")


def test_flowmodifiersolver():
    use_cache = False
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)
    datachecker.check_for_errors()

    # Test FlowModifierSolver in "Unconstrained" mode
    scenarios = datachecker.build_scenarios()
    # scenarios[1].model_params[ParameterName.ScenarioType] = ParameterScenarioType.Unconstrained
    for scenario_index, scenario in enumerate(scenarios):
        # NOTE: Baseline scenario is always the first element in the list
        # and all the alternative scenarios (if any) are after that
        if scenario_index == 0:
            # Process baseline scenario
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

    # Test FlowModifierSolver in "Constrained" mode
    scenarios = datachecker.build_scenarios()
    # scenarios[1].model_params[ParameterName.ScenarioType] = ParameterScenarioType.Constrained
    # Test FlowModifierSolver in "Unconstrained" mode
    scenarios = datachecker.build_scenarios()
    # scenarios[1].model_params[ParameterName.ScenarioType] = ParameterScenarioType.Unconstrained
    for scenario_index, scenario in enumerate(scenarios):
        # NOTE: Baseline scenario is always the first element in the list
        # and all the alternative scenarios (if any) are after that
        if scenario_index == 0:
            # Process baseline scenario
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


def test_fms_error_entry():
    # Test empty FlowErrorEntry
    empty_entry = FlowModifierSolver.FlowErrorEntry(year=0,
                                                    total_outflows=0,
                                                    required_outflows=0,
                                                    flow_modifier_index=0)
    assert isinstance(empty_entry.data, dict)

    # Test the FlowErrorEntry properties
    entry = FlowModifierSolver.FlowErrorEntry(year=1234,
                                              total_outflows=10,
                                              required_outflows=20,
                                              flow_modifier_index=1,
                                              error_type=FlowErrorType.NotEnoughOppositeFlowShares,
                                              data={"key": 1000})

    assert entry.year == 1234
    assert entry.outflows_total == 10
    assert entry.outflows_required == 20
    assert entry.flow_modifier_index == 1
    assert entry.error_type == FlowErrorType.NotEnoughOppositeFlowShares
    assert "key" in entry.data
    assert entry.data["key"] == 1000

    # Test replacing reference data
    entry.data = {"new_key": 1234}
    assert "new_key" in entry.data

    # Test replacing error type
    entry.error_type = FlowErrorType.NotEnoughSiblingFlowShares
    assert entry.error_type == FlowErrorType.NotEnoughSiblingFlowShares


def test_flow_change_entry():
    # Test FlowChangeEntry
    entry = FlowModifierSolver.FlowChangeEntry()
    entry_str = str(entry)
    assert entry_str == "FlowChangeEntry: year=0, flow_id=None, value=0.0, evaluated_share=0.0, evaluated_value=0.0, evaluated_offset=0.0, evaluated_share_offset=0.0"


def test_fms_unconstrained():
    path_to_scenario = get_path_to_fms_unconstrained_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)
    datachecker.check_for_errors()

    # Test FlowModifierSolver in "Unconstrained" mode
    scenarios = datachecker.build_scenarios()
    for scenario_index, scenario in enumerate(scenarios):
        # NOTE: Baseline scenario is always the first element in the list
        # and all the alternative scenarios (if any) are after that
        if scenario_index == 0:
            # Process baseline scenario
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


def test_fms_unconstrained_1():
    path_to_scenario = get_path_to_fms_unconstrained_1_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)
    datachecker.check_for_errors()
    scenarios = datachecker.build_scenarios()
    for scenario_index, scenario in enumerate(scenarios):
        # NOTE: Baseline scenario is always the first element in the list
        # and all the alternative scenarios (if any) are after that
        if scenario_index == 0:
            # Process baseline scenario
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


def test_fms_unconstrained_abs():
    with pytest.raises(Exception) as ex_info:
        path_to_scenario = get_path_to_fms_unconstrained_abs_scenario()
        warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
        dataprovider = DataProvider(path_to_scenario)
        datachecker = DataChecker(dataprovider)
        datachecker.check_for_errors()

        scenarios = datachecker.build_scenarios()
        for scenario_index, scenario in enumerate(scenarios):
            # NOTE: Baseline scenario is always the first element in the list
            # and all the alternative scenarios (if any) are after that
            if scenario_index == 0:
                # Process baseline scenario
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


def test_fms_unconstrained_rel():
    with pytest.raises(Exception) as ex_info:
        path_to_scenario = get_path_to_fms_unconstrained_rel_scenario()
        warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
        dataprovider = DataProvider(path_to_scenario)
        datachecker = DataChecker(dataprovider)
        datachecker.check_for_errors()

        scenarios = datachecker.build_scenarios()
        for scenario_index, scenario in enumerate(scenarios):
            # NOTE: Baseline scenario is always the first element in the list
            # and all the alternative scenarios (if any) are after that
            if scenario_index == 0:
                # Process baseline scenario
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


def test_fms_constrained():
    path_to_scenario = get_path_to_fms_constrained_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)
    datachecker.check_for_errors()

    # Test FlowModifierSolver in "Unconstrained" mode
    scenarios = datachecker.build_scenarios()
    for scenario_index, scenario in enumerate(scenarios):
        # NOTE: Baseline scenario is always the first element in the list
        # and all the alternative scenarios (if any) are after that
        if scenario_index == 0:
            # Process baseline scenario
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


def test_fms_constrained_abs():
    with pytest.raises(Exception) as ex_info:
        path_to_scenario = get_path_to_fms_constrained_abs_scenario()
        warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

        # Init Builder without cache and expect that the cache directory does not exists after running init_builder
        dataprovider = DataProvider(path_to_scenario)
        datachecker = DataChecker(dataprovider)
        datachecker.check_for_errors()

        # Test FlowModifierSolver in "Unconstrained" mode
        scenarios = datachecker.build_scenarios()
        for scenario_index, scenario in enumerate(scenarios):
            # NOTE: Baseline scenario is always the first element in the list
            # and all the alternative scenarios (if any) are after that
            if scenario_index == 0:
                # Process baseline scenario
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


def test_fms_constrained_rel():
    with pytest.raises(Exception) as ex_info:
        path_to_scenario = get_path_to_fms_constrained_rel_scenario()
        warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

        # Init Builder without cache and expect that the cache directory does not exists after running init_builder
        dataprovider = DataProvider(path_to_scenario)
        datachecker = DataChecker(dataprovider)
        datachecker.check_for_errors()

        # Test FlowModifierSolver in "Unconstrained" mode
        scenarios = datachecker.build_scenarios()
        for scenario_index, scenario in enumerate(scenarios):
            # NOTE: Baseline scenario is always the first element in the list
            # and all the alternative scenarios (if any) are after that
            if scenario_index == 0:
                # Process baseline scenario
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

