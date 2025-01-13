Step 2 - Data checking and data build for FlowSolver

Once the data is loaded, aiphoria checks if data are loaded correctly and whethere that are any errors. If not issue occurs, aiphoria builds the baseline scenario and a network graph is created. 



```python
print("Checking errors in data...")
data_checker = DataChecker(dataprovider)
scenarios = data_checker.build_scenarios()
is_checker_ok, checker_messages = data_checker.check_for_errors()
if not is_checker_ok:
    for msg in checker_messages:
        print(msg)
    SystemExit(-1)


# Create network graph for data
# scenarios[0] is always the baseline scenario and is guaranteed to exist
if model_params[ParameterName.CreateNetworkGraphs]:
    network_visualizer = NetworkGraph()
    network_visualizer.build(scenarios[0].scenario_data)
    network_visualizer.show()
```

# add networkgraph, does not pop up currently