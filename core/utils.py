import os
import shutil
import sys
import pandas as pd
import numpy as np
from typing import List, Dict
from IPython import get_ipython

from core.datastructures import Scenario
import lib.odym.modules.ODYM_Classes as msc


def setup_current_working_directory():
    """
    Setup current working directory.
    """
    if get_ipython() is None:
        # Running in terminal
        os.chdir(os.path.dirname(sys.argv[0]))
    else:
        # Running Notebook, cwd is already set
        pass


def setup_odym_directories():
    """
    Setup ODYM directories. Appends to path to ODYM files to sys.path.
    """
    sys.path.insert(0, os.path.join(os.getcwd(), '.', 'lib', 'odym', 'modules'))


def setup_output_directory(output_dir_path: str, scenario_names: List[str]) -> Dict[str, str]:
    """
    Create output directory path. Deletes existing directory if exists.
    Returns Dictionary of scenario name to scenario directory (absolute path)

    :param output_dir_name: Output directory name
    :param scenario_names: List of scenario names
    :return: Dictionary [str, str]: Scenario name to scenario directory (absolute path)
    """
    # If exists then delete existing directory and create new
    if os.path.exists(output_dir_path):
        try:
            shutil.rmtree(output_dir_path)
        except Exception as ex:
            print(ex)

    # Create output directory and directories for all scenarios
    os.makedirs(output_dir_path)
    scenario_name_to_abs_scenario_output_path = {}
    for scenario_name in scenario_names:
        abs_scenario_output_path = os.path.join(output_dir_path, scenario_name)
        os.makedirs(abs_scenario_output_path)
        scenario_name_to_abs_scenario_output_path[scenario_name] = abs_scenario_output_path

    return scenario_name_to_abs_scenario_output_path


