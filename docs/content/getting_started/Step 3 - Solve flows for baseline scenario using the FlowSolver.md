Step 3 - Solve flows for baseline scenario using the FlowSolver 

During this steps and once the data checks are performed, the flow solving takes place. FloweSolver solves the flows defined by the user which might be given as absolute (value of a number e.g., 5 m3) or relative (share e.g., 50%)



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