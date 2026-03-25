import os
import warnings
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


def test_check_scenario_results():
    # TODO: Check scenario results
    pass
