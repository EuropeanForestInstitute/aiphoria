import os
import warnings
from aiphoria.core import FlowSolver
from aiphoria.core.datachecker import DataChecker
from aiphoria.core.dataprovider import DataProvider
from aiphoria.core.flowmodifiersolver import FlowModifierSolver
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


    # use_cache = False
    # path_to_scenario = get_path_to_reference_scenario()
    # path_to_output = get_path_to_output()
    #
    # # Ignore openpyxl warning about Data validation extension support, we are not using that
    # warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    #
    # # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    # dataprovider = DataProvider(path_to_scenario)
    # datachecker = DataChecker(dataprovider)
    # datachecker.check_for_errors()
    #
    # # Test FlowModifierSolver in "Unconstrained" mode
    # scenarios = datachecker.build_scenarios()
    # scenarios[1].model_params[ParameterName.ScenarioType] = ParameterScenarioType.Constrained
    # for scenario_index, scenario in enumerate(scenarios):
    #     # NOTE: Baseline scenario is always the first element in the list
    #     # and all the alternative scenarios (if any) are after that
    #     if scenario_index == 0:
    #         # Process baseline scenario
    #         baseline_flow_solver = FlowSolver(scenario=scenario)
    #         baseline_flow_solver.solve_timesteps()
    #         scenario.flow_solver = baseline_flow_solver
    #     else:
    #         # Get and copy solved scenario data from baseline scenario flow solver
    #         baseline_scenario_data = scenarios[0].flow_solver.get_solved_scenario_data()
    #         scenario.copy_from_baseline_scenario_data(baseline_scenario_data)
    #
    #         # Solve this alternative scenario time steps
    #         scenario_flow_solver = FlowSolver(scenario=scenario, reset_evaluated_values=False)
    #         scenario_flow_solver.solve_timesteps()
    #         scenario.flow_solver = scenario_flow_solver
    #
    # # Build MFA systems for the scenarios
    # for scenario in scenarios:
    #     scenario.mfa_system = build_mfa_system_for_scenario(scenario)
    #

