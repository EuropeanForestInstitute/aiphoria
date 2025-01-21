import sys
import os
from typing import List, Union, Any, Dict
import numpy as np
import openpyxl
import pandas as pd
from core.datastructures import Process, Flow, Stock, FlowModifier, ScenarioDefinition
from core.parameters import ParameterName, ParameterFillMethod


class DataProvider(object):
    def __init__(self, filename: str = "",
                 sheet_settings_name: str = "Settings",
                 sheet_settings_col_range: Union[str, int] = "B:C",
                 sheet_settings_skip_num_rows: int = 5,
                 ):

        self._workbook = None
        self._param_name_to_value = {}
        self._processes = []
        self._flows = []
        self._stocks = []
        self._scenario_definitions = []
        self._sheet_name_processes = None
        self._sheet_name_flows = None
        self._sheet_name_scenarios = None

        # Check that all required keys exists
        required_params = [
            [ParameterName.SheetNameProcesses, str, "Sheet name that contains data for Processes, (e.g. Processes)"],
            [ParameterName.ColumnRangeProcesses, str, "Start and end column names separated by colon (e.g. B:R) that contain data for Processes"],
            [ParameterName.SkipNumRowsProcesses, int, "Number of rows to skip when reading data for Processes (e.g. 2). NOTE: Header row must be the first row to read!"],

            # Flow related
            [ParameterName.SheetNameFlows, str, "Sheet name that contains data for Flows (e.g. Flows)"],
            [ParameterName.ColumnRangeFlows, str, "Start and end column names separated by colon (e.g. B:R) that contain data for Flows"],
            [ParameterName.SkipNumRowsFlows, int, "Number of rows to skip when reading data for Processes (e.g. 2). NOTE: Header row must be the first row to read!",],

            # Model related
            [ParameterName.StartYear, int, "Starting year of the model"],
            [ParameterName.EndYear, int, "Ending year of the model, included in time range"],
            [ParameterName.DetectYearRange, bool, "Detect the year range automatically from file"],
            [ParameterName.UseVirtualFlows, bool, "Use virtual flows (create missing flows for Processes that have imbalance of input and output flows, i.e. unreported flows)"],
            [ParameterName.VirtualFlowsEpsilon, float,
             "Maximum allowed absolute difference of process input and outputs before creating virtual flow"],
        ]

        # Optional parameters entry structure:
        # Name of the parameter, expected value type, comment, default value
        optional_params = [
            [ParameterName.ConversionFactorCToCO2,
             float,
             "Conversion factor from C to CO2",
             None],

            [ParameterName.FillMissingAbsoluteFlows,
             bool,
             "Fill missing absolute flows with previous valid flow data?",
             True],

            [ParameterName.FillMissingRelativeFlows,
             bool,
             "Fill missing relative flows with previous valid flow data?",
             True],

            [ParameterName.FillMethod,
             str,
             "Fill method if either fill_missing_absolute_flows or fill_missing_relative_flows is enabled",
             ParameterFillMethod.Zeros,
             ],

            [ParameterName.SheetNameScenarios,
             str,
             "Sheet name that contains data for scenarios (flow modifiers and constraints)",
             "Scenarios"
             ],
            [ParameterName.CreateNetworkGraphs,
             bool,
             "Create network graphs to visualize process connections for each scenario",
             False
             ],
            [ParameterName.CreateSankeyCharts,
             bool,
             "Create Sankey charts for each scenario",
             True
            ],
            [ParameterName.OutputPath,
             str,
             "Path to directory where all output is created (relative to running script)",
             "output"
             ],
            [ParameterName.ShowPlots,
            bool,
            "Show Matplotlib plots",
             True,
            ],
            [ParameterName.VisualizeInflowsToProcesses,
             list,
             "Create inflow visualization and export data for process IDs defined in here. " +
             "Each process ID must be separated by comma (',')",
             [],
            ],
            [ParameterName.BaseUnitName,
             str,
             "Base unit name. This is used with relative flows when exporting flow data to CSVs.",
             "Mm3 SWE",
            ]
        ]

        param_type_to_str = {int: "integer", float: "float", str: "string", bool: "boolean", list: "list"}

        # Suppress openpyxl warning about the Data Validation removed in the future
        # We don't care that much about the actual Data Validation inside Excel, only that
        # the cells contain values
        openpyxl.reader.excel.warnings.simplefilter(action='ignore')

        # Read settings sheet from the file
        param_name_to_value = {}
        try:
            with pd.ExcelFile(filename) as xls:
                try:
                    sheet_settings = pd.read_excel(io=xls,
                                                   sheet_name=sheet_settings_name,
                                                   usecols=sheet_settings_col_range,
                                                   skiprows=sheet_settings_skip_num_rows,
                                                   )

                    for row_index, row in sheet_settings.iterrows():
                        param_name, param_value = row
                        param_name_to_value[param_name] = param_value

                except ValueError as e:
                    raise Exception("DataProvider: Settings sheet '{}' not found in file {}!".format(
                        sheet_settings_name, filename))

        except FileNotFoundError as ex:
            raise Exception("File not found: {}".format(filename))

        # Check that all required params are defined in settings sheet
        missing_params = []
        for entry in required_params:
            param_name, param_type, param_desc = entry
            if param_name not in param_name_to_value:
                missing_params.append(entry)

        # Print missing parameters and information
        if missing_params:
            print("DataProvider: Settings sheet (Sheet) is missing required following parameters")
            max_param_name_len = 0
            for entry in missing_params:
                param_name = entry[0]
                max_param_name_len = len(param_name) if len(param_name) > max_param_name_len else max_param_name_len

            for entry in missing_params:
                param_name, param_type, param_desc = entry
                fixed_param_name = "{:" + str(max_param_name_len) + "}"
                fixed_param_name = fixed_param_name.format(param_name)
                print("\t{} (type: {}). {}".format(fixed_param_name, param_type_to_str[param_type], param_desc))

            raise Exception(-1)

        # Check that required and optionals parameters are correct types
        for entry in required_params:
            param_name, param_type, param_desc = entry
            if param_name in param_name_to_value:
                found_param_value = param_name_to_value[param_name]
                found_param_type = type(found_param_value)
                try:
                    # Convert Excel value needed as bool to Python bool
                    if param_type is bool:
                        found_param_value = self._to_bool(found_param_value)
                    param_value = param_type(found_param_value)
                    self._param_name_to_value[param_name] = param_value

                except ValueError as e:
                    print("Invalid type for required parameter '{}': expected {}, got {}".format(
                        param_name, param_type_to_str[param_type], param_type_to_str[found_param_type]))

        for entry in optional_params:
            param_name, param_type, param_desc, param_default_value = entry
            if param_name in param_name_to_value:
                # NOTE: Lists need to be handled differently
                if param_type == list:
                    splits = []
                    found_param_value = param_name_to_value[param_name]
                    if type(found_param_value) is bool:
                        # Empty cell is interpreted as bool for some reason
                        splits = param_default_value
                        continue

                    if type(found_param_value) is str:
                        # Remove whitespaces in string and split by separator ','
                        sep = ","
                        splits = found_param_value.replace(" ", "").split(sep)

                    self._param_name_to_value[param_name] = splits
                    continue

                found_param_value = param_name_to_value[param_name]
                found_param_type = type(found_param_value)
                try:
                    if param_type is bool:
                        found_param_value = self._to_bool(found_param_value)
                    param_value = param_type(found_param_value)
                    self._param_name_to_value[param_name] = param_value
                except ValueError as e:
                    print("Invalid type for optional parameter '{}': expected {}, got {}".format(
                        param_name, param_type_to_str[param_type], param_type_to_str[found_param_type]))

                # Check that FillMethod has valid value
                if param_name is ParameterName.FillMethod:
                    valid_fill_method_names = []
                    for method_name in dir(ParameterFillMethod):
                        if not method_name.startswith("__"):
                            valid_fill_method_names.append(method_name)

                    # Convert found param name and valid fill method names to lowercase
                    # and check if found param name is one of the valid method names
                    found_param_value_lower = found_param_value.lower()
                    valid_method_names_lower = [name.lower() for name in valid_fill_method_names]
                    if found_param_value_lower in valid_method_names_lower:
                        self._param_name_to_value[param_name] = found_param_value
                    else:
                        print("{} not valid value for {}! ".format(found_param_value, param_name), end="")
                        print("Valid values are: ", end="")
                        for index, method_name in enumerate(valid_fill_method_names):
                            print(method_name, end="")
                            if index < len(valid_fill_method_names) - 1:
                                print(", ", end="")
                            else:
                                print("")

                        self._param_name_to_value[param_name] = param_default_value
                        print("")
                        raise Exception(-1)

            else:
                # Use default optional parameter value
                self._param_name_to_value[param_name] = param_default_value

        # ********************************************
        # * Read processes and flows from Excel file *
        # ********************************************

        # Create Processes and Flows
        sheet_name_processes = param_name_to_value.get(ParameterName.SheetNameProcesses, None)
        col_range_processes = param_name_to_value.get(ParameterName.ColumnRangeProcesses, None)
        skip_num_rows_processes = param_name_to_value.get(ParameterName.SkipNumRowsProcesses, None)

        sheet_name_flows = param_name_to_value.get(ParameterName.SheetNameFlows, None)
        col_range_flows = param_name_to_value.get(ParameterName.ColumnRangeFlows, None)
        skip_num_rows_flows = param_name_to_value.get(ParameterName.SkipNumRowsFlows, None)

        sheet_name_scenarios = param_name_to_value.get(ParameterName.SheetNameScenarios, None)
        col_range_scenarios = param_name_to_value.get(ParameterName.ColumnRangeScenarios, None)
        skip_num_rows_scenarios = param_name_to_value.get(ParameterName.SkipNumRowsScenarios, None)

        # Sheet name to DataFrame
        sheets = {}
        try:
            with pd.ExcelFile(filename) as xls:
                try:
                    sheet_processes = pd.read_excel(xls,
                                                    sheet_name=sheet_name_processes,
                                                    skiprows=skip_num_rows_processes,
                                                    usecols=col_range_processes
                                                    )
                    sheets[sheet_name_processes] = sheet_processes
                except ValueError:
                    pass

                try:
                    sheet_flows = pd.read_excel(xls, sheet_name=sheet_name_flows,
                                                skiprows=skip_num_rows_flows,
                                                usecols=col_range_flows
                                                )
                    sheets[sheet_name_flows] = sheet_flows
                except ValueError:
                    pass

                # Optional
                try:
                    sheet_scenarios = pd.read_excel(xls, sheet_name=sheet_name_scenarios,
                                                    skiprows=skip_num_rows_scenarios,
                                                    usecols=col_range_scenarios
                                                    )
                    sheets[sheet_name_scenarios] = sheet_scenarios
                except ValueError:
                    pass

        except FileNotFoundError:
            raise Exception("DataProvider: File not found ({})".format(filename))

        # Check that all the required sheets exists
        required_sheet_names = [sheet_name_processes, sheet_name_flows]
        missing_sheet_names = self._check_missing_sheet_names(required_sheet_names, sheets)
        if missing_sheet_names:
            print("DataProvider: file '{}' is missing following required sheets:".format(filename))
            for key in missing_sheet_names:
                print("\t- {}".format(key))
            raise Exception(-1)

        self._sheet_name_processes = sheet_name_processes
        self._sheet_name_flows = sheet_name_flows

        # Check that all optional sheets exists (only if optional sheets have been defined)
        optional_sheet_names = []

        if sheet_name_scenarios:
            optional_sheet_names.append(sheet_name_scenarios)

        missing_sheet_names = self._check_missing_sheet_names(optional_sheet_names, sheets)
        if missing_sheet_names:
            print("DataProvider: file '{}' is missing following optional sheets:".format(filename))
            for key in missing_sheet_names:
                print("\t- {}".format(key))
            raise Exception(-1)

        self._sheet_name_scenarios = sheet_name_scenarios

        # Create Processes
        rows_processes = []
        df_processes = sheets[self._sheet_name_processes]
        for (row_index, row) in df_processes.iterrows():
            row = self._convert_row_nan_to_none(row)
            rows_processes.append(row)

        self._processes = self._create_objects_from_rows(Process,
                                                         rows_processes,
                                                         row_start=skip_num_rows_processes)

        # Create Flows
        rows_flows = []
        df_flows = sheets[self._sheet_name_flows]
        for (row_index, row) in df_flows.iterrows():
            row = self._convert_row_nan_to_none(row)
            rows_flows.append(row)

        self._flows = self._create_objects_from_rows(Flow,
                                                     rows_flows,
                                                     row_start=skip_num_rows_flows)

        # Create Stocks from Processes
        self._stocks = self._create_stocks_from_processes(self._processes)

        # Create alternative scenarios (optional)
        if sheet_name_scenarios:
            rows_scenarios = []
            df_scenarios = sheets[self._sheet_name_scenarios]
            for (row_index, row) in df_scenarios.iterrows():
                row = self._convert_row_nan_to_none(row)
                rows_scenarios.append(row)

            self._scenario_definitions = self._create_scenario_definitions(rows_scenarios)

    def _check_missing_sheet_names(self, required_sheet_names: List[str], sheets: Dict[str, pd.DataFrame]):
        missing_sheet_names = []
        for key in required_sheet_names:
            if key not in sheets:
                missing_sheet_names.append(key)

        return missing_sheet_names

    def _create_objects_from_rows(self, object_type=None, rows=None, row_start=-1) -> List:
        if rows is None:
            rows = []

        result = []
        if not object_type:
            return result

        row_number = row_start + 2
        for row in rows:
            if not self._is_row_valid(row):
                row_number += 1
                continue

            new_instance = object_type(row, row_number)
            if new_instance.is_valid():
                result.append(new_instance)

            row_number += 1

        return result

    def _create_stocks_from_processes(self, processes=None) -> List[Stock]:
        # Create stocks only for Processes that have lifetime > 1
        if processes is None:
            processes = []

        result = []
        for process in processes:
            if process.stock_lifetime == 0:
                continue

            new_stock = Stock(process)
            if new_stock.is_valid():
                result.append(new_stock)

        return result

    def _create_scenario_definitions(self, rows: List[Any] = None) -> List[ScenarioDefinition]:
        if not rows:
            rows = []

        flow_modifiers = []
        for row_index, row in enumerate(rows):
            new_flow_modifier = FlowModifier(row)
            new_flow_modifier.row_number = row_index + 2  # Header = row 1
            if new_flow_modifier.is_valid():
                flow_modifiers.append(new_flow_modifier)

        # Build scenario mappings
        result = []
        if not flow_modifiers:
            # No alternative scenarios found, create later only the baseline scenario
            pass
        else:
            # Map scenario names to flow modifiers
            scenario_name_to_flow_modifiers = {}
            for flow_modifier in flow_modifiers:
                scenario_name = flow_modifier.scenario_name
                if scenario_name not in scenario_name_to_flow_modifiers:
                    scenario_name_to_flow_modifiers[scenario_name] = []
                scenario_name_to_flow_modifiers[scenario_name].append(flow_modifier)

            # Create scenario definitions from mappings
            for scenario_name, scenario_flow_modifiers in scenario_name_to_flow_modifiers.items():
                new_scenario_definition = ScenarioDefinition(scenario_name, scenario_flow_modifiers)
                result.append(new_scenario_definition)
        return result

    def _is_row_valid(self, row):
        # Each row must have all first columns defined
        cols = row.iloc[0:4]
        if any(pd.isna(cols)):
            return False

        return True

    def _convert_row_nan_to_none(self, row: pd.Series) -> pd.Series:
        """
        Check the row and convert NaN to None.
        Modifies the original row.

        :param row: Series
        :return: Returns the original modified row
        """
        for col_name, value in row.items():
            if np.isreal(value) and np.isnan(value):
                row[col_name] = None
        return row

    def get_model_params(self) -> dict[ParameterName, Any]:
        """
        Get model parameters read from the data file.

        :return: Dictionary of parameter name to parameter value
        """
        return self._param_name_to_value

    def get_processes(self) -> List[Process]:
        return self._processes

    def get_flows(self) -> List[Flow]:
        return self._flows

    def get_stocks(self) -> List[Stock]:
        return self._stocks

    def get_scenario_definitions(self) -> List[ScenarioDefinition]:
        return self._scenario_definitions

    def _to_bool(self, value: Any) -> bool:
        """
        Check and convert value to bool.
        If value is string then converts to lowercase and checks if value is either "true" or "false"
        and returns corresponding value as bool.\n
        NOTE: Only converts value to string and checks bool validity, no other checking is done.

        :param value: Value to convert to bool
        :return: Value as bool
        """
        if isinstance(value, str):
            if value.lower() == "true":
                return True

        if isinstance(value, bool):
            return value

        else:
            return False

    @property
    def sheet_name_processes(self):
        return self._sheet_name_processes

    @property
    def sheet_name_flows(self):
        return self._sheet_name_flows


if __name__ == "__main__":
    dp = DataProvider("C:/dev/PythonProjects/aiphoria/data/example_data.xlsx",
                      sheet_settings_name="Settings",
                      sheet_settings_col_range="B:C",
                      sheet_settings_skip_num_rows=5)