def build_mfa_system_for_scenario(scenario: Scenario):
    """
    Build MFA system for scenario.

    :param scenario: Scenario-object
    :return: ODYM MFASystem
    """

    # Track solid wood equivalent and carbon.
    # Dictionary of classifications enters the index table defined for the system.
    # The index table lists all aspects needed and assigns a classification and index letter to each aspect.
    scenario_data = scenario.scenario_data
    years = scenario_data.years

    model_time_start = scenario_data.start_year
    model_time_end = scenario_data.end_year
    model_elements = ['Solid wood equivalent', 'Carbon']
    model_years = years

    model_classifications = {
        'Time': msc.Classification(Name='Time', Dimension='Time', ID=1, Items=model_years),
        'Cohort': msc.Classification(Name='Age-cohort', Dimension='Time', ID=2, Items=model_years),
        'Element': msc.Classification(Name='Elements', Dimension='Element', ID=3, Items=model_elements),
    }

    index_table = pd.DataFrame({'Aspect': ['Time', 'Age-cohort', 'Element'],  # 'Time' and 'Element' must be present!
                                'Description': ['Model aspect "time"', 'Model aspect "age-cohort"', 'Model aspect "Element"'],
                                'Dimension': ['Time', 'Time', 'Element'],  # 'Time' and 'Element' are also dimensions
                                'Classification': [model_classifications[Aspect] for Aspect in ['Time', 'Cohort', 'Element']],
                                'IndexLetter': ['t', 'c', 'e' ]})  # Unique one letter (upper or lower case) indices to be used later for calculations.

    # Default indexing of IndexTable, other indices are produced on the fly
    index_table.set_index('Aspect', inplace=True)

    # ****************************
    # Initialize ODYM MFA system *
    # ****************************
    flow_solver = scenario.flow_solver
    mfa_system = msc.MFAsystem(Name='Wood product system', Geogr_Scope='Europe', Unit='Mm3',
                               ProcessList=[], FlowDict={}, StockDict={}, ParameterDict={},
                               Time_Start=model_time_start, Time_End=model_time_end, IndexTable=index_table,
                               Elements=index_table.loc['Element'].Classification.Items)

    # Get inflow values to stock
    year_index_to_year = dict(enumerate(model_years))
    unique_processes = flow_solver.get_unique_processes()
    unique_flows = flow_solver.get_unique_flows()

    # Create ODYM objects
    print("Building ODYM processes...")
    odym_processes = []
    process_id_to_index = {}
    for process_id, process in unique_processes.items():
        process_index = len(odym_processes)
        process_id_to_index[process_id] = process_index
        new_process = msc.Process(ID=process_index, Name=process.name)
        odym_processes.append(new_process)

    print("Building ODYM flows...")
    odym_flows = {}
    for flow_id, flow in unique_flows.items():
        source_process_index = process_id_to_index[flow.source_process_id]
        target_process_index = process_id_to_index[flow.target_process_id]
        new_flow = msc.Flow(ID=flow.id, P_Start=source_process_index, P_End=target_process_index, Indices='t,e', Values=None)
        odym_flows[flow.id] = new_flow

    print("Building ODYM stocks...")
    odym_stocks = {}
    for stock in flow_solver.get_all_stocks():
        process_index = process_id_to_index[stock.id]
        new_stock = msc.Stock(ID=stock.id, Name=stock.name, P_Res=process_index, Indices='t,e', Type=0, Values=None)
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
            flow_has_data_for_year = flow_solver.has_flow(year=year_index_to_year[year_index], flow_id=flow_id)
            if not flow_has_data_for_year:
                continue

            # NOTE: Virtual flows use default value defined in Flow for carbon content (now 1.0).
            solved_flow = flow_solver.get_flow(year=year_index_to_year[year_index], flow_id=flow_id)
            flow.Values[year_index, 0] = solved_flow.evaluated_value
            flow.Values[year_index, 1] = solved_flow.evaluated_value_carbon

    # Process stocks (fill with data)
    for stock_id, stock in odym_stocks.items():
        # Calculate cohorts for "Solid wood equivalent"
        dsm_swe = flow_solver.get_dynamic_stocks_swe()[stock_id]
        swe_stock_by_cohort = dsm_swe.compute_s_c_inflow_driven()
        swe_outflow_by_cohort = dsm_swe.compute_o_c_from_s_c()
        swe_stock_total = dsm_swe.compute_stock_total()
        swe_stock_change = dsm_swe.compute_stock_change()
        stock.Values[:, 0] = swe_stock_change

        # Calculate cohorts for "Carbon"
        dsm_carbon = flow_solver.get_dynamic_stocks_carbon()[stock_id]
        carbon_stock_by_cohort = dsm_carbon.compute_s_c_inflow_driven()
        carbon_outflow_by_cohort = dsm_carbon.compute_o_c_from_s_c()
        carbon_stock_total = dsm_carbon.compute_stock_total()
        carbon_stock_change = dsm_carbon.compute_stock_change()
        stock.Values[:, 1] = carbon_stock_change

    return mfa_system


def calculate_scenario_mass_balance(mfa_system: msc.MFAsystem) -> pd.DataFrame:
    """
    Get scenario mass balance difference per year.

    :param mfa_system: MFASystem-object
    :param model_years: List of years
    :return: DataFrame
    """

    mb = mfa_system.MassBalance()
    #print("Mass balance result shape: {}".format(mb.shape))
    df_mass_balance = pd.DataFrame(columns=["Year", "Process 0", "Rest", "Difference"])
    for year_index, year in enumerate(mfa_system.Time_L):
        # Calculate mass balance using the first element in MFA system (= base element)
        # Negative value in process 0 means that process 0 has no inflows so this mass
        # is coming from outside system boundaries
        p0 = np.sum(mb[year_index][0][0])
        rest = np.sum(mb[year_index][1:, 0])
        abs_diff = abs(p0) - abs(rest)
        df_mass_balance.loc[year_index] = np.array([year, p0, rest, abs_diff])
    df_mass_balance = df_mass_balance.astype({"Year": "int32"})
    df_mass_balance.set_index(["Year"], inplace=True)
    return df_mass_balance
