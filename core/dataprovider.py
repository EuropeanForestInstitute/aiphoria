from collections.abc import Callable
from enum import Enum
from typing import List
import numpy as np
import pandas as pd
from core.datastructures import Process, Flow, Stock


class ModelParameterNames(Enum):
    Filename = "filename"
    SheetNameProcesses = "sheet_name_processes"
    ColumnRangeProcesses = "column_range_processes"
    SkipNumRowsProcesses = "skip_num_rows_processes"


class DataProvider(object):
    def __init__(self, params):
        self._workbook = None
        self._processes = []
        self._flows = []
        self._stocks = []
        self._sheet_name_processes = None
        self._sheet_name_flows = None

        # Check that all required keys exists
        required_keys = [
            "filename",

            # Process related
            "sheet_name_processes",
            "column_range_processes",
            "skip_num_rows_processes",

            # Flow related
            "sheet_name_flows",
            "column_range_flows",
            "skip_num_rows_flows",

            # Model related
            "detect_year_range",
            "year_start",
            "year_end",
            "use_virtual_flows",
        ]

        # Check that all required keys are found in model parameter dictionary
        missing_keys = []
        for key in required_keys:
            if key not in params:
                missing_keys.append(key)

        if missing_keys:
            print("DataProvider: Missing keys from params")
            for key in missing_keys:
                print("\t- {}".format(key))
            raise SystemExit(-1)

        filename = params["filename"]
        sheet_name_processes = params["sheet_name_processes"]
        sheet_name_flows = params["sheet_name_flows"]
        col_range_processes = params["column_range_processes"]
        col_range_flows = params["column_range_flows"]
        skip_num_rows_processes = params["skip_num_rows_processes"]
        skip_num_rows_flows = params["skip_num_rows_flows"]

        # Sheet name to DataFrame
        sheets = {}
        try:
            with pd.ExcelFile(params["filename"]) as xls:
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

        # Create Stocks from Processes
        self._stocks = self._create_stocks_from_processes(self._processes)

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
