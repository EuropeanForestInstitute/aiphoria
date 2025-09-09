# Part 1 - Scenario settings

Let's go through the settings in the example scenario file.
> NOTE: This is not comprehensive list of parameters. <br>
> Names of all parameters can be found in file **core/parameters.py**

| Parameter name                  | Is required? | Description                                                                                                                                                                                  |
|---------------------------------|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| sheet_name_processes            | Yes          | Sheet name that contains data for Processes, e.g. (Processes)                                                                                                                                |
| ignore_columns_processes        | Yes          | Ignore Excel columns defined in the list when reading data from Processes sheet. Each column name must be separated by comma (',')                                                           |
| skip_num_rows_processes         | Yes          | Number of rows to skip when reading data for Processes (e.g. 2). NOTE: Header row must be the first row to read!                                                                             |
| sheet_name_flows                | Yes          | Sheet name that contains data for Flows, (e.g. Flows)                                                                                                                                        |
| ignore_columns_flows            | Yes          | Ignore Excel columns defined in the list when reading data from Flows sheet. Each column name must be separated by comma (',')                                                               |
| skip_num_rows_flows             | Yes          | Number of rows to skip when reading data for Processes (e.g. 2). NOTE: Header row must be the first row to read!                                                                             |
| start_year                      | Yes          | Starting year of the model                                                                                                                                                                   |
| end_year                        | Yes          | Ending year of the model, included in in time range                                                                                                                                          |
| detect_year_range               | Yes          | Detect the year range automatically from file                                                                                                                                                |
| use_virtual_flows               | Yes          | Use virtual flows. If enabled, creates missing flows for Processes that have imbalance of input and output flows i.e. unreported flows                                                       |
| virtual_flows_epsilon           | Yes          | If using virtual flows, create virtual flow to process if process total inputs and outputs difference is greater than this value                                                             |
| baseline_value_name             | Yes          | Baseline value name. Name of the value type that is used as baseline e.g. "Solid wood equivalent"                                                                                            |
| baseline_unit_name              | Yes          | Baseline unit name. This is used with relative flows when exporting flow data to CSVs.                                                                                                       |
| conversion_factor_c_to_co2      | No           | Conversion factor from C to CO2                                                                                                                                                              |
| fill_missing_absolute_flows     | No           | Fill in missing timestep with the last timestep provided by the user. Default value is True                                                                                                  |
| fill_missing_relative_flows     | No           | Fill in missing timestep with the last timestep provided by the user. Default value is True                                                                                                  |
| fill_method                     | No           | Fill method if either fill_missing_absolute_flows or fill_missing_relative_flows is enabled                                                                                                  |
| use_scenarios                   | No           | Run alternative scenarios defined on the scenarios sheet. Defaults to True if not defined in settings file.                                                                                  |
| scenario_type                   | No           | Scenario type (Constrained / Unconstrained)                                                                                                                                                  |
| sheet_name_scenarios            | No           | Sheet name that contains scenarios (flow variations)                                                                                                                                         |
| ignore_columns_scenarios        | No           | Ignore Excel columns defined in the list when reading data from Scenarios. Each column name must be separated by comma (',')                                                                 |
| create_network_graphs           | No           | Create network graphs to visualize process connections for each scenario                                                                                                                     |
| create_sankey_charts            | No           | Create Sankey charts for each scenario                                                                                                                                                       |
| visualize_inflows_to_processes  | No           | Create inflow visualization and export data for process IDs defined in here. Each process ID must be separated by comma (',')                                                                |
| sheet_name_colors               | No           | Sheet name that contains data for transformation stage colors (e.g. Colors)                                                                                                                  |
| ignore_columns_colors           | No           | Ignore Excel columns defined in the list when reading data from Colors sheet. Each column name must be separated by comma (',')                                                              |
| prioritize_locations            | No           | Priotize flows based on their location (e.g., Export). This functionality prioritizes / reduces exports from entering the stock so they occur on the same timestep.                          |
| prioritize_transformation_stage | No           | Priotize flows based on their transformation stage (e.g., Second). This functionality prioritizes / reduces the specific flows from entering the stock so they occur on the same timestep.   |
| sheet_name_process_positions    | No           | Sheet name that contains data for process positions in normalized format (position data in range [0,1])                                                                                      |

Example scenario file has the same descriptions as seen here: that file can be used as template when creating new scenarios.<br>
> NOTE: If parameter is not required then it can be left out: in that case internal default value is used.<br>

In the next part we look into how data is defined in scenario file.<br>

Next part: [Part 3 - Defining data for scenario](Part_3_-_Defining_data_for_scenario.md)<br>
Previous part: [Part 1 - Example scenario explained](Part_1_-_Example_scenario_explained.md)<br>
