import os
from aiphoria import ParameterName
from aiphoria.example import run_example

output_dir_name = "output_test_example"


def test_run_example():
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    path_to_settings_file = os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")
    path_to_output_dir = os.path.join(path_to_tests, output_dir_name)

    # Do not show plots
    parameter_overrides = {ParameterName.ShowPlots: False}
    run_example(path_to_output_dir,
                remove_existing_output_dir=True,
                parameter_overrides=parameter_overrides,
                )


def test_example_scenario_results():
    # TODO: Check scenario results
    pass
