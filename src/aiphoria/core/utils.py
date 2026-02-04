import os
import shutil
import sys
import re
from typing import List, Dict, Any, Union, Optional
import numpy as np
import pandas as pd
from IPython import get_ipython
from .datastructures import Scenario, Flow
import aiphoria.lib.odym.modules.ODYM_Classes as msc

global_path_to_output_dir: Union[str, None] = None


def show_model_parameters(model_params: Dict[str, Any]):
    """
    Show model parameters (= prints the model parameters to console).

    :param model_params: Dictionary of model parameters
    """
    print("Using following parameters for running the model:")
    max_param_len = max([len(name) for name in model_params])
    for param_name, param_value in model_params.items():
        print("\t{:{}} = {}".format(param_name, max_param_len, param_value))


def show_exception_errors(exception: Exception, msg: str = ""):
    """
    Show Exception errors.

    :param msg: Message about exception.
    :param exception: Exception
    """

    if msg:
        print(msg)

    errors = exception.args[0]
    if type(errors) is str:
        print(errors)

    if type(errors) is list:
        for error in errors:
            print("\t{}".format(error))


def setup_current_working_directory():
    """
    Setup current working directory.
    """
    if get_ipython() is None:
        # Running in terminal
        os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    else:
        # Running Notebook, cwd is already set
        pass


def create_output_directory(output_dir_path: str):
    """
    Create output directory.
    Deletes existing directory.
    """

    # If exists then delete existing directory and create new
    if os.path.exists(output_dir_path):
        try:
            shutil.rmtree(output_dir_path)
        except Exception as ex:
            raise ex

    # Create output directory and directories for all scenarios
    os.makedirs(output_dir_path)


def setup_odym_directories():
    """
    Setup ODYM directories. Appends to path to ODYM files to sys.path.
    """
    sys.path.insert(0, os.path.join(
        os.getcwd(), '.', 'lib', 'odym', 'modules'))


def setup_scenario_output_directories(output_dir_path: str, scenario_names: List[str]) -> Dict[str, str]:
    """
    Setup scenario output directories. Deletes existing scenario directory if exists.
    Returns Dictionary of scenario name to scenario directory (absolute path)

    :param output_dir_name: Output directory name
    :param scenario_names: List of scenario names
    :return: Dictionary [str, str]: Scenario name to scenario directory (absolute path)
    """

    scenario_name_to_abs_scenario_output_path = {}
    for scenario_name in scenario_names:
        abs_scenario_output_path = os.path.join(output_dir_path, scenario_name)
        try:
            shutil.rmtree(abs_scenario_output_path)
        except FileNotFoundError as ex:
            pass
        except Exception as ex:
            raise ex

        os.makedirs(abs_scenario_output_path)
        scenario_name_to_abs_scenario_output_path[scenario_name] = abs_scenario_output_path

    return scenario_name_to_abs_scenario_output_path


