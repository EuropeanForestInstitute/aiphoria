import copy
from enum import Enum
from typing import List, Dict, Tuple, Set, Any

import numpy as np
import pandas as pd

from core.dataprovider import DataProvider
from core.datastructures import Process, Flow, Stock, ScenarioDefinition, Scenario, ScenarioData, Color, ProcessEntry
from core.parameters import ParameterName, ParameterFillMethod, StockDistributionType,\
    RequiredStockDistributionParameters, AllowedStockDistributionParameterValues
from core.types import FunctionType, ChangeType


class DataChecker(object):
    def __init__(self, dataprovider: DataProvider = None):
        self._dataprovider = dataprovider
        self._processes = self._dataprovider.get_processes()
        self._flows = self._dataprovider.get_flows()
        self._stocks = self._dataprovider.get_stocks()
        self._scenario_definitions = self._dataprovider.get_scenario_definitions()
        self._color_definitions = self._dataprovider.get_color_definitions()
        self._year_to_flow_id_to_flow = {}
        self._year_start = 0
        self._year_end = 0
        self._years = []

    def build_scenarios(self) -> List[Scenario]:
        """
        Build scenarios to be solved using the FlowSolver.
        First element in the list is always baseline scenario and existence of this is always guaranteed.

        :return: Dictionary with data for FlowSolver
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
        baseline_value_name = model_params[ParameterName.BaselineValueName]
        baseline_unit_name = model_params[ParameterName.BaselineUnitName]

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

        if not processes:
            error = "No valid processes!"
            raise Exception([error])

        if not flows:
            error = "No valid flows!"
            raise Exception([error])

        if not processes or not flows:
            error = "No processes or flows!"
            raise Exception([error])

        if detect_year_range:
            self._year_start, self._year_end = self._detect_year_range(flows)
        else:
            self._year_start = model_params[ParameterName.StartYear]
            self._year_end = model_params[ParameterName.EndYear]

        # Check if start year is after end year and vice versa
        if self._year_start > self._year_end:
            error = "Start year is greater than end year! (start year: {}, end year: {})".format(
                self._year_start, self._year_end)
            raise Exception([error])

        if self._year_end < self._year_start:
            error = "End year is less than start year! (start year: {}, end year: {})".format(
                self._year_start, self._year_end)
            raise Exception([error])

        # Check if data years are outside defined year range
        ok, errors = self._check_if_data_is_outside_year_range(flows)
        if not ok:
            raise Exception(errors)

        # Build array of available years, last year is also included in year range
        self._years = self._get_year_range()

        # Get all unique Flow IDs and Process IDs that are used in the selected year range as dictionaries
        # because set does not preserve insertion order
        # Dictionaries preserve insertion order in Python version >= 3.7
        unique_flow_ids = self._get_unique_flow_ids_in_year_range(flows, self._years)
        unique_process_ids = self._get_unique_process_ids_in_year_range(flows, processes, self._years)
        df_year_to_flows = self._create_year_to_flow_data(unique_flow_ids, flows, self._years)

        # **********************************
        # * Check invalid parameter values *
        # **********************************

        print("Checking processes for inflow visualization...")
        process_ids_for_inflow_viz = model_params[ParameterName.VisualizeInflowsToProcesses]
        ok, errors = self._check_process_ids_for_inflow_visualization(process_ids_for_inflow_viz, unique_process_ids)
        if not ok:
            raise Exception(errors)

        # Check that source and target processes for flows are defined
        print("Checking flow source and target processes...")
        ok, errors = self._check_flow_sources_and_targets(unique_process_ids, df_year_to_flows)
        if not ok:
            raise Exception(errors)

        # Check that there is not multiple definitions for the exact same flow per year
        # Exact means that source and target processes are the same
        print("Checking multiple flow definitions in the same year...")
        ok, errors = self._check_flow_multiple_definitions_per_year(unique_flow_ids, flows, self._years)
        if not ok:
            raise Exception(errors)

        # Check if stock distribution type and parameters are set and valid
        print("Checking process stock parameters...")
        ok, errors = self._check_process_stock_parameters(processes)
        if not ok:
            raise Exception(errors)

        # Check if stocks are defined in processes that do not have any inflows and outflows at any year
        print("Checking stocks in isolated processes...")
        ok, errors = self._check_stocks_in_isolated_processes(stocks, unique_process_ids)
        if not ok:
            raise Exception(errors)

        if fill_missing_absolute_flows or fill_missing_absolute_flows:
            print("Checking fill method requirements...")
            ok, errors = self._check_fill_method_requirements(fill_method, df_year_to_flows)
            if not ok:
                raise Exception(errors)

        # Create and propagate flow data for missing years
        df_year_to_flows = self._create_flow_data_for_missing_years(
            df_year_to_flows,
            fill_missing_absolute_flows=fill_missing_absolute_flows,
            fill_missing_relative_flows=fill_missing_relative_flows,
            fill_method=fill_method
        )

        # Create process to flow mappings
        df_year_to_process_flows = self._create_process_to_flows_entries(unique_process_ids, df_year_to_flows)

        print("Merge relative outflows...")
        # NOTE: This is externalized in the future, now go with the hardcoded value
        # min_threshold is value for checking if flow is 100%: any relative flow share greater than min_threshold
        # are considered relative flows with 100% share.
        min_threshold = 99.99
        df_year_to_process_flows, df_year_to_flows = self._merge_relative_outflows(df_year_to_process_flows,
                                                                                   df_year_to_flows,
                                                                                   min_threshold)

        # Remove isolated processes caused by the flow merging
        df_year_to_process_flows = self._remove_isolated_processes(df_year_to_process_flows)

        # Check that root flows have no inflows and only absolute outflows
        print("Checking root processes...")
        ok, errors = self._check_root_processes(df_year_to_process_flows)
        if not ok:
            raise Exception(errors)

        # Check if process only absolute inflows AND absolute outflows so that
        # the total inflow matches with the total outflows within certain limit
        if not model_params[ParameterName.UseVirtualFlows]:
            print("Checking process total inflows and total outflows mismatches...")
            ok, errors = self._check_process_inflows_and_outflows_mismatch(df_year_to_process_flows,
                                                                           epsilon=virtual_flows_epsilon)
            if not ok:
                raise Exception(errors)

        print("Checking relative flow errors...")
        ok, errors = self._check_relative_flow_errors(df_year_to_flows)
        if not ok:
            raise Exception(errors)

        # Check if process has no inflows and only relative outflows:
        print("Checking processes with no inflows and only relative outflows...")
        ok, errors = self._check_process_has_no_inflows_and_only_relative_outflows(df_year_to_process_flows)
        if not ok:
            raise Exception(errors)

        print("Checking isolated/unconnected processes...")
        ok, errors = self._check_for_isolated_processes(df_year_to_process_flows)
        if not ok:
            raise Exception(errors)

        print("Checking prioritized locations...")
        ok, errors = self._check_prioritized_locations(self._processes, model_params)
        if not ok:
            raise Exception(errors)

        print("Checking prioritized transformation stages...")
        ok, errors = self._check_prioritized_transformation_stages(self._processes, model_params)
        if not ok:
            raise Exception(errors)

        # Check that the sheet ParameterName.SheetNameScenarios exists
        # and that it has properly defined data (source process ID, target process IDs, etc.)
        print("Checking scenario definitions...")
        ok, errors = self._check_scenario_definitions(df_year_to_process_flows)
        if not ok:
            raise Exception(errors)

        # Check that colors have both name and valid value
        print("Checking color definitions...")
        ok, errors = self._check_color_definitions(self._color_definitions)
        if not ok:
            raise Exception(errors)

        print("Checking flow indicators...")
        ok, errors = self._check_flow_indicators(df_year_to_flows)
        if not ok:
            raise Exception(errors)

        # *************************************
        # * Unpack DataFrames to dictionaries *
        # *************************************

        # Create mapping of year -> Process ID -> Process by deep copying entry from DataFrame
        year_to_process_id_to_process = {}
        for year in df_year_to_process_flows.index:
            year_to_process_id_to_process[year] = {}
            for process_id in df_year_to_process_flows.columns:
                entry = df_year_to_process_flows.at[year, process_id]
                if pd.isna(entry):
                    continue

                new_entry = copy.deepcopy(entry)
                process = new_entry.process

                year_to_process_id_to_process[year][process_id] = process

        # Create mapping of year -> Process ID -> List of incoming Flow IDs and list of outgoing Flow IDs
        year_to_process_id_to_flow_ids = {}
        for year in df_year_to_process_flows.index:
            year_to_process_id_to_flow_ids[year] = {}
            for process_id in df_year_to_process_flows.columns:
                entry = df_year_to_process_flows.at[year, process_id]
                if pd.isna(entry):
                    continue

                new_entry: ProcessEntry = copy.deepcopy(entry)
                inflow_ids = [flow.id for flow in entry.inflows]
                outflow_ids = [flow.id for flow in entry.outflows]
                year_to_process_id_to_flow_ids[year][process_id] = {"in": inflow_ids, "out": outflow_ids}

        # Create mapping of year -> Flow ID -> Flow by deep copying entry from DataFrame
        year_to_flow_id_to_flow = {}
        for year in df_year_to_flows.index:
            year_to_flow_id_to_flow[year] = {}
            for flow_id in df_year_to_flows.columns:
                entry = df_year_to_flows.at[year, flow_id]
                if pd.isna(entry):
                    continue

                new_entry = copy.deepcopy(df_year_to_flows.at[year, flow_id])
                year_to_flow_id_to_flow[year][flow_id] = new_entry

        # Process ID to stock mapping
        process_id_to_stock = {}
        for stock in stocks:
            stock_id = stock.id
            process_id_to_stock[stock_id] = stock

        # Copy Indicator mappings from first unique Flow (Indicator ID -> Indicator)
        # and set indicator conversion factors to default values.
        # NOTE: Virtual flows creation uses directly these default values
        first_unique_flow = unique_flow_ids[list(unique_flow_ids.keys())[0]]
        indicator_name_to_indicator = copy.deepcopy(first_unique_flow.indicator_name_to_indicator)
        for name, indicator in indicator_name_to_indicator.items():
            indicator.conversion_factor = 1.0

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
                                              virtual_flows_epsilon=virtual_flows_epsilon,
                                              baseline_value_name=baseline_value_name,
                                              baseline_unit_name=baseline_unit_name,
                                              indicator_name_to_indicator=indicator_name_to_indicator
                                              )

        baseline_scenario_definition = ScenarioDefinition(name="Baseline", flow_modifiers=[])
        baseline_scenario = Scenario(definition=baseline_scenario_definition,
                                     data=baseline_scenario_data,
                                     model_params=model_params)
        scenarios.append(baseline_scenario)

        # Create alternative Scenarios
        num_alternative_scenarios = len(self._scenario_definitions)
        print("Building {} alternative scenarios...".format(num_alternative_scenarios))
        for index, scenario_definition in enumerate(self._scenario_definitions):
            # Alternative scenarios do not have ScenarioData at this point, data is filled from the FlowSolver later
            new_alternative_scenario = Scenario(definition=scenario_definition,
                                                data=ScenarioData(),
                                                model_params=model_params)
            scenarios.append(new_alternative_scenario)

        return scenarios

    def check_processes_integrity(self):
        # Check that there is only processes with unique ids
        errors = []
        process_id_to_processes = {}
        for process in self._processes:
            process_id = process.id
            if process_id not in process_id_to_processes:
                process_id_to_processes[process_id] = []

            list_of_processes = process_id_to_processes[process_id]
            list_of_processes.append(process)

        for process_id, list_of_processes in process_id_to_processes.items():
            if len(list_of_processes) > 1:
                s = "Found multiple processes with the same ID in sheet '{}':\n".format(
                    self._dataprovider.sheet_name_processes)
                for process in list_of_processes:
                    s += "\t- {} (row {})\n".format(process, process.row_number)
                errors.append(s)

        return not errors, errors

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

    def _check_for_isolated_processes(self, df_year_to_process_to_flows: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Check for isolated Processes (= processes that have no inflows and no outflows) in any year.
        This is most likely error in data.

        :return: Tuple (has errors (bool), list of errors (list[str]))
        """
        errors = []
        for process_id in df_year_to_process_to_flows.columns:
            flow_data = df_year_to_process_to_flows[[process_id]]
            has_inflows = False
            has_outflows = False
            for year in flow_data.index:
                entry: ProcessEntry = flow_data.at[year, process_id]
                if entry is pd.NA:
                    continue

                has_inflows = has_inflows or len(entry.inflows) > 0
                has_inflows = has_inflows or len(entry.outflows) > 0

            if (not has_inflows) and (not has_outflows):
                errors.append("ERROR: Found isolated Process '{}', no inflows and no outflows at any year".format(
                    process_id))

        return not errors, errors

    def _check_prioritized_transformation_stages(self, processes: List[Process], model_params: Dict[str, Any])\
            -> Tuple[bool, List[str]]:
        """
        Check that prioritized transform stages are valid transformation stage names.

        :param processes: List of Processes
        :param model_params: Model parameters (Dictionary)
        :return: Tuple (has errors (bool), list of errors (str))
        """
        errors = []
        prioritized_transform_stages = model_params[ParameterName.PrioritizeTransformationStages]
        found_transformation_stages = set()
        for process in processes:
            found_transformation_stages.add(process.transformation_stage)

        for transformation_stage in prioritized_transform_stages:
            if transformation_stage not in found_transformation_stages:
                s = "Transformation stage '{}' is not used in any Processes".format(transformation_stage)
                errors.append(s)

        return not errors, errors

    def _check_prioritized_locations(self, processes: List[Process], model_params: Dict[str, Any])\
            -> Tuple[bool, List[str]]:
        """
        Check that prioritized locations are valid location names.

        :param processes: List of Processes
        :param model_params: Model parameters (Dictionary)
        :return: Tuple (has errors (bool), list of errors (str))
        """
        errors = []
        prioritized_locations = model_params[ParameterName.PrioritizeLocations]
        found_locations = set()
        for process in processes:
            found_locations.add(process.location)

        for location in prioritized_locations:
            if location not in prioritized_locations:
                s = "Location '{}' is not used in any Processes".format(location)
                errors.append(s)

        return not errors, errors


    def check_for_errors(self):
        """
        Check for additional errors after building the scenarios.
        Raises Exception if found errors.

        :raises Exception: Exception
        """
        ok, messages_processes = self.check_processes_integrity()
        if not ok:
            raise Exception(messages_processes)

        ok, messages_flows = self.check_flows_integrity()
        if not ok:
            raise Exception(messages_flows)

    def get_processes(self) -> List[Process]:
        return self._processes

    def get_flows(self) -> List[Flow]:
        return self._flows

    def get_stocks(self) -> List[Stock]:
        return self._stocks

    def get_start_year(self) -> int:
        return self._year_start

    def get_end_year(self) -> int:
        return self._year_end

    def get_year_to_flow_id_to_flow_mapping(self):
        return self._year_to_flow_id_to_flow

    def _detect_year_range(self, flows: List[Flow]) -> (int, int):
        """
        Detect year range for flow data.
        Return tuple (start year, end year)

        :param flows: List of Flows
        :return: Tuple (start year, end year)
        """
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

    def _check_if_data_is_outside_year_range(self, flows: List[Flow]) -> Tuple[bool, List[str]]:
        """
        Check if data is outside year range.

        :param flows: List of Flows
        :return: Tuple (has errors (bool), list of errors (list[str])
        """
        errors = []

        # Get year range defined in settings (= simulation years)
        years = self._get_year_range()
        year_min = min(years)
        year_max = max(years)

        unique_flow_years = set()
        for flow in flows:
            unique_flow_years.add(flow.year)

        # Min and max year found in data
        flow_year_min = min(unique_flow_years)
        flow_year_max = max(unique_flow_years)

        # Flows defined later that end_year
        if flow_year_min > year_max:
            error = "All flows are defined after the end year ({}) defined in settings file".format(year_max)
            errors.append(error)

        # Flows defined before the start_year
        if flow_year_max < year_min:
            error = "All flows are defined before the start year ({}) defined in the settings file".format(year_min)
            errors.append(error)

        # First flow year is defined afther the start_year
        if flow_year_min > year_min:
            error = "Start year ({}) is set before first flow data year ({}) in settings file".format(
                year_min, flow_year_min)
            errors.append(error)

        return not errors, errors

    def _check_process_ids_for_inflow_visualization(self, process_ids: List[str],
                                                    unique_processes: Dict[str, Process]) -> Tuple[bool, List[str]]:
        """
        Check that all Process IDs that are selected for inflow visualization are valid

        :param process_ids: List of Process IDs
        :param unique_processes: Dictionary (Process ID, Process)
        :return: Tuple (has errors, list of errors)
        """
        errors = []
        for process_id in process_ids:
            if process_id not in unique_processes.keys():
                errors.append("Process inflows to visualize '{}' is not valid process ID!".format(process_id))

        return not errors, errors


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
        df = pd.DataFrame(index=years, columns=list(unique_flow_ids.keys()))
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

    def _check_root_processes(self, df_year_to_process_flows: pd.DataFrame):
        """
        Check root processes.
        Root processes do not have inflows and have only absolute outflows.

        :param df_year_to_process_flows: DataFrame
        :return: Tuple (has errors (bool), list of errors (list[str]))
        """

        errors = []
        for year in df_year_to_process_flows.index:
            for process_id in df_year_to_process_flows.columns:
                entry: ProcessEntry = df_year_to_process_flows.at[year, process_id]

                # Skip NA entries
                if pd.isna(entry):
                    continue

                process = entry.process
                inflows = entry.inflows
                outflows = entry.outflows

                if len(inflows) > 0:
                    continue

                abs_outflows = []
                rel_outflows = []
                for flow in outflows:
                    if flow.is_unit_absolute_value:
                        abs_outflows.append(flow)
                    else:
                        rel_outflows.append(flow)

                num_abs_outflows = len(abs_outflows)
                num_rel_outflows = len(rel_outflows)
                no_outflows = (num_abs_outflows == 0) and (num_rel_outflows == 0)
                if no_outflows:
                    # Error: Root process does not have any outflows
                    msg = "Root process '{}' has no outflows".format(process)
                    errors.append(msg)

                if num_rel_outflows > 0:
                    # Error: root process can have only absolute outflows
                    msg = "Root process '{}' has relative outflows".format(process)
                    errors.append(msg)

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

                        errors.append("Check following outflows:")
                        for flow in outflows:
                            s = "- flow '{}' in row {}".format(flow.id, flow.row_number)
                            errors.append(s)

                        s = ""
                        errors.append(s)

        return not errors, errors

    def _check_relative_flow_errors(self, df_year_to_flows: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Check that relative flows do not go over 100%.

        :param df_year_to_flows: DataFrame
        :return: Tuple (bool, list of errors)
        """
        errors = []
        for flow_id in df_year_to_flows.columns:
            flow_data = df_year_to_flows[flow_id]
            for year, flow in flow_data.items():
                # NOTE: NEW, allow making "holes" to DataFrame
                if not isinstance(flow, Flow):
                    continue

                if flow.is_unit_absolute_value:
                    continue

                if flow.value < 0.0:
                    s = "Flow {} has value less than 0% for year {} in row {} in sheet '{}'".format(
                        flow.id, flow.year, flow.row_number, self._dataprovider.sheet_name_flows
                    )
                    errors.append(s)
                    return not errors, errors

                if flow.value > 100.0:
                    s = "Flow {} has value over 100% for year {} in row {} in sheet '{}'".format(
                        flow.id, flow.year, flow.row_number, self._dataprovider.sheet_name_flows
                    )
                    errors.append(s)
                    return not errors, errors

        # Check if total relative outflows from process are >100%
        for year in df_year_to_flows.index:
            process_id_to_rel_outflows = {}
            for flow_id in df_year_to_flows.columns:
                flow = df_year_to_flows.at[year, flow_id]
                # NOTE: NEW, allow making "holes" to DataFrame
                if not isinstance(flow, Flow):
                    continue

                if flow.is_unit_absolute_value:
                    continue

                # Gather relative outflows to source process ID
                outflows = process_id_to_rel_outflows.get(flow.source_process_id, [])
                outflows.append(flow)
                process_id_to_rel_outflows[flow.source_process_id] = outflows

            # Check if total outflows of the process are > 100%
            for process_id, outflows in process_id_to_rel_outflows.items():
                total_share = np.sum([flow.value for flow in outflows])
                if total_share > 100.0:
                    s = "Process {} has total relative outflows over 100%".format(process_id)
                    s += " (total={:.3f}%) for year {} in sheet '{}'".format(
                        total_share, year, self._dataprovider.sheet_name_flows)
                    s.format(process_id)
                    errors.append(s)

                    s = "Check following flows:"
                    errors.append(s)
                    for flow in outflows:
                        s = "\t{} (row {})".format(flow, flow.row_number)
                        errors.append(s)
                    errors.append("")

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
        Fill years missing Flow data with the previous valid Flow data.
        If fill_absolute_flows is set to True then process Flows with absolute values.
        If fill_relative_values is set to True then process Flows with relative values.
        If both fill_absolute_flows and fill_relative_flows are set to False then returns copy
        of the original.

        :param df_year_flows: DataFrame
        :param fill_missing_absolute_flows: If True then process Flows with absolute values
        :param fill_missing_relative_flows: If True then process Flows with relative values
        :return: DataFrame
        """
        # No filling, convert nan in DataFrame to None
        if (not fill_missing_absolute_flows) and (not fill_missing_relative_flows):
            # TODO: Convert nan in DataFrame to None
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

        df = pd.DataFrame(index=df_year_flows.index, columns=list(unique_process_ids.keys()), dtype="object")
        for year in df_year_flows.index:
            for process_id, process in unique_process_ids.items():
                df.at[year, process.id] = {"process": copy.deepcopy(process), "flows": {"in": [], "out": []}}

        # Add process inflows and outflows for every year
        for year in df_year_flows.index:
            for flow_id in df_year_flows.columns:
                flow = df_year_flows.at[year, flow_id]

                # No data defined for process ID at this year
                if pd.isnull(flow):
                    continue

                df.at[year, flow.source_process_id]["flows"]["out"].append(flow)
                df.at[year, flow.target_process_id]["flows"]["in"].append(flow)

        return df

    def _create_process_to_flows_entries(self,
                                         unique_process_ids: dict[str, Process],
                                         df_year_flows: pd.DataFrame) -> pd.DataFrame:
        """
        Create Process to Flows (inflows and outflows) entries.
        Entries are ProcessEntry-objects inside DataFrame.

        :param unique_process_ids: Dictionary of unique [Process ID -> Process]
        :param df_year_flows: DataFrame, year to flows
        :return: DataFrame (index as year, column as Process ID, cell as ProcessEntry)
        """

        df = pd.DataFrame(index=df_year_flows.index, columns=list(unique_process_ids.keys()), dtype="object")

        for year in df_year_flows.index:
            for process_id, process in unique_process_ids.items():
                df.at[year, process_id] = ProcessEntry(process)

        # Add Process inflows and outflows for every year
        for year in df_year_flows.index:
            for flow_id in df_year_flows.columns:
                flow = df_year_flows.at[year, flow_id]
                if pd.isnull(flow):
                    continue

                entry_source_process = df.at[year, flow.source_process_id]
                entry_source_process.add_outflow(flow)

                entry_target_process = df.at[year, flow.target_process_id]
                entry_target_process.add_inflow(flow)

        return df

    @staticmethod
    def _merge_relative_outflows(df_year_to_process_flows: pd.DataFrame,
                                 df_year_to_flows: pd.DataFrame,
                                 min_threshold: float = 99.9) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Check if relative outflows needs merging. Flow merging means that
        if Process has only one 100% relative flow then from that year onward
        that is going to be the only outflow unless new Flows are introduced
        in later years. Other relative outflows are removed from the Process for that
        year and the rest of the years.

        :param min_threshold: Flow with share greater than this are considered as 100%
        :param df_year_to_process_flows: pd.DataFrame (index is year, column is Process ID)
        :param df_year_to_flows: pd.DataFrame (index is year, column is Flow ID)
        :return: pd.DataFrame
        """
        assert min_threshold > 0.0, "min_threshold should be > 0.0"
        assert min_threshold <= 100.0, "min_threshold should be <= 100.0"

        df_process = df_year_to_process_flows.copy()
        df_flows = df_year_to_flows.copy()
        for process_id in df_process.columns:
            for year in df_process.index:
                entry: ProcessEntry = df_process.at[year, process_id]
                inflows = entry.inflows
                outflows = entry.outflows

                # Skip root processes
                if not inflows:
                    continue

                # Get only Processes that have only 1 relative outflow
                rel_outflows = [flow for flow in outflows if not flow.is_unit_absolute_value]
                full_relative_outflows = [flow for flow in rel_outflows if flow.value > min_threshold]
                if not full_relative_outflows:
                    continue

                assert len(full_relative_outflows) == 1, "There should be only 1 full relative outflow"

                # Remove all other flows except the Flow that had 100% share from both
                # source process outflows and in target process inflows.
                flows_to_remove = list(set(rel_outflows) - set(full_relative_outflows))

                for flow in flows_to_remove:
                    # Remove the source process outflow for this year
                    source_entry: ProcessEntry = df_process.at[year, flow.source_process_id]
                    source_entry.remove_outflow(flow.id)

                    # Remove the target process inflow for this year
                    target_entry: ProcessEntry = df_process.at[year, flow.target_process_id]
                    target_entry.remove_inflow(flow.id)

                    # Remove the flow also from df_flows for this year
                    df_flows.at[year, flow.id] = pd.NA

        return df_process, df_flows

    def _remove_isolated_processes(self, df_year_to_process_flows: pd.DataFrame) -> pd.DataFrame:
        df = df_year_to_process_flows.copy()

        # Remove isolated processes from DataFrame
        for year in df.index:
            for process_id in df.columns:
                entry = df.at[year, process_id]
                if (not entry.inflows) and (not entry.outflows):
                    df.at[year, process_id] = pd.NA

        return df

    def _check_process_stock_parameters(self, processes: List[Process]) -> Tuple[bool, list[str]]:
        """
        Check if Process has valid definition for stock distribution type
        :param processes: List of Processes
        :return: True if no errors, False otherwise
        """
        errors = []
        print("Checking stock distribution types...")
        allowed_distribution_types = set([name.value for name in StockDistributionType])

        for process in processes:
            if process.stock_distribution_type not in allowed_distribution_types:
                msg = "Process {} has invalid stock distribution type '{}' in row {} in sheet '{}'".format(
                    process.id, process.stock_distribution_type,
                    process.row_number, self._dataprovider.sheet_name_processes)
                errors.append(msg)

        if errors:
            # Add information about the valid stock distribution types
            errors.append("")
            errors.append("\tValid stock distribution types are:")
            for distribution_type in allowed_distribution_types:
                errors.append("\t{}".format(distribution_type))
            errors.append("")

            return not errors, errors

        # Check stock lifetimes
        errors = []
        for process in processes:
            if process.stock_lifetime < 0:
                msg = "Process {} has negative stock lifetime ({}) in row {} in sheet '{}'".format(
                    process.id, process.stock_lifetime, process.row_number, self._dataprovider.sheet_name_processes)
                errors.append(msg)

            if errors:
                return not errors, errors

        # Check if Process has valid parameters for stock distribution parameters
        # Expected: float or dictionary with valid keys (stddev, shape, scale)
        errors = []
        print("Checking stock distribution parameters...")
        for process in processes:
            if process.stock_distribution_params is None:
                msg = "Process {} has invalid stock distribution parameter '{}' in row {} in sheet '{}'".format(
                    process.id, process.stock_distribution_params,
                    process.row_number, self._dataprovider.sheet_name_processes)
                errors.append(msg)
                continue

            # Check that all required stock distribution parameters are present and have valid type
            found_params = process.stock_distribution_params
            required_params = RequiredStockDistributionParameters[process.stock_distribution_type]
            is_float = type(process.stock_distribution_params) is float
            num_required_params = len(required_params)
            if (not num_required_params) and (not is_float):
                s = "Stock distribution parameter must be float for distribution type '{}' for process '{}' in row {}".format(
                    process.stock_distribution_type, process.id, process.row_number)
                errors.append(s)
                continue

            for required_param_name, required_param_value_type in required_params.items():
                # Check if only float was provided
                if num_required_params and is_float:
                    s = "Stock distribution parameters was number, following parameters are required "
                    s += "for distribution type '{}' for process '{}' in row {}".format(
                        process.stock_distribution_type, process.id, process.row_number)
                    errors.append(s)
                    for p in required_params.keys():
                        errors.append("\t{}".format(p))

                    continue

                # Check if required parameter name is found in stock distribution parameters
                if required_param_name not in found_params:
                    s = "Stock distribution type '{}' needs following parameters for process '{}' in row {}:".format(
                        process.stock_distribution_type, process.id, process.row_number)
                    errors.append(s)
                    for p in required_params:
                        errors.append("\t{}".format(p))
                    continue

                # Check if parameter has proper value type
                for found_param_name, found_param_value in found_params.items():
                    allowed_parameter_values = AllowedStockDistributionParameterValues[found_param_name]

                    # If allowed_parameter_values is empty then skip to next, nothing to check against
                    if not allowed_parameter_values:
                        continue

                    if found_param_value not in allowed_parameter_values:
                        s = "Stock distribution parameter '{}' needs following parameters for process '{}' in row {}:".format(
                            process.stock_distribution_type, process.id, process.row_number)
                        errors.append(s)
                        for p in allowed_parameter_values:
                            errors.append("\t{}".format(p))

                if errors:
                    return not errors, errors

                pass

        return not errors, errors

    def _check_stocks_in_isolated_processes(self, stocks: List[Stock], unique_process_ids: Dict[str, Process]) -> Tuple[bool, List[str]]:
        # Check for processes with stocks that are not used unique_process_ids
        """
        Check for stock in isolated Processes.

        :param stocks: All stocks (list of Stocks)
        :param unique_process_ids: Set of unique Process IDs
        :return: Tuple (has errors (bool), list of errors (List[str])
        """
        errors = []
        for stock in stocks:
            stock_id = stock.id
            if stock_id not in unique_process_ids:
                s = "ERROR: Stock found in isolated Process {} in row {}".format(stock_id, stock.row_number)
                errors.append(s)

        return not errors, errors

    def _check_fill_method_requirements(self, fill_method: ParameterFillMethod, df_year_to_flows: pd.DataFrame)\
            ->Tuple[bool, List[str]]:
        """
        Check if fill method requirements are met for flows.
        Fill method Zeros: No checks needed.
        Fill method Previous: At least Flow for the starting year must be defined in the data.
        Fill method Next: At least Flow for the last year must be defined in the data.
        Fill method Interpolate: At least start AND last year have Flows defined in the data.

        :param fill_method: Fill method (ParameterFillMethod)
        :param df_year_to_flows: DataFrame
        :return: Tuple (has errors (bool), list of errors (list[str]))
        """
        errors = []
        if fill_method is ParameterFillMethod.Zeros:
            # Flow must be defined at least for one year
            # This works always, just fills years without Flow data with Flows
            return not errors, errors

        if fill_method is ParameterFillMethod.Previous:
            pass

        if fill_method is ParameterFillMethod.Next:
            pass

        if fill_method is ParameterFillMethod.Interpolate:
            pass

        return not errors, errors

    def _check_process_has_no_inflows_and_only_relative_outflows(self, df_year_to_process_flows: pd.DataFrame)\
            -> Tuple[bool, List[str]]:
        """
        Check for Processes that have no inflows and have only relative outflows.
        This is error in data.

        :param df_year_to_process_flows: DataFrame (index: year, column: Process name, cell: ProcessEntry)
        :return: True if no errors, False otherwise
        """
        errors = []
        print("Checking for processes that have no inflows and only relative outflows...")
        year_to_errors = {}
        for year in df_year_to_process_flows.index:
            for process_id in df_year_to_process_flows.columns:
                entry: ProcessEntry = df_year_to_process_flows.at[year, process_id]

                # Skip removed entries
                if pd.isna(entry):
                    continue

                process = entry.process
                flows_in = entry.inflows
                flows_out = entry.outflows

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

            errors.append(msg)
            for year, year_errors in year_to_errors.items():
                errors.append("Year {} ({} errors):".format(year, len(year_errors)))
                for error in year_errors:
                    errors.append("\t{}".format(error))
                errors.append("")

        return not has_errors, errors

    def _check_scenario_definitions(self, df_year_to_process_flows: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Check scenario definitions.

        :param df_year_to_process_flows: pd.DataFrame
        :return: Tuple (has errors: bool, list of errors)
        """
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
                    continue

                # Check rule for last year
                if end_year > last_valid_year:
                    s = "" + error_message_prefix
                    s += "Source Process ID '{}' end year ({}) is after last year of simulation ({})".format(
                        source_process_id, end_year, last_valid_year)
                    errors.append(s)
                    continue

                # Check if source Process ID exists for the defined year range
                for year in years:
                    year_data = df_year_to_process_flows[df_year_to_process_flows.index == year]
                    if source_process_id not in year_data.columns:
                        s = "" + error_message_prefix
                        s += "Source Process ID '{}' not defined for the year {}".format(source_process_id, year)
                        errors.append(s)
                        continue

                    # Check if target Process ID exists for the defined year range
                    if target_process_id not in year_data.columns:
                        s = "" + error_message_prefix
                        s += "Target Process ID '{}' not defined for the year {}".format(source_process_id, year)
                        errors.append(s)
                        continue

                    entry: ProcessEntry = year_data.at[year, source_process_id]
                    flows_out = entry.outflows
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
                    source_to_target_id = "{} {}".format(flow_modifier.source_process_id, flow_modifier.target_process_id)
                    start_year_processes = df_year_to_process_flows.loc[flow_modifier.start_year]

                    # Get source-to-target flow mappings at start year
                    source_process_entry: ProcessEntry = start_year_processes[source_process_id]
                    source_process_outflows = source_process_entry.outflows
                    flow_id_to_flow = {flow.id: flow for flow in source_process_outflows}
                    if source_to_target_id not in flow_id_to_flow:
                        s = "" + error_message_prefix
                        s += "Source Process ID '{}' does not have outflow to target Process ID '{}'".format(
                            source_process_id, target_process_id)
                        errors.append(s)
                        continue

                    source_to_target_flow = flow_id_to_flow[source_to_target_id]
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
                else:
                    # Change in delta, change flow value either by value or by factor
                    # - If target flow is absolute: change_type can be either ChangeType.Value or ChangeType.Proportional
                    # - If target flow is relative: change_type can be only ChangeType.Proportional
                    #
                    # Absolute flow:
                    # Change in value (delta): 50 ABS, change in delta = 50 ABS, result = 50 ABS + 50 ABS = 100 ABS
                    # Target value: 50 ABS, target value = 75, result = 50 ABS becomes 75 ABS during the defined time

                    # Relative flow:
                    # Relative flow can have change in value
                    # Absolute change in this case means that e.g. original value = 100, "Change in value" is 50" then
                    # the resulting value is 150.
                    #
                    # Relative flow:
                    # Absolute change here means that e.g. original value = 100 %
                    pass

        return not errors, errors

    def _check_color_definitions(self, colors: List[Color]) -> Tuple[bool, List[str]]:
        """
        Check if all color definitions are valid:
        - Color definition must have name
        - Color definition must have valid value (hex string starting with character '#')

        :param colors: List of Colors
        :return: Tuple (has errors: bool, list of errors)
        """

        # Get list of unique transformation stages
        transformation_stages = set()
        for process in self._processes:
            transformation_stages.add(process.transformation_stage)

        errors = []
        for color in colors:
            row_errors = []

            # Has valid name?
            if not color.name:
                s = "Color definition does not have name (row {})".format(color.row_number)
                row_errors.append(s)

            # Has valid value?
            # - hex string prefixed with character '#'
            # - string length is 7
            if not color.value.startswith('#'):
                s = "Color definition does not start with character '#' (row {})".format(color.row_number)
                row_errors.append(s)

            if len(color.value) != 7:
                s = "Color definition value length must be 7, example: #123456 (row {})".format(color.row_number)
                row_errors.append(s)

            # Check if color value can be converted to hexadecimal value
            int_value = -1
            try:
                int_value = int(color.value[1:], 16)
            except ValueError:
                s = "Color definition value '{}' is not hexadecimal string (row {})".format(color.value,
                                                                                            color.row_number)
                row_errors.append(s)

            # Check that transformation stage with the name color.name exists
            if color.name:
                if color.name not in transformation_stages:
                    s = "INFO: Color definition name '{}' is not transformation stage name (row {})".format(
                        color.name, color.row_number)
                    print(s)

            if row_errors:
                msg = "errors" if len(row_errors) > 1 else "error"
                row_errors.insert(0, "{} {} in row {}:".format(len(row_errors), msg, color.row_number))

                for error in row_errors:
                    errors.append(error)
                errors.append("")

        return not errors, errors

    def _check_flow_indicators(self, df_year_to_flows: pd.DataFrame, default_conversion_factor: float = 1.0)\
            -> Tuple[bool, List[str]]:
        """
        Check and set default value to every flow that is missing value.

        :param df_year_to_flows:
        :return: Tuple (has errors (bool), list of errors (str))
        """
        errors = []
        for year in df_year_to_flows.index:
            for flow_id in df_year_to_flows:
                flow = df_year_to_flows.at[year, flow_id]
                # NOTE: NEW, allow making "holes" to DataFrame
                if not isinstance(flow, Flow):
                    continue

                for name, indicator in flow.indicator_name_to_indicator.items():
                    if indicator.conversion_factor is None:
                        s = "Flow '{}' has no conversion factor defined for year {}, using default={} (row {})"\
                            .format(flow_id, year, default_conversion_factor, flow.row_number)
                        print("INFO: {}".format(s))
                        indicator.conversion_factor = default_conversion_factor

                    try:
                        # Try casting value to float and if exception happens then
                        # value was not float
                        conversion_factor = float(indicator.conversion_factor)
                        indicator.conversion_factor = conversion_factor
                    except ValueError as ex:
                        s = "Flow '{}' has invalid conversion factor defined for year {} (row {})".format(
                            flow_id, year, flow.row_number)
                        errors.append(s)

        return not errors, errors