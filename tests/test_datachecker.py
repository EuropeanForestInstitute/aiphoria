import os
import pytest
import warnings
from aiphoria import ParameterName, ParameterFillMethod
from aiphoria.core.datachecker import DataChecker
from aiphoria.core.dataprovider import DataProvider


def get_path_to_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")


def get_path_to_stock_lt_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_stock_lt_overrides.xlsx")


def get_path_to_flow_indicators_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_flow_indicators.xlsx")


def get_path_to_color_definitions_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_color_definitions.xlsx")


def get_path_to_scenario_definitions_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_definitions.xlsx")


def get_path_to_scenario_process_stock_parameters() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "test_scenario_process_stock_parameters.xlsx")


def get_path_to_output() -> str:
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "test_output")


def test_datachecker():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)

    # Compare to reference scenario values
    scenarios = datachecker.build_scenarios()


def test_datachecker_no_processes():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    dataprovider._processes = []
    datachecker = DataChecker(dataprovider)

    # No Processes - expect Exception
    with pytest.raises(Exception) as ex_info:
        scenarios = datachecker.build_scenarios()

def test_datachecker_no_flows():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    dataprovider._flows = []
    datachecker = DataChecker(dataprovider)

    # No Flows - expect Exception
    with pytest.raises(Exception) as ex_info:
        scenarios = datachecker.build_scenarios()


def test_datachecker_detect_year_range():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)

    # Detect year range automatically
    with pytest.raises(Exception) as ex_info:
        params = dataprovider.get_model_params()
        params[ParameterName.DetectYearRange] = True
        scenarios = datachecker.build_scenarios()

    # Use defined start and end year - expect no Exceptions
    params = dataprovider.get_model_params()
    params[ParameterName.DetectYearRange] = False
    scenarios = datachecker.build_scenarios()

    # End year before start year - expect Exception
    with pytest.raises(Exception) as ex_info:
        params = dataprovider.get_model_params()
        params[ParameterName.DetectYearRange] = False
        params[ParameterName.StartYear] = 2000
        params[ParameterName.EndYear] = 1990
        scenarios = datachecker.build_scenarios()


def test_start_year():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    datachecker = DataChecker(dataprovider)

    params = dataprovider.get_model_params()
    defined_start_year = params[ParameterName.StartYear]
    defined_end_year = params[ParameterName.StartYear]

    # Set all Flows year before defined start year - expect Exception
    with pytest.raises(Exception) as ex_info:
        for flow in dataprovider.get_flows():
            flow.year = defined_start_year - 1

        scenarios = datachecker.build_scenarios()

    # Set all Flows year after defined end year - expect Exception
    with pytest.raises(Exception) as ex_info:
        params = dataprovider.get_model_params()
        for flow in dataprovider.get_flows():
            flow.year = defined_end_year + 1

        scenarios = datachecker.build_scenarios()

    # Set all Flows year after defined end year - expect Exception
    with pytest.raises(Exception) as ex_info:
        params = dataprovider.get_model_params()
        for flow in dataprovider.get_flows():
            flow.year = defined_end_year + 1

        scenarios = datachecker.build_scenarios()


def test_check_inflow_viz():
    # Test invalid Process IDs for inflow visualization
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)
    params = dataprovider.get_model_params()
    params[ParameterName.VisualizeInflowsToProcesses].append("InvalidProcessID")
    datachecker = DataChecker(dataprovider)
    with pytest.raises(Exception) as ex_info:
        scenarios = datachecker.build_scenarios()


def test_check_flow_sources_and_targets():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)

    # Set invalid target for Flow - expect Exception
    flows = dataprovider.get_flows()
    flows[-1].source_process_id = "123"

    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


def test_check_flow_multiple_definitions_per_year():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)

    # Duplicate Flow - expect Exception
    flows = dataprovider.get_flows()
    flows.append(flows[-1])

    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


def test_isolated_stocks():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)

    # Isolated Process has Stock (= Process with no inflows and outflows)
    # Make Stock ID invalid so it emulates invalid Process
    stocks = dataprovider.get_stocks()
    stocks[0].id = "123"

    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


# def test_fill_method_requirements():
#     path_to_scenario = get_path_to_reference_scenario()
#     path_to_output = get_path_to_output()
#
#     # Ignore openpyxl warning about Data validation extension support, we are not using that
#     warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
#
#     # Init Builder without cache and expect that the cache directory does not exists after running init_builder
#     dataprovider = DataProvider(path_to_scenario)
#
#     params = dataprovider.get_model_params()
#     params[ParameterName.FillMethod] = ParameterFillMethod.Previous
#     flows = dataprovider.get_flows()
#     flows[-1].source_process_id = "InvalidSource"
#
#     with pytest.raises(Exception) as ex_info:
#         datachecker = DataChecker(dataprovider)
#         scenarios = datachecker.build_scenarios()


def test_check_root_processes():
    # Test root processes that only have relative outflows
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    dataprovider = DataProvider(path_to_scenario)

    # Make root process isolated - expect Exception
    params = dataprovider.get_model_params()

    # Find root processes and make all outflows from root processes relative - expect Exception
    processes = dataprovider.get_processes()
    flows = dataprovider.get_flows()
    for p in processes:
        process_inflows = []
        process_outflows = []
        for f in flows:
            if f.target_process_id == p.id:
                process_inflows.append(f)
            if f.source_process_id == p.id:
                process_outflows.append(f)

        if not process_inflows:
            for f in process_outflows:
                f.unit = "%"

    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


def test_stock_lifetime_overrides():
    # Test errors stock lifetime overrides
    path_to_scenario = get_path_to_stock_lt_reference_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


def test_flow_indicators():
    path_to_scenario = get_path_to_flow_indicators_reference_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


def test_color_definitions():
    # Check errors in color definitions in "Colors"-sheet
    path_to_scenario = get_path_to_color_definitions_reference_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        scenarios = datachecker.build_scenarios()


def test_scenario_definitions():
    # Test errors in "Scenarios"-sheet
    path_to_scenario = get_path_to_scenario_definitions_reference_scenario()
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
    dataprovider = DataProvider(path_to_scenario)
    with pytest.raises(Exception) as ex_info:
        datachecker = DataChecker(dataprovider)
        datachecker.check_for_errors()
        scenarios = datachecker.build_scenarios()


# def test_scenario_definitions():
#     path_to_scenario = get_path_to_scenario_definitions_reference_scenario()
#     warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")
#     dataprovider = DataProvider(path_to_scenario)
#     with pytest.raises(Exception) as ex_info:
#         datachecker = DataChecker(dataprovider)
#         datachecker.check_for_errors()
#         scenarios = datachecker.build_scenarios()


def test_process_stock_parameters():
    pass
