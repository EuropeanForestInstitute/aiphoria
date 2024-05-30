from typing import List
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from core.datastructures import Process, Flow, Stock


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
            "row_start_processes",

            # Flow related
            "sheet_name_flows",
            "column_range_flows",
            "row_start_flows",

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
        try:
            self._workbook = openpyxl.load_workbook(filename, read_only=False, data_only=True)
        except InvalidFileException:
            print("DataProvider: file not found (" + filename + ")")
            raise SystemExit(-1)

        # Check that sheets exists
        required_sheet_names = [
            sheet_name_processes,
            sheet_name_flows,
        ]

        missing_sheet_names = []
        for key in required_sheet_names:
            if key not in self._workbook:
                missing_sheet_names.append(key)

        if missing_sheet_names:
            print("DataProvider: file '{}' is missing following sheets:".format(filename))
            for key in missing_sheet_names:
                print("\t- {}".format(key))
            raise SystemExit(-1)

        self._sheet_name_processes = sheet_name_processes
        self._sheet_name_flows = sheet_name_flows

        # Read Processes
        col_range_processes = params["column_range_processes"]
        row_start_processes = params["row_start_processes"]
        sheet_processes = self._workbook[sheet_name_processes]
        rows_processes = self._read_rows_from_range(sheet=sheet_processes,
                                              col_range=col_range_processes,
                                              row_start=row_start_processes)

        self._processes = self._create_objects_from_rows(Process, rows_processes)

        # Read Flows
        col_range_flows = params["column_range_flows"]
        row_start_flows = params["row_start_flows"]
        sheet_flows = self._workbook[sheet_name_flows]
        rows_flows = self._read_rows_from_range(sheet=sheet_flows,
                                      col_range=col_range_flows,
                                      row_start=row_start_flows)

        self._flows = self._create_objects_from_rows(Flow, rows_flows)

        # Create stocks from Processes
        self._stocks = self._create_stocks_from_processes(self._processes)

    def _read_rows_from_range(self, sheet=None, col_range=None, row_start=-1):
        rows = []
        if not sheet:
            return rows

        columns = sheet[col_range]
        num_rows = len(columns[0])

        for row_index in range(row_start, num_rows):
            row = []
            for col in columns:
                row.append(col[row_index])

            # Track also Excel file row number
            excel_row_number = row_index + 1
            row.append(excel_row_number)
            rows.append(row)

        return rows

    def _create_objects_from_rows(self, object_type=None, rows=[]) -> List:
        result = []
        if not object_type:
            return result

        for row in rows:
            new_instance = object_type(row)
            if new_instance.is_valid():
                result.append(new_instance)

        return result

    def _create_stocks_from_processes(self, processes=[]) -> List:
        # Create stocks only for Processes that have lifetime > 1
        result = []
        for process in processes:
            if process.lifetime <= 1:
                continue

            new_stock = Stock(process)
            if new_stock.is_valid():
                result.append(new_stock)

        return result

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
