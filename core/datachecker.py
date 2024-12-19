import copy
from collections import namedtuple
from typing import List, Dict, Tuple, Union
import numpy as np
from core.dataprovider import DataProvider
from core.parameters import ParameterName, ParameterFillMethod
from core.datastructures import Process, Flow, Stock, ScenarioDefinition, Scenario, ScenarioData
from core.types import FunctionType, ChangeType
import pandas as pd


class DataChecker(object):
    def __init__(self, dataprovider: DataProvider = None):
        self._dataprovider = dataprovider
        self._processes = self._dataprovider.get_processes()
        self._flows = self._dataprovider.get_flows()
        self._stocks = self._dataprovider.get_stocks()
        self._scenario_definitions = self._dataprovider.get_scenario_definitions()
        self._year_to_flow_id_to_flow = {}
        self._year_start = 0
        self._year_end = 0
        self._years = []

    def build_scenarios(self, epsilon: float = 0.1) -> List[Scenario]:
        """
        Build scenarios to be solved using the FlowSolver.
        First element in the list is always baseline scenario and existence of this is always guaranteed.

        :param epsilon: Maximum allowed absolute difference in process inputs and outputs.\n
                        Generate warning message in case this happens.
                        Default: 0.1
        :return:        Dictionary with data for FlowSolver.\n
        """

        # NOTE: All flows must have data for the starting year
        processes = self._dataprovider.get_processes()
        flows = self._dataprovider.get_flows()
        stocks = self._dataprovider.get_stocks()

        model_params = self._dataprovider.get_model_params()
        detect_year_range = model_params[ParameterName.DetectYearRange]
        self._year_start = model_params[ParameterName.StartYear]
        self._year_end = model_params[ParameterName.EndYear]
        use_virtual_flows = model_params[ParameterName.UseVirtualFlows]

        # Default optional values
        # The default values are set inside DataProvider but
        # in this is to ensure that the optional parameters have default
        # values if they are missing from the settings file
        virtual_flows_epsilon = 0.1
        if use_virtual_flows and ParameterName.VirtualFlowsEpsilon in model_params:
            virtual_flows_epsilon = model_params[ParameterName.VirtualFlowsEpsilon]

        fill_missing_absolute_flows = True
        if ParameterName.FillMissingAbsoluteFlows in model_params:
            fill_missing_absolute_flows = model_params[ParameterName.FillMissingAbsoluteFlows]

        fill_missing_relative_flows = True
        if ParameterName.FillMissingRelativeFlows in model_params:
            fill_missing_relative_flows = model_params[ParameterName.FillMissingRelativeFlows]

        fill_method = ParameterFillMethod.Zeros
        if ParameterName.FillMethod in model_params:
            fill_method = model_params[ParameterName.FillMethod]

        # Checking options
        epsilon_inflows_outflows_mismatch = 0.1

        if not processes:
            print("DataChecker: No valid processes!")

        if not flows:
            print("DataChecker: No valid flows!")

        if not processes or not flows:
            raise SystemExit("No processes or flows found!")

        if detect_year_range:
            # Years are converted to int
            self._year_start, self._year_end = self._detect_year_range(flows)
        else:
            self._year_start = model_params[ParameterName.StartYear]
            self._year_end = model_params[ParameterName.EndYear]

        # Check if start year is after end year and vice versa
        if self._year_start > self._year_end:
            print("Start year is greater than end year! (start year: {}, end year: {})".format(
                self._year_start, self._year_end))
            print("Stopping execution...")
            raise SystemExit(-1)

        if self._year_end < self._year_start:
            print("End year is less than start year! (start year: {}, end year: {})".format(
                self._year_start, self._year_end))
            print("Stopping execution...")
            raise SystemExit(-1)

        # Build array of available years, last year is also included in year range
        self._years = self._get_year_range()

        # Get all unique Flow IDs and Process IDs that are used in the selected year range as dictionaries
        # because set does not preserve insertion order
        # Dictionaries preserve insertion order in Python version >= 3.7
        unique_flow_ids = self._get_unique_flow_ids_in_year_range(flows, self._years)
        unique_process_ids = self._get_unique_process_ids_in_year_range(flows, processes, self._years)
        df_year_to_flows = self._create_year_to_flow_data(unique_flow_ids, flows, self._years)

        # Check that source and target processes for flows are defined
        ok, errors = self._check_flow_sources_and_targets(unique_process_ids, df_year_to_flows)
        if not ok:
            print("Found following errors checking flow sources and targets:")
            for error in errors:
                print("\t{}".format(error))
            raise SystemExit(-1)

        # Check that there is not multiple definitions for the exact same flow per year
        # Exact means that source and target processes are the same
        ok, errors = self._check_flow_multiple_definitions_per_year(unique_flow_ids, flows, self._years)
        if not ok:
            print("Found following errors checking multiple flow definitions for same year:")
            for error in errors:
                print("\t{}".format(error))
            raise SystemExit(-1)

        # Check if stock distribution type and parameters are set and valid
        if not self._check_process_stock_parameters(processes):
            raise SystemExit(-1)

        # Create and propagate flow data for missing years
        df_year_to_flows = self._create_flow_data_for_missing_years(
            df_year_to_flows,
            fill_missing_absolute_flows=fill_missing_absolute_flows,
            fill_missing_relative_flows=fill_missing_relative_flows,
            fill_method=fill_method
        )

        # Create process to flow mappings
        df_year_to_process_flows = self._create_process_to_flows(unique_process_ids, df_year_to_flows)

        # Check if process only absolute inflows AND absolute outflows so that
        # the total inflow matches with the total outflows within certain limit
        print("Checking process total inflows and total outflows mismatches...")
        if not self._check_process_inflows_and_outflows_mismatch(df_year_to_process_flows,
                                                                 epsilon=epsilon_inflows_outflows_mismatch):
            pass

        # Check that flow type stays the same during the simulation
        print("Checking flow type changes...")
        ok, errors = self._check_flow_type_changes(df_year_to_flows)
        if not ok:
            for error in errors:
                print(error)
            raise SystemExit(-1)

        # Check if process has no inflows and only relative outflows:
        if not self._check_process_has_no_inflows_and_only_relative_outflows(df_year_to_process_flows):
            raise SystemExit(-1)

        # Check that the sheet ParameterName.SheetNameScenarios exists
        # and that it has properly defined data (source process ID, target process IDs, etc.)
        ok, errors = self.check_scenario_definitions(df_year_to_process_flows)
        if not ok:
            for error in errors:
                print(error)
            raise SystemExit(-1)

        # *************************************
        # * Unpack DataFrames to dictionaries *
        # *************************************

        # Create mapping of year -> Process ID -> Process by deep copying entry from DataFrame
        year_to_process_id_to_process = {}
        for year in df_year_to_process_flows.index:
            year_to_process_id_to_process[year] = {}
            for process_id in df_year_to_process_flows.columns:
                entry = copy.deepcopy(df_year_to_process_flows.at[year, process_id])
                process = entry["process"]
                year_to_process_id_to_process[year][process_id] = process

        # Create mapping of year -> Process ID -> List of incoming Flow IDs and list of outgoing Flow IDs
        year_to_process_id_to_flow_ids = {}
        for year in df_year_to_process_flows.index:
            year_to_process_id_to_flow_ids[year] = {}
            for process_id in df_year_to_process_flows.columns:
                entry = copy.deepcopy(df_year_to_process_flows.at[year, process_id])
                inflow_ids = [flow.id for flow in entry["flows"]["in"]]
                outflow_ids = [flow.id for flow in entry["flows"]["out"]]
                year_to_process_id_to_flow_ids[year][process_id] = {"in": inflow_ids, "out": outflow_ids}

        # Create mapping of year -> Flow ID -> Flow by deep copying entry from DataFrame
        year_to_flow_id_to_flow = {}
        for year in df_year_to_flows.index:
            year_to_flow_id_to_flow[year] = {}
            for flow_id in df_year_to_flows.columns:
                entry = copy.deepcopy(df_year_to_flows.at[year, flow_id])
                year_to_flow_id_to_flow[year][flow_id] = entry

        # Process ID to stock mapping
        process_id_to_stock = {}
        for stock in stocks:
            stock_id = stock.id
            process_id_to_stock[stock_id] = stock

        # List of all scenarios, first element is always the baseline scenario and always exists even if
        # any alternative scenarios are not defined
        scenarios = []
        print("Building baseline scenario...")
        baseline_scenario_data = ScenarioData(years=self._years,
                                              year_to_process_id_to_process=year_to_process_id_to_process,
                                              year_to_process_id_to_flow_ids=year_to_process_id_to_flow_ids,
                                              year_to_flow_id_to_flow=year_to_flow_id_to_flow,
                                              unique_process_id_to_process=unique_process_ids,
                                              unique_flow_id_to_flow=unique_flow_ids,
                                              process_id_to_stock=process_id_to_stock,
                                              stocks=stocks,
                                              use_virtual_flows=use_virtual_flows,
                                              virtual_flows_epsilon=virtual_flows_epsilon
                                              )

        baseline_scenario_definition = ScenarioDefinition(name="Baseline", flow_modifiers=[])
        baseline_scenario = Scenario(definition=baseline_scenario_definition, data=baseline_scenario_data)
        scenarios.append(baseline_scenario)

        # Create alternative Scenarios
        num_alternative_scenarios = len(self._scenario_definitions)
        print("Building {} alternative scenarios...".format(num_alternative_scenarios))
        for index, scenario_definition in enumerate(self._scenario_definitions):
            # Alternative scenarios do not have ScenarioData at this point, data is filled from the FlowSolver later
            new_alternative_scenario = Scenario(definition=scenario_definition, data=ScenarioData())
            scenarios.append(new_alternative_scenario)

        return scenarios

    def check_processes_integrity(self):
        # Check that there is only processes with unique ids
        result = True
        messages = []
        process_ids = set()
        duplicate_process_ids = []

        for process in self._processes:
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

        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow:
                source_process_id = flow.source_process_id
                target_process_id = flow.target_process_id

                if source_process_id not in self._processes:
                    flows_missing_source_ids.append(flow)

                if target_process_id not in self._processes:
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
        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            process_to_flows = {}
            for process in self._processes:
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

    def check_for_errors(self) -> Tuple[bool, List[str]]:
        ok, messages_processes = self.check_processes_integrity()
        if not ok:
            return False, messages_processes

        ok, messages_flows = self.check_flows_integrity()
        if not ok:
            return False, messages_flows

        return True, []

    def get_processes(self) -> List[Process]:
        return self._processes

    def get_flows(self) -> List[Flow]:
        return self._flows

    def get_stocks(self) -> List[Stock]:
        return self._stocks

    def get_start_year(self) -> int:
        return self.year_start

    def get_end_year(self) -> int:
        return self.year_end

    def get_year_to_flow_id_to_flow_mapping(self):
        return self._year_to_flow_id_to_flow

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
        """
        Get year range used in simulation as list of integers. Starting year and end year are included in the range.
        :return: List of years as integers
        """
        return [year for year in range(self._year_start, self._year_end + 1)]

    def _check_flow_sources_and_targets(self,
                                        unique_process_ids: dict[str, Process],
                                        df_year_to_flows: pd.DataFrame) -> [bool, List[str]]:
        """
        Check that all Flow sources and target Processes exists.

        :param unique_process_ids:
        :param df_year_to_flows: DataFrame
        :return: Tuple (True, list of errors)
        """
        errors = []
        sheet_name_flows = self._dataprovider.sheet_name_flows
        for year in df_year_to_flows.index:
            for flow_id in df_year_to_flows.columns:
                flow = df_year_to_flows.at[year, flow_id]
                if pd.isnull(flow):
                    continue

                if flow.source_process_id not in unique_process_ids:
                    s = "No source process {} for flow {} (row number {}) in year {} (in Excel sheet {}) ".format(
                        flow.source_process_id, flow_id, flow.row_number, year, sheet_name_flows)
                    errors.append(s)

                if flow.target_process_id not in unique_process_ids:
                    s = "No target process {} for flow {} (row number {}) in year {} (sheet {})".format(
                        flow.target_process_id, flow_id, flow.row_number, year, sheet_name_flows)
                    errors.append(s)

        return not errors, errors

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

    def _get_unique_flow_ids_in_year_range(self, flows: list[Flow], years: list[int]) -> dict[str, Flow]:
        """
        Get unique Flow IDs used in the year range as dictionary [Flow ID -> Flow].

        :param flows: List of Flows
        :param years: List of years
        :return: Dictionary [Flow ID -> Flow]
        """
        unique_flow_id_to_flow = {}
        for flow in flows:
            flow_year = flow.year
            if flow_year not in years:
                continue

            flow_id = flow.id
            if flow_id not in unique_flow_id_to_flow:
                unique_flow_id_to_flow[flow_id] = flow

        return unique_flow_id_to_flow

    def _get_unique_process_ids_in_year_range(self,
                                              flows: list[Flow],
                                              processes: list[Process],
                                              years: list[int]) -> dict[str, Process]:
        """
        Get unique Process IDs used in the year range as dictionary [Process ID -> Process].

        :param flows: List of Flows
        :param years: List of years
        :return: Dictionary [Process ID -> Process]
        """
        # Map Process IDs to Processes (this contains all Processes)
        process_id_to_process = {}
        for process in processes:
            process_id = process.id
            process_id_to_process[process_id] = process

        # Map all unique Process IDs to Processes
        unique_process_id_to_process = {}
        for flow in flows:
            flow_year = flow.year
            if flow_year not in years:
                continue

            source_process_id = flow.source_process_id
            if source_process_id not in unique_process_id_to_process:
                source_process = process_id_to_process[source_process_id]
                unique_process_id_to_process[source_process_id] = source_process

            target_process_id = flow.target_process_id
            if target_process_id not in unique_process_id_to_process:
                target_process = process_id_to_process[target_process_id]
                unique_process_id_to_process[target_process_id] = target_process

        return unique_process_id_to_process

    def _create_year_to_flow_mapping(self, flows) -> Dict[int, Dict[str, Flow]]:
        year_to_flow_id_to_flow = {}
        for flow in flows:
            if flow.year not in year_to_flow_id_to_flow:
                year_to_flow_id_to_flow[flow.year] = {}

            if flow.id not in year_to_flow_id_to_flow[flow.year]:
                year_to_flow_id_to_flow[flow.year][flow.id] = flow
        return year_to_flow_id_to_flow

    def _create_year_to_flow_data(self,
                                  unique_flow_ids: dict[str, Flow],
                                  flows: list[Flow],
                                  years: list[int]) -> pd.DataFrame:
        """
        Create DataFrame that has year as index and Flow IDs as column and cell is Flow-object.

        :param unique_flow_ids: Dictionary of unique [Flow ID -> Flow]
        :param flows: List of Flows
        :param years: list of years
        :return: DataFrame
        """

        df = pd.DataFrame(index=years, columns=unique_flow_ids.keys())
        for flow in flows:
            if flow.year not in years:
                continue

            df.at[flow.year, flow.id] = flow

        return df

    def _check_flow_multiple_definitions_per_year(self,
                                                  unique_flow_ids: Dict[str, Flow],
                                                  flows: List[Flow],
                                                  years: list[int]
                                                  ) -> Tuple[bool, List[str]]:
        """
        Check that there is only one Flow definition per year.

        :param unique_flow_ids: Dictionary of unique [Flow ID -> Flow]
        :param flows: List of Flows
        :param years: List of years
        :return: True if successful, False otherwise
        """
        errors = []
        sheet_name_flows = self._dataprovider.sheet_name_flows
        df = pd.DataFrame(index=years, columns=unique_flow_ids)
        for flow in flows:
            if flow.year not in years:
                continue

            if flow.year > max(years):
                continue

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
                    s = "Multiple definitions for the same flow '{}' in year {} in sheet named '{}':".format(
                        target_flow.id, target_flow.year, sheet_name_flows)
                    errors.append(s)

                    for duplicate_flow in existing_flows:
                        s = "- in row {}".format(duplicate_flow.row_number)
                        errors.append(s)

        return not errors, errors

    def _check_process_inflows_and_outflows_mismatch(self,
                                                     df_process_to_flows: pd.DataFrame,
                                                     epsilon: float = 0.1) -> Tuple[bool, List[str]]:
        errors = []
        sheet_name_flows = self._dataprovider.sheet_name_flows
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
                        s = "Total inflows and total outflows for process '{}' does not match.".format(process_id)
                        errors.append(s)

                        s = "Absolute difference of total inflows and total outflows was {}".format(diff_abs)
                        errors.append(s)

                        s = "Check following inflows in Excel sheet '{}':".format(sheet_name_flows)
                        errors.append(s)
                        for flow in inflows:
                            s = "- flow '{}' in row {}".format(flow.id, flow.row_number)
                            errors.append(s)

                        print("Check following outflows:")
                        for flow in outflows:
                            s = "- flow '{}' in row {}".format(flow.id, flow.row_number)
                            errors.append(s)

                        s = ""
                        errors.append(s)
                        result = False

        return not errors, errors

    def _check_flow_type_changes(self, df_year_to_flows: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Check that flows do not change the type during the simulation.

        :param df_year_to_flows: DataFrame
        :return: Tuple (bool, list of errors)
        """
        errors = []
        for flow_id in df_year_to_flows.columns:
            is_flow_abs_entry = []
            flow_data = df_year_to_flows[flow_id]
            for year, flow in flow_data.items():
                if pd.notna(flow):
                    new_entry = [flow.is_unit_absolute_value, year]
                    is_flow_abs_entry.append(new_entry)

            # Compare the rest of the list for the first state
            initial_entry = is_flow_abs_entry[0]
            is_same_as_initial_state = [entry[0] == initial_entry[0] for entry in is_flow_abs_entry]
            if not all(is_same_as_initial_state):
                source_type_name = "absolute" if initial_entry[0] else "relative"
                target_type_name = "relative" if initial_entry[0] else "absolute"
                for entry in is_flow_abs_entry:
                    if entry[0] != initial_entry[0]:
                        s = "\t- Flow '{}' was defined initially as {} in year {} but changed to {} in year {}".format(
                            flow_id, source_type_name, initial_entry[1], target_type_name, entry[1])
                        errors.append(s)

        return not errors, errors

    def _create_flow_id_has_data_mapping(self, df_flows) -> pd.DataFrame:
        df = df_flows.copy()
        for flow_id in df.columns:
            df[flow_id] = np.where(pd.isnull(df[flow_id]), False, True)
        return df

    def _create_flow_data_for_missing_years(self,
                                            df_year_flows: pd.DataFrame,
                                            fill_missing_absolute_flows: bool,
                                            fill_missing_relative_flows: bool,
                                            fill_method: str = ParameterFillMethod.Zeros
                                            ) -> pd.DataFrame:
        """
        Fill years missing Flow data with the previous valid Flow data.\n
        If fill_absolute_flows is set to True then process Flows with absolute values.\n
        If fill_relative_values is set to True then process Flows with relative values.\n
        If both fill_absolute_flows and fill_relative_flows are set to False then returns copy
        of the original.\n

        :param df_flows:
        :param fill_missing_absolute_flows: If True then process Flows with absolute values
        :param fill_missing_relative_flows: If True then process Flows with relative values
        :return: DataFrame
        """
        # No filling, convert nan in DataFrame to None
        if (not fill_missing_absolute_flows) and (not fill_missing_relative_flows):
            result = df_year_flows.copy()
            return result

        # Create flow has data as boolean mapping
        df_flow_id_has_data = df_year_flows.copy()
        for flow_id in df_flow_id_has_data.columns:
            df_flow_id_has_data[flow_id] = np.where(pd.isnull(df_flow_id_has_data[flow_id]), False, True)

        # Find earliest and latest year of Flow data for each Flow ID
        flow_id_to_min_year = {flow_id: max(df_year_flows.index) for flow_id in df_year_flows}
        flow_id_to_max_year = {flow_id: min(df_year_flows.index) for flow_id in df_year_flows}
        for flow_id in df_year_flows.columns:
            for year, has_flow_data in df_year_flows[flow_id].items():
                if pd.notna(has_flow_data):
                    if year < flow_id_to_min_year[flow_id]:
                        flow_id_to_min_year[flow_id] = year
                    if year > flow_id_to_max_year[flow_id]:
                        flow_id_to_max_year[flow_id] = year

        # Find gaps flow data columns and set values according to fill_method
        year_start = min(df_year_flows.index)
        year_end = max(df_year_flows.index)
        for flow_id in df_year_flows.columns:
            flow_data = df_year_flows[flow_id]
            flow_has_data = df_flow_id_has_data[flow_id]

            # NOTE: Now checks the flow type on from the first occurrence of flow data and assume that the flow type
            # NOTE: does not change during the years
            first_valid_flow = flow_data[flow_id_to_min_year[flow_id]]
            is_abs_flow = first_valid_flow.is_unit_absolute_value
            is_rel_flow = not is_abs_flow

            # Skip to next if not using filling for flow type
            if is_abs_flow and not fill_missing_absolute_flows:
                continue

            if is_rel_flow and not fill_missing_relative_flows:
                continue

            if fill_method == ParameterFillMethod.Zeros:
                # Fill all missing flow values with zeros
                flow_id_min_year = flow_id_to_min_year[flow_data.name]
                missing_flow_base = copy.deepcopy(flow_data.loc[flow_id_min_year])
                for year, has_data in flow_has_data.items():
                    if not has_data:
                        new_flow_data = copy.deepcopy(missing_flow_base)
                        new_flow_data.value = 0.0
                        new_flow_data.year = year
                        flow_data[year] = new_flow_data
                        flow_has_data[year] = True

            if fill_method == ParameterFillMethod.Previous:
                # Fill all missing flow values using the last found flow values
                # NOTE: Do not fill flows if flows are missing at the start of the flow_data
                flow_data.ffill(inplace=True)

                # DataFrame.ffill copies the object that the new created object references
                # to the last found flow object so overwrite all objects in flow_data
                # with the new deepcopied flow object
                for year, flow in flow_data.items():
                    if pd.isna(flow):
                        continue

                    new_flow = copy.deepcopy(flow)
                    new_flow.year = year
                    flow_data.at[year] = new_flow
                    flow_has_data[year] = True

            if fill_method == ParameterFillMethod.Next:
                # Fill all missing flow values using the next found flow values
                # NOTE: Do not fill flows if flows are missing at the end of the flow_data
                flow_data.bfill(inplace=True)

                # DataFrame.bfill copies the object that the new created object references
                # to the last found flow object so overwrite all objects in flow_data
                # with the new deepcopied flow object
                for year, flow in flow_data.items():
                    if pd.isna(flow):
                        continue

                    new_flow = copy.deepcopy(flow)
                    new_flow.year = year
                    flow_data.at[year] = new_flow
                    flow_has_data[year] = True

            if fill_method == ParameterFillMethod.Interpolate:
                # Fill all missing flow values using interpolation
                # Do not fill flow values if missing at the start of flow_data or missing at the end of flow_data
                flow_values = flow_data.copy()
                for year, has_data in flow_has_data.items():
                    if not has_data:
                        continue

                    flow_values[year] = flow_data[year].value

                flow_values = flow_values.astype("float64")
                flow_values.interpolate(limit_direction="forward", inplace=True)

                # Get first valid flow data and use that as missing flow base
                flow_id_min_year = flow_id_to_min_year[flow_data.name]
                missing_flow_base = copy.deepcopy(flow_data.loc[flow_id_min_year])
                for year, interpolated_value in flow_values.items():
                    if pd.isna(interpolated_value):
                        continue

                    new_flow = copy.deepcopy(missing_flow_base)
                    new_flow.value = flow_values[year]
                    new_flow.year = year
                    flow_data[year] = new_flow
                    flow_has_data[year] = True

        return df_year_flows

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

    def _create_process_to_flows(self,
                                 unique_process_ids: dict[str, Process],
                                 df_year_flows: pd.DataFrame) -> pd.DataFrame:
        """

        :param unique_process_ids: Dictionary of unique [Process ID -> Process]
        :param df_year_flows: DataFrame, year to Flows
        :return: DataFrame
        """

        df = pd.DataFrame(index=df_year_flows.index, columns=unique_process_ids.keys(), dtype="object")
        for year in df_year_flows.index:
            for process_id, process in unique_process_ids.items():
                df.at[year, process.id] = {"process": copy.deepcopy(process), "flows": {"in": [], "out": []}}

        # Add process inflows and outflows for every year
        for year in df_year_flows.index:
            for flow_id in df_year_flows.columns:
                # No data defined for process ID at this year
                flow = df_year_flows.at[year, flow_id]
                if pd.isnull(flow):
                    continue

                df.at[year, flow.source_process_id]["flows"]["out"].append(flow)
                df.at[year, flow.target_process_id]["flows"]["in"].append(flow)
        return df

    def _check_process_stock_parameters(self, processes: List[Process]):
        """
        Check if Process has valid definition for stock distribution type
        :param processes: List of Processes
        :return: True if no errors, False otherwise
        """
        errors = []
        result_type = True
        print("Checking stock distribution types...")
        allowed_distribution_types = ["Fixed", "Simple", "Normal", "LogNormal", "FoldedNormal", "Weibull"]
        for process in processes:
            if process.stock_distribution_type not in allowed_distribution_types:
                msg = "Process {} has invalid stock distribution type '{}' in row {} in sheet '{}'".format(
                    process.id, process.stock_distribution_type,
                    process.row_number, self._dataprovider.sheet_name_processes)
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
                    process.row_number, self._dataprovider.sheet_name_processes)
                errors.append(msg)
                continue

            # Fixed uses Mean
            # Simple uses Mean
            # Normal uses Mean and StdDev
            # FoldedNormal uses Mean and StdDev
            # LogNormal uses Mean and StdDev
            required_params_for_distribution_type = {
                "Fixed": [""],
                "Simple": [""],
                "Normal": ['stddev'],
                "FoldedNormal": ['stddev'],
                "LogNormal": ['stddev'],
                "Weibull": ['shape', 'scale'],
            }

            is_fixed = process.stock_distribution_type == "Fixed"
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
                    if param not in process.stock_distribution_params:
                        errors.append("Stock distribution type '{}' needs following additional parameters:".format(
                            process.stock_distribution_type))
                        errors.append("\t{}".format(param))

        if errors:
            for msg in errors:
                print("{}".format(msg))
            result_params = False

        return result_type and result_params

    def _check_process_has_no_inflows_and_only_relative_outflows(self, df_year_to_process_flows: pd.DataFrame) -> bool:
        """
        Check for Processes that have no inflows and have only relative outflows.
        This is error in data.

        :param df_year_to_process_flows: DataFrame (index: year, column: Process name, cell: Dictionary)
        :return: True if no errors, False otherwise
        """
        print("Checking for processes that have no inflows and only relative outflows...")
        year_to_errors = {}
        for year in df_year_to_process_flows.index:
            row = df_year_to_process_flows.loc[year]
            for entry in row:
                # entry is Dictionary (keys: "process", "flows")
                process = entry["process"]
                flows = entry["flows"]
                flows_in = flows["in"]
                flows_out = flows["out"]

                no_inflows = len(flows_in) == 0
                all_outflows_relative = len(flows_out) > 0 and all([not flow.is_unit_absolute_value for flow in flows_out])

                if no_inflows and all_outflows_relative:
                    if year not in year_to_errors:
                        year_to_errors[year] = []
                    year_to_errors[year].append("{}".format(process.id))

        has_errors = len(year_to_errors.keys()) > 0
        if has_errors:
            msg = "DataChecker: Found following Processes that can not be evaluated" + \
                    " (= processes have no inflows and have ONLY relative outflows)\n"

            msg += "Ensure that any process causing an error has at least one absolute incoming flow in the first year"
            print(msg)
            for year, errors in year_to_errors.items():
                print("Year {} ({} errors):".format(year, len(errors)))
                for msg in errors:
                    print("\t{}".format(msg))
                print("")

        return not has_errors

    def check_scenario_definitions(self, df_year_to_process_flows: pd.DataFrame):
        print("Checking scenario definitions...")
        errors = []
        scenario_definitions = self._scenario_definitions
        valid_years = list(df_year_to_process_flows.index)
        first_valid_year = min(valid_years)
        last_valid_year = max(valid_years)
        for scenario_definition in scenario_definitions:
            scenario_name = scenario_definition.name
            flow_modifiers = scenario_definition.flow_modifiers

            for flow_modifier in flow_modifiers:
                error_message_prefix = "Error in flow modifier in row {} (scenario '{}'): ".format(
                    flow_modifier.row_number, scenario_name)

                # Check that all required node IDs are valid during the defined time range
                source_process_id = flow_modifier.source_process_id
                target_process_id = flow_modifier.target_process_id
                opposite_target_process_ids = flow_modifier.opposite_target_process_ids

                # Is the flow modifier in valid year range?
                start_year = flow_modifier.start_year
                end_year = flow_modifier.end_year
                years = [year for year in range(flow_modifier.start_year, flow_modifier.end_year + 1)]

                # Check rule for start year
                if start_year < first_valid_year:
                    s = "" + error_message_prefix
                    s += "Source Process ID '{}' start year ({}) is before first year of simulation ({})".format(
                        source_process_id, start_year, first_valid_year)
                    errors.append(s)

                # Check rule for last year
                if end_year > last_valid_year:
                    s = "" + error_message_prefix
                    s += "Source Process ID '{}' end year ({}) is after last year of simulation ({})".format(
                        source_process_id, end_year, last_valid_year)
                    errors.append(s)

                # Check if source Process ID exists for the defined year range
                for year in years:
                    year_data = df_year_to_process_flows[df_year_to_process_flows.index == year]
                    if source_process_id not in year_data.columns:
                        s = "" + error_message_prefix
                        s += "Source Process ID '{}' not defined for the year {}".format(source_process_id, year)
                        errors.append(s)

                    # Check if target Process ID exists for the defined year range
                    if target_process_id not in year_data.columns:
                        s = "" + error_message_prefix
                        s += "Target Process ID '{}' not defined for the year {}".format(source_process_id, year)
                        errors.append(s)

                    entry = year_data.at[year, source_process_id]
                    process = entry["process"]
                    flows_out = entry["flows"]["out"]
                    target_process_id_to_flow = {flow.target_process_id: flow for flow in flows_out}
                    source_to_target_flow = target_process_id_to_flow.get(target_process_id, None)

                    # Check that source Process ID is connected to target Process ID
                    if source_to_target_flow is None:
                        s = "" + error_message_prefix
                        s += "Source Process ID '{}' does not have outflow to target Process ID {}".format(
                            source_process_id, target_process_id)
                        errors.append(s)
                        continue

                    # Check that the flows from source Process ID to opposite target Process ID exists
                    for opposite_target_process_id in opposite_target_process_ids:
                        source_to_opposite_target_flow = target_process_id_to_flow.get(opposite_target_process_id, None)
                        if source_to_opposite_target_flow is None:
                            s = "" + error_message_prefix
                            s += "Process ID '{}' does not have outflow to opposite target Process ID {}".format(
                                source_process_id, opposite_target_process_id)
                            errors.append(s)
                            continue

                        # Check that the flow from source Process to opposite target Process has the same type (absolute
                        # or relative) as the flow from source Process to target Process
                        is_source_to_target_flow_abs = source_to_target_flow.is_unit_absolute_value
                        is_source_to_opposite_target_flow_abs = source_to_opposite_target_flow.is_unit_absolute_value
                        if is_source_to_target_flow_abs != is_source_to_opposite_target_flow_abs:
                            source_to_target_flow_type = "absolute" if is_source_to_target_flow_abs else "relative"
                            source_to_opposite_flow_type = "absolute" if is_source_to_opposite_target_flow_abs else "relative"
                            s = "" + error_message_prefix
                            s += "Source Process ID {} to target Process ID {} is {} flow".format(
                                source_process_id, target_process_id, source_to_target_flow_type)

                            s += " but flow from source Process ID {} to opposite target Process ID {} is {} flow".format(
                                source_process_id, opposite_target_process_id, source_to_opposite_flow_type)
                            errors.append(s)

                change_type_names = [change_type.value for change_type in ChangeType]
                function_type_names = [function_type.value for function_type in FunctionType]
                if flow_modifier.change_type not in change_type_names:
                    s = "" + error_message_prefix
                    s += "Invalid change type '{}'".format(flow_modifier.change_type)
                    errors.append(s)

                if flow_modifier.function_type not in function_type_names:
                    s = "" + error_message_prefix
                    s += "Invalid function type: '{}'".format(flow_modifier.function_type)
                    errors.append(s)

                if flow_modifier.function_type is FunctionType.Constant:
                    if not flow_modifier.use_target_value:
                        s = "" + error_message_prefix
                        s += "No target value set"
                        errors.append(s)
                else:
                    if not flow_modifier.use_change_in_value and not flow_modifier.use_target_value:
                        s = "" + error_message_prefix
                        s += "No change in value or target value set"
                        errors.append(s)

                if flow_modifier.use_target_value:
                    # Target flow type must match with the change type
                    # Flow type must match with the ChangeType:
                    # - Absolute flows must have change_type == ChangeType.Value
                    # - Relative flows must have change_type == ChangeType.Proportional
                    is_flow_abs = source_to_target_flow.is_unit_absolute_value
                    is_flow_rel = not is_flow_abs
                    if is_flow_abs and flow_modifier.change_type is not ChangeType.Value:
                        s = "" + error_message_prefix
                        s += "Target value change type must be Value for absolute flow"
                        errors.append(s)

                    if is_flow_rel and flow_modifier.change_type is not ChangeType.Proportional:
                        s = "" + error_message_prefix
                        s += "Target value change type must be % for relative flow"
                        errors.append(s)

                    if flow_modifier.target_value is not None and flow_modifier.target_value < 0.0:
                        s = "" + error_message_prefix
                        s += "Target value must be > 0.0"
                        errors.append(s)

        return not errors, errors
