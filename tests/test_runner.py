import os
import warnings

# Running matplotlib in headless mode, otherwise errors are raised
import matplotlib
matplotlib.use("Agg")

from aiphoria import ParameterName
from aiphoria.runner import run_scenarios

output_dir_name = "output_test_runner"


def test_run_scenarios():
    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    path_to_settings_file = os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")
    path_to_output_dir = os.path.join(path_to_tests, output_dir_name)

    # Do not show plots
    parameter_overrides = {ParameterName.ShowPlots: False}
    run_scenarios(path_to_settings_file,
                  path_to_output_dir,
                  remove_existing_output_dir=True,
                  parameter_overrides=parameter_overrides,
                  )

def test_run_scenarios_no_settings_file():
    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    # path_to_settings_file = os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")
    path_to_settings_file = None
    path_to_output_dir = os.path.join(path_to_tests, output_dir_name)

    # Do not show plots
    parameter_overrides = {ParameterName.ShowPlots: False}
    run_scenarios(path_to_settings_file,
                  path_to_output_dir,
                  remove_existing_output_dir=True,
                  parameter_overrides=parameter_overrides,
                  )

def test_check_scenario_results():
    # TODO: Check scenario results
    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    # path_to_settings_file = os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")
    path_to_settings_file = None


    path_to_output_dir = os.path.join(path_to_tests, output_dir_name)

    # Do not show plots
    parameter_overrides = {ParameterName.ShowPlots: False}
    run_scenarios(path_to_settings_file,
                  path_to_output_dir,
                  remove_existing_output_dir=True,
                  parameter_overrides=parameter_overrides,
                  )

def test_flow_change_entry():
    from aiphoria.core.flowmodifiersolver import FlowModifierSolver
    from aiphoria.core.parameters import ParameterScenarioType

    # Check default instantiated FlowChangeEntry-object
    entry = FlowModifierSolver.FlowChangeEntry()
    entry_str = str(entry)

    expected_str = "FlowChangeEntry: year=0, flow_id=None, value=0.0, evaluated_share=0.0, evaluated_value=0.0, evaluated_offset=0.0, evaluated_share_offset=0.0"
    assert entry_str == expected_str


def test_flow_error_entry():
    from aiphoria.core.flowmodifiersolver import FlowModifierSolver, FlowErrorType

    # Check default instantiated object state
    entry = FlowModifierSolver.FlowErrorEntry(
        year=0,
        total_outflows=0.0,
        required_outflows=0.0,
        flow_modifier_index=0,
        error_type=FlowErrorType.Undefined,
        data={}
    )

    assert(entry.year == 0)
    print(entry.year)
