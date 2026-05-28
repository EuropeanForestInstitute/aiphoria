import os
import warnings

import pytest

from aiphoria import ParameterName
from aiphoria.example import run_example
import matplotlib

output_dir_name = "output_test_example"


def test_run_example():
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
    run_example(path_to_output_dir=path_to_output_dir,
                remove_existing_output_dir=True,
                parameter_overrides=parameter_overrides,
                )
    # Close matploblib figures after running run_example() to fix warning about too many figures opened
    matplotlib.pyplot.close()

    # Run without output directory - invalid usage
    parameter_overrides = {ParameterName.ShowPlots: False}
    result = run_example(path_to_output_dir=None,
                         remove_existing_output_dir=True,
                         parameter_overrides=parameter_overrides,
                         )
    assert result is None
    matplotlib.pyplot.close()

    # Path to output directory is not in absolute format - invalid usage
    parameter_overrides = {ParameterName.ShowPlots: False}
    result = run_example(path_to_output_dir="test",
                         remove_existing_output_dir=True,
                         parameter_overrides=parameter_overrides
                         )
    assert result is False
    matplotlib.pyplot.close()

    # Path to output directory is not in absolute format - invalid usage
    parameter_overrides = {ParameterName.ShowPlots: False}
    result = run_example(path_to_output_dir="test",
                         remove_existing_output_dir=True,
                         parameter_overrides=parameter_overrides
                         )
    assert result is False
    matplotlib.pyplot.close()

    # Path to output directory already exists and remove existing output dir not set
    parameter_overrides = {ParameterName.ShowPlots: False}
    result = run_example(path_to_output_dir=path_to_output_dir,
                         remove_existing_output_dir=False,
                         parameter_overrides=parameter_overrides
                         )
    assert result is False
    matplotlib.pyplot.close()
