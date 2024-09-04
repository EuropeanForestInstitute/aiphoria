from enum import Enum
from typing import List, Union, Any
import numpy as np
import pandas as pd
from core.datastructures import Process, Flow, Stock


class ParameterName(Enum):
    # Process related
    SheetNameProcesses: str = "sheet_name_processes"
    ColumnRangeProcesses: str = "column_range_processes"
    SkipNumRowsProcesses: str = "skip_num_rows_processes"

    # Flow related
    SheetNameFlows: str = "sheet_name_flows"
    ColumnRangeFlows: str = "column_range_flows"
    SkipNumRowsFlows: str = "skip_num_rows_flows"

    # Model parameters
    StartYear: str = "start_year"
    EndYear: str = "end_year"
    DetectYearRange: str = "detect_year_range"
    UseVirtualFlows: str = "use_virtual_flows"


class DataProvider(object):
    def __init__(self, filename: str = "",
                 sheet_settings_name: str = "Settings",
                 sheet_settings_col_range: str = "B:C",
                 sheet_settings_skip_num_rows: int = 5
                 ):
        self._workbook = None
        self._processes = []
        self._flows = []
        self._stocks = []
        self._sheet_name_processes = None
        self._sheet_name_flows = None

        # Check that all required keys exists
        param_name_to_value = {}
        required_params = [
            [ParameterName.SheetNameProcesses.value, str, "Sheet name that contains data for Processes, (e.g. Processes)"],
            [ParameterName.ColumnRangeProcesses.value, str, "Start and end column names separated by colon (e.g. B:R) that contain data for Processes"],
            [ParameterName.SkipNumRowsProcesses.value, int, "Number of rows to skip when reading data for Processes (e.g. 2). NOTE: Header row must be the first row to read!"],

            # Flow related
            [ParameterName.SheetNameFlows.value, str, "Sheet name that contains data for Flows (e.g. Flows)"],
            [ParameterName.ColumnRangeFlows.value, str, "Start and end column names separated by colon (e.g. B:R) that contain data for Flows"],
            [ParameterName.SkipNumRowsFlows.value, int, "Number of rows to skip when reading data for Processes (e.g. 2). NOTE: Header row must be the first row to read!"],

            # Model related
            [ParameterName.StartYear.value, int, "Starting year of the model"],
            [ParameterName.EndYear.value, int, "Ending year of the model, included in time range"],
            [ParameterName.DetectYearRange.value, bool, "Detect the year range automatically from file"],
            [ParameterName.UseVirtualFlows.value, bool, "Use virtual flows (create missing flows for Processes that have imbalance of input and output flows, i.e. unreported flows)"],
        ]

        param_type_to_str = {int: "integer", str: "string", bool: "boolean"}

        # Read settings sheet from the file
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
                    raise SystemExit("DataProvider: Settings sheet '{}' not found in file {}!".format(
                        sheet_settings_name, filename))

        except FileNotFoundError:
            raise SystemExit("DataProvider: File not found ({})".format(filename))

        # Check that all required params are defined in settings sheet
        missing_params = []
        for entry in required_params:
            param_name, param_type, param_desc = entry
            if param_name not in param_name_to_value:
                missing_params.append(entry)

        # Print missing parameters and information
        if missing_params:
            print("DataProvider: Settings sheet is missing required following parameters")
            max_param_name_len = 0
            for entry in missing_params:
                param_name = entry[0]
                print(param_name)
                max_param_name_len = len(param_name) if len(param_name) > max_param_name_len else max_param_name_len

            for entry in missing_params:
                param_name, param_type, param_desc = entry
                fixed_param_name = "{:" + str(max_param_name_len) + "}"
                fixed_param_name = fixed_param_name.format(param_name)
                print("\t{} (type: {}). {}".format(fixed_param_name, param_type_to_str[param_type], param_desc))

            raise SystemExit(-1)

        sheet_name_processes = param_name_to_value[ParameterName.SheetNameProcesses.value]
        sheet_name_flows = param_name_to_value[ParameterName.SheetNameFlows.value]
        col_range_processes = param_name_to_value[ParameterName.ColumnRangeProcesses.value]
        col_range_flows = param_name_to_value[ParameterName.ColumnRangeFlows.value]
        skip_num_rows_processes = param_name_to_value[ParameterName.SkipNumRowsProcesses.value]
        skip_num_rows_flows = param_name_to_value[ParameterName.SkipNumRowsFlows.value]

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

        except FileNotFoundError:
            print("DataProvider: file not found (" + filename + ")")
            raise SystemExit(-1)

        # Check that sheets exists
        required_sheet_names = [
            sheet_name_processes,
            sheet_name_flows,
        ]

        missing_sheet_names = []
        for key in required_sheet_names:
            if key not in sheets:
                missing_sheet_names.append(key)

        if missing_sheet_names:
            print("DataProvider: file '{}' is missing following sheets:".format(filename))
            for key in missing_sheet_names:
                print("\t- {}".format(key))
            raise SystemExit(-1)

        self._sheet_name_processes = sheet_name_processes
        self._sheet_name_flows = sheet_name_flows

        # Create Processes
        rows_processes = []
        df_processes = sheets[self._sheet_name_processes]
        for (row_index, row) in df_processes.iterrows():
            rows_processes.append(row)
        self._processes = self._create_objects_from_rows(Process, rows_processes, row_start=skip_num_rows_processes)

        # Create Flows
        rows_flows = []
        df_flows = sheets[self._sheet_name_flows]

        for (row_index, row) in df_flows.iterrows():
            rows_flows.append(row)

        self._flows = self._create_objects_from_rows(Flow, rows_flows, row_start=skip_num_rows_flows)

        # # Create Stocks from Processes
        # self._stocks = self._create_stocks_from_processes(self._processes)

    def _create_objects_from_rows(self, object_type=None, rows=[], row_start=-1) -> List:
        result = []
        if not object_type:
            return result

        row_number = row_start
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
            if process.lifetime == 0:
                continue

            new_stock = Stock(process)
            if new_stock.is_valid():
                result.append(new_stock)

        return result

    def _is_row_valid(self, row):
        # Each row must have all first columns defined
        cols = row.iloc[0:4]
        if any(pd.isna(cols)):
            return False

        return True

    def get_processes(self) -> List[Process]:
        return self._processes

    def get_flows(self) -> List[Flow]:
        return self._flows

    def get_stocks(self) -> List[Stock]:
        return self._stocks

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