def build_mfa_system_for_scenario(scenario: Scenario):
    """
    Build MFA system for scenario.

    :param scenario: Scenario-object
    :param progress_bar: Progress bar instance (optional)
    :return: ODYM MFASystem
    """

    # Track solid wood equivalent and carbon.
    # Dictionary of classifications enters the index table defined for the system.
    # The index table lists all aspects needed and assigns a classification and index letter to each aspect.
    scenario_data = scenario.scenario_data
    flow_solver = scenario.flow_solver
    years = scenario_data.years

    # Baseline value and unit name: e.g. name = "Solid wood equivalent and unit = "Mm3"
    baseline_value_name = scenario_data.baseline_value_name
    baseline_unit_name = scenario_data.baseline_unit_name

    # Indicator names are used as Elements in ODYM MFASystem
    indicator_names = flow_solver.get_indicator_names()

    model_time_start = scenario_data.start_year
    model_time_end = scenario_data.end_year
    model_elements = [baseline_value_name] + indicator_names
    model_years = years

    model_classifications = {
        'Time': msc.Classification(Name='Time', Dimension='Time', ID=1, Items=model_years),
        'Cohort': msc.Classification(Name='Age-cohort', Dimension='Time', ID=2, Items=model_years),
        'Element': msc.Classification(Name='Elements', Dimension='Element', ID=3, Items=model_elements),
    }

    index_table = pd.DataFrame({'Aspect': ['Time', 'Age-cohort', 'Element'],  # 'Time' and 'Element' must be present!
                                'Description': ['Model aspect "time"', 'Model aspect "age-cohort"', 'Model aspect "Element"'],
                                # 'Time' and 'Element' are also dimensions
                                'Dimension': ['Time', 'Time', 'Element'],
                                'Classification': [model_classifications[Aspect] for Aspect in ['Time', 'Cohort', 'Element']],
                                # Unique one letter (upper or lower case) indices to be used later for calculations.
                                'IndexLetter': ['t', 'c', 'e']})

    # Default indexing of IndexTable, other indices are produced on the fly
    index_table.set_index('Aspect', inplace=True)

    # ****************************
    # Initialize ODYM MFA system *
    # ****************************
    flow_solver = scenario.flow_solver
    mfa_system = msc.MFAsystem(Name='MFA System',
                               Geogr_Scope='Not defined',
                               Unit=baseline_unit_name,
                               ProcessList=[], FlowDict={}, StockDict={}, ParameterDict={},
                               Time_Start=model_time_start, Time_End=model_time_end, IndexTable=index_table,
                               Elements=index_table.loc['Element'].Classification.Items)

    # Get inflow values to stock
    year_index_to_year = dict(enumerate(model_years))
    unique_processes = flow_solver.get_unique_processes()
    unique_flows = flow_solver.get_unique_flows()

    # Create ODYM objects
    # print("Building ODYM processes...")
    odym_processes = []
    process_id_to_index = {}
    for process_id, process in unique_processes.items():
        process_index = len(odym_processes)
        process_id_to_index[process_id] = process_index
        new_process = msc.Process(ID=process_index, Name=process.name)
        odym_processes.append(new_process)

    # print("Building ODYM flows...")
    odym_flows = {}
    for flow_id, flow in unique_flows.items():
        source_process_index = process_id_to_index[flow.source_process_id]
        target_process_index = process_id_to_index[flow.target_process_id]
        new_flow = msc.Flow(ID=flow.id, P_Start=source_process_index,
                            P_End=target_process_index, Indices='t,e', Values=None)
        odym_flows[flow.id] = new_flow

    # print("Building ODYM stocks...")
    odym_stocks = {}
    for stock in flow_solver.get_all_stocks():
        process_index = process_id_to_index[stock.id]
        new_stock = msc.Stock(ID=stock.id, Name=stock.name,
                              P_Res=process_index, Indices='t,e', Type=0, Values=None)
        odym_stocks[stock.id] = new_stock

    mfa_system.ProcessList = odym_processes
    mfa_system.FlowDict = odym_flows
    mfa_system.StockDict = odym_stocks
    mfa_system.Initialize_FlowValues()
    mfa_system.Initialize_StockValues()
    mfa_system.Consistency_Check()

    # Update ODYM flow values from flow values DataFrame
    for flow_id, flow in mfa_system.FlowDict.items():
        for year_index, value in enumerate(flow.Values):
            # Skip to next year if FlowSolver does not have data for this year
            # This is possible because ODYM flow and stock values are already initialized to 0.0
            flow_has_data_for_year = flow_solver.has_flow(
                year=year_index_to_year[year_index], flow_id=flow_id)
            if not flow_has_data_for_year:
                continue

            # NOTE: Virtual flows use default value defined in Flow for carbon content (now 1.0).
            # Get all evaluated values and set those to ODYM flow
            solved_flow = flow_solver.get_flow(
                year=year_index_to_year[year_index], flow_id=flow_id)

            # If flow is not present this year, use 0.0 value
            if not isinstance(solved_flow, Flow):
                for index, indicator_name in enumerate(indicator_names):
                    flow.Values[year_index, index] = 0.0
                continue

            for index, evaluated_value in enumerate(solved_flow.get_all_evaluated_values()):
                flow.Values[year_index, index] = evaluated_value

    # Process stocks (fill with data)
    for stock_id, stock in odym_stocks.items():
        # Baseline DSM
        # These are needed for triggering DSM calculations
        baseline_dsm = flow_solver.get_baseline_dynamic_stocks()[stock_id]
        baseline_stock_by_cohort = baseline_dsm.compute_s_c_inflow_driven()
        baseline_outflow_by_cohort = baseline_dsm.compute_o_c_from_s_c()
        baseline_stock_total = baseline_dsm.compute_stock_total()
        baseline_stock_change = baseline_dsm.compute_stock_change()
        stock.Values[:, 0] = baseline_stock_change

        # Indicator DSMs
        for indicator_index, indicator_name in enumerate(indicator_names):
            # These are needed for triggering DSM calculations
            indicator_dsm = flow_solver.get_indicator_dynamic_stocks()[
                stock_id][indicator_name]
            indicator_stock_by_cohort = indicator_dsm.compute_s_c_inflow_driven()
            indicator_outflow_by_cohort = indicator_dsm.compute_o_c_from_s_c()
            indicator_stock_total = indicator_dsm.compute_stock_total()
            indicator_stock_change = indicator_dsm.compute_stock_change()

            # Baseline values are at index 0 so offset by +1
            stock.Values[:, indicator_index + 1] = indicator_stock_change

    return mfa_system


