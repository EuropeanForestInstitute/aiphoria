import os
import pickle
import shutil
from typing import Union, List
import core.logger
from core.logger import log, start_log_perf, stop_log_perf, clear_log_perf, show_log_perf_summary
from core.datachecker import DataChecker
from core.dataprovider import DataProvider
from core.datastructures import Scenario
from core.flowsolver import FlowSolver
from core.parameters import ParameterName
from core.utils import show_exception_errors, show_model_parameters, build_mfa_system_for_scenario

# Globals
global_path_to_cache = ""
global_use_cache = False
global_use_timing = False
global_clear_cache = False


def init_builder(path_to_cache: str,
                 use_cache: bool = False,
                 use_timing: bool = False,
                 clear_cache: bool = False,
                 ) -> None:
    """
    Initialize Builder module.
    If use_cache is True then create cache directory if directory does not exist.

    :param path_to_cache: Absolute path to directory to contain cached objects
    :param use_cache: True to use cached objects (default: False)
    :param use_timing: True to show timing information (default: False)
    :param clear_cache: True to clear delete cache directory and create new directory
    :return: None
    """
    # Update globals
    globals().update(global_path_to_cache=path_to_cache)
    globals().update(global_use_cache=use_cache)
    globals().update(global_use_timing=use_timing)
    globals().update(global_clear_cache=clear_cache)

    if global_clear_cache:
        shutil.rmtree(global_path_to_cache, ignore_errors=True)

    if global_use_cache:
        if not os.path.exists(global_path_to_cache):
            os.makedirs(global_path_to_cache, exist_ok=True)

    core.logger.use_log_perf = global_use_timing


def build_dataprovider(filename: str, use_cache: Union[bool, None] = None) -> DataProvider:
    """
    Build DataProvider.
    If use_cache is True then create DataProvider normally, write pickled object to file and read pickled
    object from cache.

    :param filename: Target settings filename
    :param use_cache: True to use cached DataProvider object (default: False)
    :return: DataProvider-object
    """
    if use_cache is None:
        use_cache = global_use_cache

    dataprovider = None
    if use_cache:
        path_to_cached_dataprovider = os.path.join(global_path_to_cache, "dataprovider.pickle")

        if not os.path.exists(path_to_cached_dataprovider):
            try:
                dataprovider = DataProvider(filename)
            except Exception as ex:
                show_exception_errors(ex, "Following errors occurred when loading settings file:")
                print("Fatal error, stopping execution...")
                raise ex

            with open(path_to_cached_dataprovider, "wb") as fs:
                pickle.dump(dataprovider, fs, pickle.HIGHEST_PROTOCOL)

        with open(path_to_cached_dataprovider, "rb") as fs:
            dataprovider = pickle.load(fs)
    else:
        try:
            dataprovider = DataProvider(filename)
        except Exception as ex:
            show_exception_errors(ex, "Following errors occurred when loading settings file:")
            print("Fatal error, stopping execution...")
            raise ex

    return dataprovider


def build_datachecker(dataprovider: DataProvider = None, use_cache: Union[bool, None] = None) -> DataChecker:
    """
    Build DataChecker.

    :param dataprovider: DataProvider
    :param use_cache: True to use cached DataChecker from file (default: False)
    :return: DataChecker
    """
    if use_cache is None:
        use_cache = global_use_cache

    datachecker = None
    if use_cache:
        path_to_cached_datachecker = os.path.join(global_path_to_cache, "datachecker.pickle")
        if not os.path.exists(path_to_cached_datachecker):
            datachecker = DataChecker(dataprovider)

            with open(path_to_cached_datachecker, "wb") as fs:
                pickle.dump(datachecker, fs, pickle.HIGHEST_PROTOCOL)

        with open(path_to_cached_datachecker, "rb") as fs:
            datachecker = pickle.load(fs)
    else:
        datachecker = DataChecker(dataprovider)

    return datachecker