# import sys
# import pytest
# from unittest.mock import Mock, patch
#
# # Adjust this import to your actual module path
# from aiphoria.core.flowmodifiersolver import FlowModifierSolver, FlowErrorType, ParameterScenarioType
#
# # --------------------------------------------------
# # 🔧 Fixtures
# # --------------------------------------------------
#
#
# @pytest.fixture
# def mock_flow_solver():
#     solver = Mock()
#
#     # Scenario mock
#     scenario = Mock()
#     scenario.scenario_definition.flow_modifiers = []
#     scenario.scenario_data.years = [2020]
#
#     solver.get_scenario.return_value = scenario
#
#     # Defaults
#     solver.get_process_outflows_total_abs.return_value = 100.0
#     solver.get_process_outflows_total_rel.return_value = 100.0
#
#     solver.clamp_flow_values_below_zero = Mock()
#
#     return solver
#
#
# @pytest.fixture
# def simple_absolute_flow():
#     flow = Mock()
#     flow.id = "f1"
#     flow.is_unit_absolute_value = True
#     flow.value = 100.0
#     flow.evaluated_value = 100.0
#     flow.evaluated_share = 1.0
#     return flow
#
#
# @pytest.fixture
# def simple_relative_flows():
#     f1 = Mock()
#     f1.id = "f1"
#     f1.is_unit_absolute_value = False
#     f1.value = 50.0
#     f1.evaluated_value = 50.0
#     f1.evaluated_share = 0.5
#
#     f2 = Mock()
#     f2.id = "f2"
#     f2.is_unit_absolute_value = False
#     f2.value = 50.0
#     f2.evaluated_value = 50.0
#     f2.evaluated_share = 0.5
#
#     return f1, f2
#
#
# def make_modifier(target_flow_id="f1"):
#     m = Mock()
#     m.source_process_id = "p1"
#     m.target_flow_id = target_flow_id
#     m.start_year = 2020
#     m.row_number = 1
#     m.use_change_in_value = True
#     return m
#
#
# # --------------------------------------------------
# # ✅ Basic execution
# # --------------------------------------------------
#
# def test_unconstrained_runs_successfully(mock_flow_solver):
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     ok, errors = solver._solve_unconstrained_scenario()
#
#     assert ok is True
#     assert errors == []
#
#
# # --------------------------------------------------
# # 🔢 Absolute flow tests
# # --------------------------------------------------
#
# def test_absolute_flow_is_updated(mock_flow_solver, simple_absolute_flow):
#     mock_flow_solver.get_flow.return_value = simple_absolute_flow
#
#     modifier = make_modifier("f1")
#     scenario = mock_flow_solver.get_scenario()
#     scenario.scenario_definition.flow_modifiers = [modifier]
#
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     # Mock internal behavior
#     solver._calculate_new_flow_values = Mock(return_value=(
#         {2020: 200.0},  # new value
#         {2020: 0.0}
#     ))
#
#     solver._process_absolute_flows = Mock(return_value=(
#         {},  # no errors
#         {
#             0: [
#                 FlowModifierSolver.FlowChangeEntry(
#                     year=2020,
#                     flow_id="f1",
#                     value=200.0,
#                     evaluated_value=200.0,
#                     evaluated_share=1.0
#                 )
#             ]
#         }
#     ))
#
#     solver._process_relative_flows = Mock(return_value=({}, {}))
#     solver._check_flow_modifier_changes = Mock()
#     solver._recalculate_relative_flow_evaluated_shares = Mock()
#     solver._check_flow_modifier_results = Mock(return_value=[])
#
#     ok, _ = solver._solve_unconstrained_scenario()
#
#     assert ok
#     assert simple_absolute_flow.value == 200.0
#
#
# # --------------------------------------------------
# # 📊 Relative flow tests
# # --------------------------------------------------
#
# def test_relative_flow_redistribution(mock_flow_solver, simple_relative_flows):
#     f1, f2 = simple_relative_flows
#
#     def get_flow(flow_id, year):
#         return f1 if flow_id == "f1" else f2
#
#     mock_flow_solver.get_flow.side_effect = get_flow
#
#     modifier = make_modifier("f1")
#     scenario = mock_flow_solver.get_scenario()
#     scenario.scenario_definition.flow_modifiers = [modifier]
#
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     solver._calculate_new_flow_values = Mock(return_value=(
#         {2020: 70.0},
#         {2020: 0.0}
#     ))
#
#     solver._process_absolute_flows = Mock(return_value=({}, {}))
#
#     solver._process_relative_flows = Mock(return_value=(
#         {},
#         {
#             0: [
#                 # Target flow
#                 FlowModifierSolver.FlowChangeEntry(
#                     year=2020,
#                     flow_id="f1",
#                     value=70.0,
#                     evaluated_value=70.0,
#                     evaluated_share=0.7
#                 ),
#                 # Sibling flow adjustment
#                 FlowModifierSolver.FlowChangeEntry(
#                     year=2020,
#                     flow_id="f2",
#                     evaluated_offset=-20.0,
#                     evaluated_share_offset=-0.2
#                 )
#             ]
#         }
#     ))
#
#     solver._check_flow_modifier_changes = Mock()
#     solver._recalculate_relative_flow_evaluated_shares = Mock()
#     solver._check_flow_modifier_results = Mock(return_value=[])
#
#     ok, _ = solver._solve_unconstrained_scenario()
#
#     assert ok
#     assert f1.value == 70.0
#     assert f2.value < 50.0
#
#
# # --------------------------------------------------
# # ❌ Error handling tests
# # --------------------------------------------------
#
# def test_absolute_flow_error_triggers_exit(mock_flow_solver):
#     modifier = make_modifier()
#     scenario = mock_flow_solver.get_scenario()
#     scenario.scenario_definition.flow_modifiers = [modifier]
#
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     error_entry = FlowModifierSolver.FlowErrorEntry(
#         year=2020,
#         total_outflows=50,
#         required_outflows=100,
#         flow_modifier_index=0,
#         error_type=FlowErrorType.NotEnoughTotalOutflows
#     )
#
#     solver._process_absolute_flows = Mock(return_value=(
#         {0: error_entry},
#         {}
#     ))
#
#     solver._process_relative_flows = Mock(return_value=({}, {}))
#     solver._calculate_new_flow_values = Mock(return_value=({}, {}))
#     solver._check_flow_modifier_changes = Mock()
#
#     with pytest.raises(SystemExit):
#         solver._solve_unconstrained_scenario()
#
#
# def test_relative_flow_error_triggers_exit(mock_flow_solver):
#     modifier = make_modifier()
#     scenario = mock_flow_solver.get_scenario()
#     scenario.scenario_definition.flow_modifiers = [modifier]
#
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     error_entry = FlowModifierSolver.FlowErrorEntry(
#         year=2020,
#         total_outflows=50,
#         required_outflows=100,
#         flow_modifier_index=0,
#         error_type=FlowErrorType.NotEnoughTotalOutflows
#     )
#
#     solver._process_absolute_flows = Mock(return_value=({}, {}))
#     solver._process_relative_flows = Mock(return_value=(
#         {0: error_entry},
#         {}
#     ))
#
#     solver._calculate_new_flow_values = Mock(return_value=({}, {}))
#     solver._check_flow_modifier_changes = Mock()
#
#     with pytest.raises(SystemExit):
#         solver._solve_unconstrained_scenario()
#
#
# # --------------------------------------------------
# # 🧹 Cleanup behavior
# # --------------------------------------------------
#
# def test_clamp_called(mock_flow_solver):
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     solver._recalculate_relative_flow_evaluated_shares = Mock()
#     solver._check_flow_modifier_results = Mock(return_value=[])
#
#     solver._solve_unconstrained_scenario()
#
#     mock_flow_solver.clamp_flow_values_below_zero.assert_called_once()
#
#
# def test_check_results_errors_propagated(mock_flow_solver):
#     solver = FlowModifierSolver(
#         mock_flow_solver,
#         ParameterScenarioType.Unconstrained
#     )
#
#     solver._recalculate_relative_flow_evaluated_shares = Mock()
#     solver._check_flow_modifier_results = Mock(return_value=["error"])
#
#     ok, errors = solver._solve_unconstrained_scenario()
#
#     assert not ok
#     assert errors == ["error"]