def calculate_scenario_mass_balance(mfa_system: msc.MFAsystem) -> pd.DataFrame:
    """
    Get scenario mass balance difference per year.

    :param mfa_system: MFASystem-object
    :param model_years: List of years
    :return: DataFrame
    """

    mb = mfa_system.MassBalance()
    # print("Mass balance result shape: {}".format(mb.shape))
    df_mass_balance = pd.DataFrame(
        columns=["Year", "Process 0", "Rest", "Difference"])
    for year_index, year in enumerate(mfa_system.Time_L):
        # Calculate mass balance using the first element in MFA system (= base element)
        # Negative value in process 0 means that process 0 has no inflows so this mass
        # is coming from outside system boundaries
        p0 = np.sum(mb[year_index][0][0])
        rest = np.sum(mb[year_index][1:, 0])
        abs_diff = abs(p0) - abs(rest)
        df_mass_balance.loc[year_index] = np.array([year, p0, rest, abs_diff])
    df_mass_balance = df_mass_balance.astype({"Year": "int32"})
    # df_mass_balance.set_index(["Year"], inplace=True)
    return df_mass_balance


def shorten_sheet_name(name, max_length=31):
    """Shorten and sanitize Excel sheet names to comply with the 31-character limit."""
    # Sanitize name
    sanitized_name = re.sub(r'[:/\\]', '_', name)

    # Split by underscores to maintain structure
    parts = sanitized_name.split('_')

    # Identify fixed parts: these are short words (<= 3 chars) or common connectors
    fixed_parts = {i: p for i, p in enumerate(
        parts) if len(p) <= 3 or not p.isalnum()}
    variable_parts = [p for i, p in enumerate(parts) if i not in fixed_parts]

    # Determine available length for variable parts (accounting for underscores and fixed parts)
    num_underscores = len(parts) - 1
    fixed_length = sum(len(p) for p in fixed_parts.values())
    available_length = max_length - num_underscores - fixed_length

    # Reduce variable parts proportionally
    total_variable_length = sum(len(p) for p in variable_parts)
    if total_variable_length <= available_length:
        return sanitized_name[:max_length]  # Trim if needed

    reduced_parts = []
    for part in variable_parts:
        reduced_length = max(
            1, len(part) * available_length // total_variable_length)
        reduced_parts.append(part[:reduced_length])

    # Reconstruct the name, preserving fixed parts
    final_parts = []
    variable_index = 0
    for i in range(len(parts)):
        if i in fixed_parts:
            final_parts.append(fixed_parts[i])
        else:
            final_parts.append(reduced_parts[variable_index])
            variable_index += 1

    # Ensure final length
    shortened_name = "_".join(final_parts)
    return shortened_name[:max_length]


def get_output_directory() -> str:
    """
    Get output path directory.
    NOTE: Must be using the set_output_directory(), otherwise raises Exception
    """

    if global_path_to_output_dir is None:
        raise Exception("Output path not set")

    return global_path_to_output_dir


def set_output_directory(path_to_output_dir: str) -> None:
    """
        Set output directory for results.
        Path is converted to absolute path (e.g. .., . and ~ are converted to
        actual directory names).

        :param path_to_output_dir:  Path to directory

    """
    # NOTE: os.path.realpath follows symlinks where os.path.abspath does not
    # NOTE: ~ is not expanded to user home directory in Linux
    global_path_to_output_dir = os.path.realpath(path_to_output_dir)


def make_output_directory(path_to_output: str = "", remove_existing: bool = True) -> None:
    """
        Make output directory.
        If path to output directory is not set then creates directory "output"
        by default to the directory of the running script.

        :param remove_existing: If True then removes existing directory.
    """
    # TODO: Implement creating output directory

    os.makedirs(exist_ok=True)