def build_and_solve_scenarios(datachecker: DataChecker = None, use_cache: Union[bool, None] = None) -> List[Scenario]:
    """
    Build and check errors in scenario data and solve scenarios.

    :param datachecker: DataChecker-object
    :param use_cache: True to use cached Scenario-objects (default: False)
    :return: List of solved Scenario-objects
    """
    if use_cache is None:
        use_cache = global_use_cache

    scenarios = []
    if use_cache:
        # Check for cached scenario files
        filenames_to_load = []
        scenario_prefix = "scenario"
        files_in_cache = os.listdir(global_path_to_cache)
        for file in files_in_cache:
            abs_path = os.path.join(global_path_to_cache, file)
            has_prefix = file.startswith(scenario_prefix)
            is_file = os.path.isfile(abs_path)
            if has_prefix and is_file:
                filenames_to_load.append(abs_path)

        if not filenames_to_load:
            # No existing scenario data, build scenarios to pickle to files
            try:
                scenarios = datachecker.build_scenarios()
            except Exception as ex:
                show_exception_errors(ex, "Following errors occurred when building scenarios:")
                print("Fatal error, stopping execution...")
                raise ex

            # Check for build scenario errors
            try:
                datachecker.check_for_errors()
            except Exception as ex:
                show_exception_errors(ex, "Following errors found when checking scenario errors:")
                print("Fatal error, stopping execution...")
                raise ex

            # Solve scenarios
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

                    a = 0

                    # Solve this alternative scenario time steps
                    scenario_flow_solver = FlowSolver(scenario=scenario)
                    scenario_flow_solver.solve_timesteps()
                    scenario.flow_solver = scenario_flow_solver

            # Build MFA systems for the scenarios
            for scenario in scenarios:
                scenario.mfa_system = build_mfa_system_for_scenario(scenario)

            for scenario_index, scenario in enumerate(scenarios):
                filename = os.path.join(global_path_to_cache, "{}_{}.pickle".format(scenario_prefix, scenario_index))
                with open(filename, "wb") as fs:
                    pickle.dump(scenario, fs, pickle.HIGHEST_PROTOCOL)

            # Rescan cache for scenario files
            filenames_to_load = []
            files_in_cache = os.listdir(global_path_to_cache)
            for file in files_in_cache:
                if file.startswith(scenario_prefix) and os.path.isfile(file):
                    filenames_to_load.append(os.path.abspath(file))
            filenames_to_load.sort()

        # Load all scenario files
        for filename in filenames_to_load:
            with open(filename, "rb") as fs:
                scenario = pickle.load(fs)
                scenarios.append(scenario)

    else:
        try:
            scenarios = datachecker.build_scenarios()
        except Exception as ex:
            show_exception_errors(ex, "Following errors occurred when building scenarios:")
            print("Fatal error, stopping execution...")
            raise ex

        # Check for build scenario errors
        try:
            datachecker.check_for_errors()
        except Exception as ex:
            show_exception_errors(ex, "Following errors found when checking scenario errors:")
            print("Fatal error, stopping execution...")
            raise ex

        # Solve scenarios
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

    return scenarios


def build_results(filename: str = None):
    """
    Build and solve scenarios using the settings file.

    :param filename: Path to Excel settings file
    :return: Tuple (model parameters (dictionary), list of scenarios (List[Scenario), color definitions (dictionary))
    """
    # Build DataProvider
    log("Loading data from file '{}'...".format(filename), level="info")

    start_log_perf("Loaded DataProvider" if not global_use_cache else "Loaded DataProvider (cached)")
    log("Build DataProvider...")
    dataprovider: DataProvider = build_dataprovider(filename)
    stop_log_perf()

    # Model parameters is a Dictionary that contains loaded data from Excel sheet named "Settings"
    # and are used for running the FlowSolver and setting up ODYM
    model_params = dataprovider.get_model_params()
    show_model_parameters(model_params)

    # Setup output path
    # NOTE: This only works inside Notebook, executable might need __file__?
    # Convert output directory name to absolute path and update model parameter dictionary
    model_params[ParameterName.OutputPath] = os.path.abspath(
        os.path.join(os.getcwd(), model_params[ParameterName.OutputPath]))

    # **************************************************************
    # * Step 2: Check data integrity and build data for FlowSolver *
    # **************************************************************
    log("Build and check errors in data...")
    start_log_perf("Loaded DataChecker" if not global_use_cache else "Loaded DataChecker (cached)")
    datachecker: DataChecker = build_datachecker(dataprovider)
    stop_log_perf()

    # **************************************************
    # * Step 3: Build and solve flows in all scenarios *
    # **************************************************
    log("Solve scenarios...")
    start_log_perf("Solve scenarios" if not global_use_cache else "Loaded scenarios (cached)")
    scenarios: List[Scenario] = build_and_solve_scenarios(datachecker)
    stop_log_perf()

    # Transformation stage color definitions
    color_definitions = {color.name: color.value for color in dataprovider.get_color_definitions()}

    # Show perf logs if toggled on
    show_log_perf_summary("build_scenarios()")
    clear_log_perf()

    return model_params, scenarios, color_definitions

