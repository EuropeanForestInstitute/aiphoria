import os
import pytest
from aiphoria.core.dataprovider import DataProvider


@pytest.fixture
def reference_scenario_name() -> str:
    return os.path.realpath("tests/reference_data/example_scenario.xlsx")


def test_check_reference_scenario(reference_scenario_name):
    """
    Test that reference scenario contains expected values.
    """
    dataprovider = DataProvider(reference_scenario_name)

    # Check that all parameters are found in reference settings file
    expected_params = {
        "sheet_name_processes": "Processes",
        "ignore_columns_processes": ["A"],
        "skip_num_rows_processes": 2,
        "sheet_name_flows": "Flows",
        "ignore_columns_flows": ["A"],
        "skip_num_rows_flows": 2,
        "start_year": 2021,
        "end_year": 2030,
        "detect_year_range": False,
        "use_virtual_flows": True,
        "virtual_flows_epsilon": 0.1,
        "baseline_value_name": "Solid wood equivalent",
        "baseline_unit_name": "Mm3",
        "conversion_factor_c_to_co2": -3.67,
        "fill_missing_absolute_flows": True,
        "fill_missing_relative_flows": True,
        "fill_method": "Previous",
        "use_scenarios": True,
        "scenario_type": "Constrained",
        "sheet_name_scenarios": "Scenarios",
        "ignore_columns_scenarios": [],
        "create_network_graphs": True,
        "create_sankey_charts": True,
        "visualize_inflows_to_processes": ["Incineration:FI", "Sawmilling:FI"],
        "sheet_name_colors": "Colors",
        "ignore_columns_colors": [],
        "prioritize_locations": [],
        "prioritize_transformation_stages": [],
        "sheet_name_process_positions": "Process positions",
        "output_path": ".",
        "include_metadata": True,
        "use_stock_lifetime_overrides": True,
        "sheet_name_stock_lifetime_overrides": "Stock lifetime overrides",
        "ignore_columns_stock_lifetime_overrides": ["A"],
        "skip_num_rows_stock_lifetime_overrides": 2,
    }

    # Check that all settings are defined properly
    model_params = dataprovider.get_model_params()

    # List of entries [expected parameter name, expected parameter value, got parameter value]
    errors = []
    max_allowed_diff = 0.0001
    for expected_param_name, expected_param_value in expected_params.items():
        got_param_value = model_params[expected_param_name]

        if got_param_value == expected_param_value:
            continue

        if expected_param_value is float:
            diff = abs(expected_param_value) - abs(got_param_value)
            if diff > max_allowed_diff:
                entry = [expected_param_name, expected_param_value, got_param_value]
                errors.append(entry)

    if errors:
        print("{} parameters failed:".format(len(errors)))
        for entry in errors:
            expected_param_name = entry[0]
            expected_param_value = entry[1]
            got_param_value = entry[2]
            print("\t- {}, expected={}, got={}".format(expected_param_name, expected_param_value, got_param_value))

    assert len(errors) == 0
