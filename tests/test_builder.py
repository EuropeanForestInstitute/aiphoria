import os
import warnings
import pytest
from aiphoria.core.builder import init_builder, build_dataprovider, build_datachecker, build_and_solve_scenarios, build_results


def get_path_to_reference_scenario() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "reference_data", "example_scenario.xlsx")


def get_path_to_output() -> str:
    # Check that the last part of the path is "tests" to allow running
    # the tests outside tests/
    path_to_tests = os.path.abspath(".")
    if os.path.split(path_to_tests)[-1] != "tests":
        path_to_tests = os.path.join(path_to_tests, "tests")

    return os.path.join(path_to_tests, "test_output")


def test_init_builder_no_use_cache():
    use_cache = False
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    path_to_cache = os.path.join(os.path.abspath("."), "tests", "test_cache")
    init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)
    assert not os.path.exists(path_to_cache)

    dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
    datachecker = build_datachecker(dataprovider, use_cache=use_cache)
    scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)

    model_params, scenarios, color_defs = build_results(path_to_scenario,
                                                        path_to_output_dir=path_to_output)


def test_init_builder_use_cache():
    use_cache = True
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    path_to_cache = os.path.join(os.path.abspath("."), "tests", "test_cache")
    init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)
    assert os.path.exists(path_to_cache)

    dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
    datachecker = build_datachecker(dataprovider, use_cache=use_cache)
    scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)

    model_params, scenarios, color_defs = build_results(path_to_scenario,
                                                        path_to_output_dir=path_to_output)

def test_dataprovider():
    use_cache = True
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    path_to_cache = os.path.join(os.path.abspath("."), "tests", "test_cache")
    init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)
    assert os.path.exists(path_to_cache)

    # Use non-existing parameter file (not cached)
    # Expect Exception (no target file found)
    with pytest.raises(Exception) as ex_info:
        path_to_scenario = "123"
        dataprovider = build_dataprovider(path_to_scenario, use_cache=False)

    # Use non-existing parameter file (cached)
    # Expect Exception (no target file found)
    with pytest.raises(Exception) as ex_info:
        path_to_scenario = "123"
        dataprovider = build_dataprovider(path_to_scenario, use_cache=True)

    # # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    # # Use non-existing path to cache (expect Exception)
    # path_to_cache = "123"
    # init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=False)
    # assert os.path.exists(path_to_cache)


def test_build_and_solve_scenarios():
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    path_to_cache = os.path.join(os.path.abspath("."), "tests", "test_cache")

    # Expect Exception if there is no Processes
    with pytest.raises(Exception) as ex_info:
        use_cache = True
        init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)
        assert os.path.exists(path_to_cache)

        dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
        datachecker = build_datachecker(dataprovider, use_cache=use_cache)

        # Empty list of Processes should cause Exception
        datachecker._processes = []
        scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)

    # Expect Exception if there is no Processes
    with pytest.raises(Exception) as ex_info:
        use_cache = True
        init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)
        assert os.path.exists(path_to_cache)

        dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
        datachecker = build_datachecker(dataprovider, use_cache=use_cache)

        # Create duplicate Process to cause Exception
        datachecker._processes.append(datachecker._processes[-1])
        scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)

    # Expect Exception if there is no Processes
    with pytest.raises(Exception) as ex_info:
        use_cache = False
        init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)

        dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
        datachecker = build_datachecker(dataprovider, use_cache=use_cache)

        # Empty list of Processes should cause Exception
        datachecker._processes = []
        scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)

    # Expect Exception if there is no Processes
    with pytest.raises(Exception) as ex_info:
        use_cache = False
        init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)

        dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
        datachecker = build_datachecker(dataprovider, use_cache=use_cache)

        # Create duplicate Process to cause Exception
        datachecker._processes.append(datachecker._processes[-1])
        scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)


def test_build_results(capfd):
    use_cache = True
    path_to_scenario = get_path_to_reference_scenario()
    path_to_output = get_path_to_output()

    # Ignore openpyxl warning about Data validation extension support, we are not using that
    warnings.filterwarnings(action="ignore", category=UserWarning, module="openpyxl")

    # Init Builder without cache and expect that the cache directory does not exists after running init_builder
    path_to_cache = os.path.join(os.path.abspath("."), "tests", "test_cache")
    init_builder(path_to_cache=path_to_cache, use_cache=use_cache, use_timing=False, clear_cache=True)
    assert os.path.exists(path_to_cache)

    dataprovider = build_dataprovider(path_to_scenario, use_cache=use_cache)
    datachecker = build_datachecker(dataprovider, use_cache=use_cache)
    scenarios = build_and_solve_scenarios(datachecker, use_cache=use_cache)

    # Expect KeyError-exception when passing invalid parameter to build_results()
    # Use output directory defined in parameter
    parameter_overrides = {"invalid_param": 123}
    with pytest.raises(KeyError) as ex_info:
        model_params, scenarios, color_defs = build_results(
            filename=path_to_scenario,
            path_to_output_dir=path_to_output,
            parameter_overrides=parameter_overrides)

        raise ex_info

    # Expect KeyError-exception when passing invalid parameter to build_results()
    # Use output directory defined in settings file
    parameter_overrides = {"invalid_param": 123}
    with pytest.raises(KeyError) as ex_info:
        model_params, scenarios, color_defs = build_results(
            filename=path_to_scenario,
            parameter_overrides=parameter_overrides)

        raise ex_info

    parameter_overrides = {"start_year": 1000}
    model_params, scenarios, color_defs = build_results(
        filename=path_to_scenario,
        path_to_output_dir=path_to_output,
        parameter_overrides=parameter_overrides)

    # Expect string "Overriding parameter" in standard output (parameter has been overridden)
    out, err = capfd.readouterr()
    assert "Overriding parameter" in out
