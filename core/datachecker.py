import copy
from typing import List, Dict
import numpy as np
from core.dataprovider import DataProvider
from core.datastructures import Process, Flow, Stock
import pandas as pd


class DataChecker(object):
    def __init__(self, dataprovider: DataProvider = None):
        self.dataprovider = dataprovider
        self.processes = self.dataprovider.get_processes()
        self.flows = self.dataprovider.get_flows()
        self.stocks = self.dataprovider.get_stocks()
        self.year_to_flow_id_to_flow = {}
        self.year_start = 0
        self.year_end = 0
        self.years = []

    def check_processes_integrity(self):
        # Check that there is only processes with unique ids
        result = True
        messages = []
        process_ids = set()
        duplicate_process_ids = []

        for process in self.processes:
            if process.id not in process_ids:
                process_ids.add(process.id)
            else:
                duplicate_process_ids.append(process.id)

        if duplicate_process_ids:
            result = False
            messages.append("Found processes without unique IDs:")
            for process_id in duplicate_process_ids:
                messages.append("\t{}".format(process_id))

        return result, messages

    def check_flows_integrity(self):
        # Check all years that all processes that are flows are using exists
        result = True
        messages = []
        flows_missing_source_ids = []
        flows_missing_target_ids = []
        flows_missing_value = []
        flows_missing_unit = []

        for year, flow_id_to_flow in self.year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow:
                source_process_id = flow.source_process_id
                target_process_id = flow.target_process_id

                if source_process_id not in self.processes:
                    flows_missing_source_ids.append(flow)

                if target_process_id not in self.processes:
                    flows_missing_target_ids.append(flow)

                # Value or unit could be 0 so check for None
                if flow.value is None:
                    flows_missing_value.append(flow)

                if flow.unit is None:
                    flows_missing_unit.append(flow)

        flows = flows_missing_source_ids
        if flows:
            result = False
            messages.append("Found flows missing source process IDs:")
            for flow in flows:
                messages.append("\t- Flow in row {} is missing Source_ID".format(flow.row_number))

        flows = flows_missing_target_ids
        if flows:
            result = False
            messages.append("Found flows missing target process IDs:")
            for flow in flows:
                messages.append("\t- Flow in row {} is missing Target_ID".format(flow.row_number))

        flows = flows_missing_value
        if flows:
            result = False
            messages.append("Found flows missing value:")
            for flow in flows:
                messages.append("\t- Flow in row {} is missing value".format(flow.row_number))

        flows = flows_missing_unit
        if flows:
            result = False
            messages.append("Found flows missing unit:")
            for flow in flows:
                messages.append("\t- Flow in row {} is missing unit".format(flow.row_number))

        return result, messages

    def check_for_isolated_processes(self):
        # Find isolated processes (= processes that has no inflows and outflows)
        # This is an error in data
        result = True
        messages = []
        for year, flow_id_to_flow in self.year_to_flow_id_to_flow.items():
            process_to_flows = {}
            for process in self.processes:
                process_to_flows[process] = {"in": [], "out": []}

            for flow_id, flow in flow_id_to_flow.items():
                source_process_id = flow.source_process_id
                target_process_id = flow.target_process_id
                process_to_flows[target_process_id]["in"].append(flow)
                process_to_flows[source_process_id]["out"].append(flow)

            for process, flows in process_to_flows.items():
                inflows = flows["in"]
                outflows = flows["out"]
                if (not inflows) and (not outflows):
                    messages.append("Found isolated processes:")
                    messages.append("{} in row ".format(process.id, process.row_number))

        return result, messages

    def check_for_errors(self):
        ok, messages_processes = self.check_processes_integrity()
        if not ok:
            return False, messages_processes

        ok, messages_flows = self.check_flows_integrity()
        if not ok:
            return False, messages_flows

        return True, []

    def build_flowsolver_data(self, start_year=0, end_year=0, detect_year_range=False):
        # NOTE: All flows must have data for the starting year
        processes = self.dataprovider.get_processes()
        flows = self.dataprovider.get_flows()
        stocks = self.dataprovider.get_stocks()

        if not processes:
            print("No processes!")

        if not flows:
            print("DataChecker: No valid flows flows!")

        if not processes or not flows:
            raise SystemExit("No processes or flows found!")

        # If 'detect_year_range' is set to True, detect start and end year
        # automatically from data. Year is converted to int.
        if detect_year_range:
            self.year_start, self.year_end = self._detect_year_range(flows)
        else:
            # Use years passed in as parameters
            if not start_year:
                raise SystemExit("DataChecker: No start year defined")

            if not end_year:
                raise SystemExit("DataChecker: No end year defined")

            self.year_start = start_year
            self.year_end = end_year

        # Build array of available years, last year is also included in year range
        self.years = [year for year in range(self.year_start, self.year_end + 1)]

        # Get unique flow and process IDs as dictionaries
        # Dictionary in Python >= 3.7 will preserve insertion order
        unique_flow_ids = self._get_unique_flow_ids(flows)
        unique_process_ids = self._get_unique_process_ids(processes)
        df_flows = self._create_year_to_flow_data(unique_flow_ids, flows)

        # Check that source and target processes for flows are defined
        if not self._check_flow_sources_and_targets(unique_process_ids, df_flows):
            raise SystemExit(-1)

        # Check that there is not multiple definitions for the exact same flow per year
        # Exact means that source and target processes are the same
        if not self._check_flow_multiple_definitions_per_year(unique_flow_ids, flows):
            raise SystemExit(-1)

        # Check if stock distribution type and parameters are set and valid
        if not self._check_process_stock_parameters(processes):
            raise SystemExit(-1)

        # Create and propagate flow data for missing years
        df_flows = self._create_flow_data_for_missing_years(df_flows)

        # Create process to flow mappings
        df_process_to_flows = self._create_process_to_flows(unique_process_ids, processes, df_flows)

        # Check if process only absolute inflows AND absolute outflows so that
        # the total inflow matches with the total outflows within certain limit
        if not self._check_process_inflows_and_outflows_mismatch(df_process_to_flows, epsilon=0.1):
            #raise SystemExit(-1)
            pass

        # Build graph data
        process_id_to_process = {}
        process_id_to_stock = {}

        for process in processes:
            process_id_to_process[process.id] = process

        for stock in stocks:
            stock_id = stock.id
            process_id_to_stock[stock_id] = stock

        # Data for graph
        graph_data = {
            "year_start": self.year_start,
            "year_end": self.year_end,
            "years": self.years,
            "process_id_to_process": process_id_to_process,
            "process_id_to_stock": process_id_to_stock,
            "df_process_to_flows": df_process_to_flows,
            "df_flows": df_flows,
            "all_processes": processes,
            "all_flows": flows,
            "all_stocks": stocks,
            "unique_process_id_to_process": unique_process_ids,
            "unique_flow_id_to_flow": unique_flow_ids,
        }
        return graph_data

    def get_processes(self) -> List[Process]:
        return self.processes

    def get_flows(self) -> List[Flow]:
        return self.flows

    def get_stocks(self) -> List[Stock]:
        return self.stocks

    def get_start_year(self) -> int:
        return self.year_start

    def get_end_year(self) -> int:
        return self.year_end

    def get_year_to_flow_id_to_flow_mapping(self):
        return self.year_to_flow_id_to_flow

    def _detect_year_range(self, flows: List[Flow]) -> (int, int):
        year_min = 9999
        year_max = 0

        for flow in flows:
            flow_year = flow.year
            if flow_year is None:
                continue

            flow_year = int(flow_year)
            if flow_year <= year_min:
                year_min = flow_year
            if flow_year >= year_max:
                year_max = flow_year

        year_start = min(year_min, year_max)
        year_end = max(year_min, year_max)
        return year_start, year_end

    def _get_year_range(self) -> list[int]:
        return [year for year in range(self.year_start, self.year_end + 1)]

    def _check_flow_sources_and_targets(self, unique_process_ids, df_flows):
        result = True
        sheet_name_processes = self.dataprovider.sheet_name_processes
        sheet_name_flows = self.dataprovider.sheet_name_flows
        for year in df_flows.index:
            for flow_id in df_flows.columns:
                flow = df_flows.at[year, flow_id]
                if pd.isnull(flow):
                    continue

                if flow.source_process_id not in unique_process_ids:
                    print("No source process {} for flow {} (row number {}) in year {} (in Excel sheet {}) ".format(
                        flow.source_process_id, flow_id, flow.row_number, year, sheet_name_flows))
                    result = False

                if flow.target_process_id not in unique_process_ids:
                    print("No target process {} for flow {} (row number {}) in year {} (sheet {})".format(
                        flow.target_process_id, flow_id, flow.row_number, year, sheet_name_flows))
                    result = False

        if not result:
            print("Some or all processes are missing definitions in Excel sheet {}".format(sheet_name_flows))

        return result

    def _get_unique_flow_ids(self, flows: List[Flow]) -> Dict[str, Flow]:
        unique_flow_id_to_flow = {}
        for flow in flows:
            if flow.id not in unique_flow_id_to_flow:
                unique_flow_id_to_flow[flow.id] = flow
        return unique_flow_id_to_flow

    def _get_unique_process_ids(self, processes: List[Process]) -> Dict[str, Process]:
        unique_process_id_to_process = {}
        for process in processes:
            if process.id not in unique_process_id_to_process:
                unique_process_id_to_process[process.id] = process
        return unique_process_id_to_process
    
    def _create_year_to_flow_mapping(self, flows) -> Dict[int, Dict[str, Flow]]:
        year_to_flow_id_to_flow = {}
        for flow in flows:
            if flow.year not in year_to_flow_id_to_flow:
                year_to_flow_id_to_flow[flow.year] = {}

            if flow.id not in year_to_flow_id_to_flow[flow.year]:
                year_to_flow_id_to_flow[flow.year][flow.id] = flow
        return year_to_flow_id_to_flow

    def _create_year_to_flow_data(self, unique_flow_ids: dict[str, Flow], flows: list[Flow]) -> pd.DataFrame:
        years = self._get_year_range()
        df = pd.DataFrame(index=years, columns=unique_flow_ids)
        for flow in flows:
            df.at[flow.year, flow.id] = flow
        return df

    def _check_flow_multiple_definitions_per_year(self, unique_flow_ids: Dict[str, Flow], flows: List[Flow]) -> bool:
        result = True
        years = self._get_year_range()
        sheet_name_flows = self.dataprovider.sheet_name_flows
        df = pd.DataFrame(index=years, columns=unique_flow_ids)
        for flow in flows:
            if pd.isnull(df.at[flow.year, flow.id]):
                df.at[flow.year, flow.id] = []
            df.at[flow.year, flow.id].append(flow)

        for year in df.index:
            for flow_id in df.columns:
                existing_flows = df.at[year, flow_id]
                if type(existing_flows) != list:
                    continue

                if len(existing_flows) > 1:
                    target_flow = existing_flows[0]
                    print("Multiple definitions for the same flow '{}' in year {} in sheet named '{}':".format(
                        target_flow.id, target_flow.year, sheet_name_flows))
                    for duplicate_flow in existing_flows:
                        print("- in row {}".format(duplicate_flow.row_number))
                    result = False

        return result

    def _check_process_inflows_and_outflows_mismatch(self, df_process_to_flows: pd.DataFrame, epsilon=0.1):
        print("Checking process total inflows and total outflows mismatches...")
        result = True
        years = self._get_year_range()
        sheet_name_flows = self.dataprovider.sheet_name_flows
        for year in df_process_to_flows.index:
            for process_id in df_process_to_flows.columns:
                entry = df_process_to_flows.at[year, process_id]
                inflows = entry["flows"]["in"]
                outflows = entry["flows"]["out"]

                if not inflows:
                    continue

                if not outflows:
                    continue

                is_all_inflows_absolute = all([flow.is_unit_absolute_value for flow in inflows])
                is_all_outflows_absolute = all([flow.is_unit_absolute_value for flow in outflows])
                if is_all_inflows_absolute and is_all_outflows_absolute:
                    inflows_total = np.sum([flow.value for flow in inflows])
                    outflows_total = np.sum([flow.value for flow in outflows])
                    diff_abs = np.abs(inflows_total) - np.abs(outflows_total)
                    if diff_abs > epsilon:
                        print("Total inflows and total outflows for process '{}' does not match.".format(process_id))
                        print("Absolute difference of total inflows and total outflows was {}".format(diff_abs))
                        print("Check following inflows in Excel sheet '{}':".format(sheet_name_flows))
                        for flow in inflows:
                            print("- flow '{}' in row {}".format(flow.id, flow.row_number))

                        print("Check following outflows:")
                        for flow in outflows:
                            print("- flow '{}' in row {}".format(flow.id, flow.row_number))

                        print("")

                        result = False

        return result

    def _create_flow_id_has_data_mapping(self, df_flows) -> pd.DataFrame:
        df = df_flows.copy()
        for flow_id in df.columns:
            df[flow_id] = np.where(pd.isnull(df[flow_id]), False, True)
        return df

    def _create_flow_data_for_missing_years(self, df_flows: pd.DataFrame) -> pd.DataFrame:
        # Create flow has data as boolean mapping
        df_flow_id_has_data = df_flows.copy()
        for flow_id in df_flow_id_has_data.columns:
            df_flow_id_has_data[flow_id] = np.where(pd.isnull(df_flow_id_has_data[flow_id]), False, True)

        # Find earliest and latest year of Flow data for each Flow ID
        flow_id_to_min_year = {flow_id: max(df_flows.index) for flow_id in df_flows}
        flow_id_to_max_year = {flow_id: min(df_flows.index) for flow_id in df_flows}
        for flow_id in df_flows.columns:
            for year, has_flow_data in df_flows[flow_id].items():
                if pd.notna(has_flow_data):
                    if year < flow_id_to_min_year[flow_id]:
                        flow_id_to_min_year[flow_id] = year
                    if year > flow_id_to_max_year[flow_id]:
                        flow_id_to_max_year[flow_id] = year

        # Fill with empty data until real Flow data is found
        year_start = min(df_flows.index)
        year_end = max(df_flows.index)
        for flow_id, flow_data in df_flows.items():
            data_min_year = flow_id_to_min_year[flow_data.name]
            empty_flow_data = copy.deepcopy(flow_data.loc[data_min_year])
            empty_flow_data.value = 0.0

            years_missing_flow_data = flow_data.loc[:data_min_year].drop(index=data_min_year)
            if len(years_missing_flow_data):
                for missing_year in years_missing_flow_data.keys():
                    empty_flow_data.year = missing_year
                    df_flows.at[missing_year, flow_id] = empty_flow_data

            # Start filling Flow data from min year for each Flow to next year
            # until new Flow data is found. Update current_flow_data to use found flow data.
            # Repeat this for the remaining years.
            current_flow_data = df_flows.at[data_min_year, flow_id]
            remaining_years = [year for year in flow_data.index if year > data_min_year]
            for year in remaining_years:
                existing_flow_data = df_flows.at[year, flow_id]
                if pd.isna(existing_flow_data):
                    # No flow data for this year
                    new_flow_data = copy.deepcopy(current_flow_data)
                    new_flow_data.year = year
                    df_flows.at[year, flow_id] = new_flow_data
                else:
                    # Update current_flow_data to use this years' data
                    current_flow_data = existing_flow_data

        # and propagate flow data for years that are missing flow data
        last_flow_data = {}
        df_result = df_flows.copy()
        for year in df_flow_id_has_data.index:
            for flow_id in df_flow_id_has_data.columns:
                if df_flow_id_has_data.at[year, flow_id]:
                    # Insert missing years as keys, sort the dictionary keys in ascending order
                    # Update flow ID to use data from this year
                    last_flow_data[flow_id] = df_result.at[year, flow_id]
                else:
                    # Skip to next if there is not yet last flow data
                    # This happens for all the years before flow data is first defined
                    if flow_id not in last_flow_data:
                        continue

                    new_data = copy.deepcopy(last_flow_data[flow_id])
                    new_data.year = year
                    df_result.at[year, flow_id] = new_data

        return df_result

    def _create_process_to_flow_ids(self, unique_process_ids, processes: List[Process], df_flows: pd.DataFrame) -> pd.DataFrame:
        df = pd.DataFrame(dtype="object", index=df_flows.index, columns=unique_process_ids)
        for year in df_flows.index:
            for process in processes:
                df.at[year, process.id] = {"process": copy.deepcopy(process), "flow_ids": {"in": [], "out": []}}

        # Add process inflows and outflows for every year
        for year in df_flows.index:
            for flow_id in df_flows.columns:
                # No data defined for process ID at this year
                flow = df_flows.at[year, flow_id]
                if pd.isnull(flow):
                    continue

                df.at[year, flow.source_process_id]["flow_ids"]["out"].append(flow.id)
                df.at[year, flow.target_process_id]["flow_ids"]["in"].append(flow.id)
        return df

    def _create_process_to_flows(self, unique_process_ids, processes: List[Process], df_flows: pd.DataFrame) -> pd.DataFrame:
        df = pd.DataFrame(dtype="object", index=df_flows.index, columns=unique_process_ids)
        for year in df_flows.index:
            for process in processes:
                df.at[year, process.id] = {"process": copy.deepcopy(process), "flows": {"in": [], "out": []}}

        # Add process inflows and outflows for every year
        for year in df_flows.index:
            for flow_id in df_flows.columns:
                # No data defined for process ID at this year
                flow = df_flows.at[year, flow_id]
                if pd.isnull(flow):
                    continue

                df.at[year, flow.source_process_id]["flows"]["out"].append(flow)
                df.at[year, flow.target_process_id]["flows"]["in"].append(flow)
        return df

    def _check_process_stock_parameters(self, processes: List[Process]):
        # Check if Process has valid definition for stock distribution type
        # Expected: Any keyword in allowed_distribution_types
        errors = []
        result_type = True
        print("Checking stock distribution types...")
        allowed_distribution_types = ["Fixed", "Normal", "LogNormal", "FoldedNormal", "Weibull"]
        for process in processes:
            if process.stock_distribution_type not in allowed_distribution_types:
                msg = "Process {} has invalid stock distribution type '{}' in row {} in sheet '{}'".format(
                    process.id, process.stock_distribution_type,
                    process.row_number, self.dataprovider.sheet_name_processes)
                errors.append(msg)

        if errors:
            for msg in errors:
                print("\t{}".format(msg))

            print("")
            print("\tValid stock distribution types are:")
            for distribution_type in allowed_distribution_types:
                print("\t{}".format(distribution_type))
            print("")
            result_type = False

        # Check if Process has valid parameters for stock distribution parameters
        # Expected: float or dictionary with valid keys (stddev, shape, scale)
        errors = []
        result_params = True
        print("Checking stock distribution parameters...")
        for process in processes:
            if process.stock_distribution_params is None:
                msg = "Process {} has invalid stock distribution parameter '{}' in row {} in sheet '{}'".format(
                    process.id, process.stock_distribution_params,
                    process.row_number, self.dataprovider.sheet_name_processes)
                errors.append(msg)
                continue

            # Mean uses StdDev
            # Normal uses Mean and StdDev
            # FoldedNormal uses Mean and StdDev
            # LogNormal uses Mean and StdDev
            required_params_for_distribution_type = {
                "Fixed": [""],
                "Normal": ['stddev'],
                "FoldedNormal": ['stddev'],
                "LogNormal": ['stddev'],
                "Weibull": ['shape', 'scale'],
            }

            is_fixed = process.stock_distribution_type == "Fixed"
            is_weibull = process.stock_distribution_type == "Weibull"
            is_float = type(process.stock_distribution_params) is float
            required_params = required_params_for_distribution_type[process.stock_distribution_type]
            num_required_params = len(required_params)
            missing_required_params = []
            for param in required_params:
                if num_required_params > 1 and is_float:
                    msg = "Stock distribution parameters was number, following parameters are required "
                    msg += "for distribution type '{}'".format(process.stock_distribution_type)
                    errors.append(msg)
                    for p in required_params:
                        errors.append("\t{}".format(p))

                if not is_float:
                    if is_fixed:
                        errors.append("Stock distribution type 'Fixed' needs only number as distribution parameter")
                        continue

                    if param not in process.stock_distribution_params:
                        errors.append("Stock distribution type '{}' needs following additional parameters:".format(
                            process.stock_distribution_type))
                        errors.append("\t{}".format(param))

        if errors:
            for msg in errors:
                print("{}".format(msg))
            result_params = False

        return result_type and result_params
