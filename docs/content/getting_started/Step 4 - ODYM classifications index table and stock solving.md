Step 4 - ODYM classifications, index table and stock solving

During this step, aiphoria passes of the necessary parameters in the proper format to ODYM to create the MFA system.  

Setup ODYM classifications and index table for each Scenario:
```python
for scenario_index, scenario in enumerate(scenarios):
    print("Building ODYM MFA for scenario '{}' ({}/{})...".format(scenario.name, scenario_index + 1, len(scenarios)))

    # Track solid wood equivalent and carbon.
    # Dictionary of classifications enters the index table defined for the system.
    # The index table lists all aspects needed and assigns a classification and index letter to each aspect.
    # More info on ODYM model classifications and index table see: https://github.com/IndEcol/ODYM
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

    index_table.set_index('Aspect', inplace=True)  # Default indexing of IndexTable, other indices are produced on the fly
    index_table

```

ODYM initialization: the dynamic stock models are developed to track how stocks change over time based on
their inflows and lifetime parameters and each result is stored in a dictionary. 

```python
flow_solver = scenario.flow_solver
    mfa_system = msc.MFAsystem(Name='Wood product system', Geogr_Scope='Europe', Unit='Mm3',
                               ProcessList=[], FlowDict={}, StockDict={}, ParameterDict={},
                               Time_Start=model_time_start, Time_End=model_time_end, IndexTable=index_table,
                               Elements=index_table.loc['Element'].Classification.Items)

    # Get inflow values to stock
    year_index_to_year = dict(enumerate(model_years))
    unique_processes = flow_solver.get_unique_processes()
    unique_flows = flow_solver.get_unique_flows()

    # NOTE: These are not used anywhere
    # TODO: Export these as CSVs
    # # DataFrames for Processes, Flows and Flow values
    # print("Collecting processes to DataFrame...")
    # df_processes = flow_solver.get_processes_as_dataframe()
    # print("Collecting flows to DataFrame...")
    # df_flows = flow_solver.get_flows_as_dataframe()
    # print("Collecting evaluated flow values to DataFrame...")
    # df_flow_values = flow_solver.get_evaluated_flow_values_as_dataframe()

    print("Creating ODYM objects...")
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