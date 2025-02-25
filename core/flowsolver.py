import copy
from typing import List, Dict, Tuple, Union
import numpy as np
import pandas as pd
import tqdm as tqdm
from pandas import DataFrame

from core.datastructures import Process, Flow, Stock, ScenarioData, Scenario, Indicator
from core.parameters import ParameterName, StockDistributionType, StockDistributionParameter
from core.types import FunctionType
from lib.odym.modules.dynamic_stock_model import DynamicStockModel


# Solves flows to absolute values
class FlowSolver(object):
    """
    Solves flows to absolute values, evaluates Process in- and outflow values,
    and handles dynamic stocks.
    """
    _virtual_process_id_prefix = "VP_"
    _virtual_flow_id_prefix = "VF_"
    _max_iterations = 100000
    _virtual_process_transformation_stage = "Virtual"

    def __init__(self, scenario: Scenario = None):
        self._scenario = scenario

        # Prioritized transformation stages
        self._model_params = self._scenario.model_params
        self._prioritized_locations = self._model_params[ParameterName.PrioritizeLocations]
        self._prioritized_transformation_stages = self._model_params[ParameterName.PrioritizeTransformationStages]

        # Time
        self._year_start = self._scenario.scenario_data.start_year
        self._year_end = self._scenario.scenario_data.end_year
        self._years = self._scenario.scenario_data.years
        self._year_current = self._year_start
        self._year_prev = self._year_current

        # Year to Process/Flow/Flow IDs mappings
        self._year_to_process_id_to_process = scenario.scenario_data.year_to_process_id_to_process
        self._year_to_process_id_to_flow_ids = scenario.scenario_data.year_to_process_id_to_flow_ids
        self._year_to_flow_id_to_flow = scenario.scenario_data.year_to_flow_id_to_flow

        # Stocks
        self._all_stocks = self._scenario.scenario_data.stocks
        self._process_id_to_stock = self._scenario.scenario_data.process_id_to_stock

        # Unique Process IDs and Flow IDs to Process/Flow
        self._unique_process_id_to_process = self._scenario.scenario_data.unique_process_id_to_process
        self._unique_flow_id_to_flow = self._scenario.scenario_data.unique_flow_id_to_flow

        # Virtual flows
        self._use_virtual_flows = self._scenario.scenario_data.use_virtual_flows
        self._virtual_flows_epsilon = self._scenario.scenario_data.virtual_flows_epsilon

        # Current timestep data
        self._current_process_id_to_process = self._year_to_process_id_to_process[self._year_current]
        self._current_process_id_to_flow_ids = self._year_to_process_id_to_flow_ids[self._year_current]
        self._current_flow_id_to_flow = self._year_to_flow_id_to_flow[self._year_current]

        # Prepare flows for all timesteps
        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            self._prepare_flows_for_timestep(flow_id_to_flow, year)

        # Get and store indicator names from scenario.scenario_data
        self._indicator_name_to_indicator = scenario.scenario_data.indicator_name_to_indicator
        self._indicators = {name: indicator for name, indicator in self._indicator_name_to_indicator.items()}

        # Baseline indicator name (e.g. Solid wood equivalent) and unit name (e.g. 'Mm3')
        self._baseline_value_name = self._scenario.scenario_data.baseline_value_name
        self._baseline_unit_name = self._scenario.scenario_data.baseline_unit_name

        # Stock ID -> Baseline value DSM
        self._stock_id_to_baseline_dsm = {}

        # Stock ID -> Indicator name -> DSM
        self._stock_id_to_indicator_name_to_dsm = {}

    def get_all_stocks(self) -> List[Stock]:
        """
        Get list of all Stocks.

        :return: List of all Stocks
        """
        return self._all_stocks

    def get_unique_processes(self) -> Dict[str, Process]:
        """
        Get dictionary of all unique Process ID to Process.

        :return: Dictionary (Process ID (str) -> Process)
        """
        return self._unique_process_id_to_process

    def get_unique_flows(self) -> Dict[str, Flow]:
        """
        Get dictionary of all unique Flow ID to Flow.

        :return: Dictionary (Flow ID (str) -> Flow)
        """
        return self._unique_flow_id_to_flow

    # Utility methods
    def get_processes_as_dataframe(self) -> DataFrame:
        """
        Get Process information as DataFrame for every year:
            - Process ID
            - Total inflows (baseline)
            - Total outflows (baseline)
            - Total inflows (indicator N)
            - Total outflows (indicator N)
            - Total inflows (indicator N+1)
            - Total outflows (indicator N+1)
            - ...

        :return: DataFrame
        """
        col_names = ["Year", "Process ID"]
        col_names += ["Total inflows, {} ({})".format(self._baseline_value_name, self._baseline_unit_name)]
        col_names += ["Total outflows, {} ({})".format(self._baseline_value_name, self._baseline_unit_name)]
        for indicator in self.get_indicator_name_to_indicator().values():
            col_names += ["Total inflows, {} ({})".format(indicator.name, indicator.unit)]
            col_names += ["Total outflows, {} ({})".format(indicator.name, indicator.unit)]

        df = pd.DataFrame({name: [] for name in col_names})
        for year, process_id_to_process in self._year_to_process_id_to_process.items():
            for process_id, process in process_id_to_process.items():
                new_row = [year, process_id]
                new_row += [self.get_process_inflows_total(process_id, year)]
                new_row += [self.get_process_outflows_total(process_id, year)]
                for indicator in self.get_indicator_name_to_indicator().values():
                    new_row += [self._get_process_indicator_inflows_total(process_id, indicator.name, year)]
                    new_row += [self._get_process_indicator_outflows_total(process_id, indicator.name, year)]


                df.loc[len(df.index)] = new_row
        return df

    def get_flows_as_dataframe(self) -> DataFrame:
        """
        Get all Flow information for all years in DataFrame:
            - Flow ID
            - Source Process ID
            - Target Process ID
            - Baseline value (baseline unit)
            - Indicator N value (indicator N unit)
            - Indicator N+1 value (indicator N+1 unit)
            - ...

        :return: DataFrame
        """
        col_names = ["Year", "Flow ID", "Source Process ID", "Target Process ID"]
        col_names += ["{} ({})".format(self._baseline_value_name, self._baseline_unit_name)]
        col_names += ["{} ({})".format(ind.name, ind.unit) for ind in self.get_indicator_name_to_indicator().values()]

        df = pd.DataFrame({name: [] for name in col_names})
        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                if not isinstance(flow, Flow):
                    continue

                new_row = [year, flow_id, flow.source_process_id, flow.target_process_id]
                new_row += [evaluated_value for evaluated_value in flow.get_all_evaluated_values()]
                df.loc[len(df.index)] = new_row
        return df

    def get_evaluated_flow_values_as_dataframe(self) -> DataFrame:
        """
        Get baseline evaluated value for Flows for all years.

        :return: DataFrame
        """

        unique_flows = self.get_unique_flows()
        sorted_flow_ids = sorted([flow.id for flow in unique_flows.values()], key=lambda x: x)
        columns = ["Year"]
        columns += [flow_id for flow_id in sorted_flow_ids]

        df = pd.DataFrame(columns=columns)
        df["Year"] = [year for year in self._years]
        df.set_index(["Year"], inplace=True)
        for year in df.index:
            for flow_id in df.columns:
                flow_value = 0.0
                if self.has_flow(flow_id, year):
                    flow = self.get_flow(flow_id, year)
                    if not isinstance(flow, Flow):
                        pass
                    else:
                        flow_value = flow.evaluated_value
                df.at[year, flow_id] = flow_value
        df.reset_index(inplace=True)
        return df

    def get_process(self, process_id: str, year: int = -1) -> Process:
        """
        Get Process by ID and target year.

        :param process_id: Process ID (str)
        :param year: Target year (int)
        :return: Process (Process)
        """
        if year >= 0:
            return self._year_to_process_id_to_process[year][process_id]

        return self._current_process_id_to_process[process_id]

    def get_flow(self, flow_id: str, year=-1) -> Flow:
        """
        Get Flow by ID and target year.

        :param flow_id: Flow ID (str)
        :param year: Target year (int)
        :return: Flow (Flow)
        """
        if year >= 0:
            return self._year_to_flow_id_to_flow[year][flow_id]

        return self._current_flow_id_to_flow[flow_id]

    def get_stock(self, process_id: str) -> Stock:
        """
        Get stock by ID.
        NOTE: Process and stocks share the same ID

        :param process_id: Target Stock ID / Process ID
        :return: Stock (Stock)
        """
        return self._process_id_to_stock[process_id]

    def get_baseline_dynamic_stocks(self) -> Dict[str, DynamicStockModel]:
        """
        Get dictionary of Stock ID -> baseline DynamicStockModel.

        :return: Dictionary (Stock ID -> baseline DynamicStockModel)
        """

        return self._stock_id_to_baseline_dsm

    def get_indicator_dynamic_stocks(self) -> Dict[str, Dict[str, DynamicStockModel]]:
        """
        Get dictionary of stock ID -> indicator name -> DynamicStockModel

        :return: Dictionary (stock ID (str) -> indicator name -> DynamicStockModel)
        """
        return self._stock_id_to_indicator_name_to_dsm

    def get_indicator_names(self) -> List[str]:
        """
        Get indicator names.

        :return: Indicator names (list of strings)
        """
        return list(self._indicator_name_to_indicator.keys())

    def get_indicator_name_to_indicator(self) -> Dict[str, Indicator]:
        """
        Get Indicator ID to Indicator mappings.

        :return: Dictionary (Indicator ID (str) -> Indicator (Indicator))
        """
        return self._indicator_name_to_indicator

    def get_process_inflows_total(self, process_id: str, year: int = -1) -> float:
        """
        Get total inflows (baseline) for Process ID.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: Sum of all inflows' evaluated value (baseline)
        """
        total = 0.0
        inflows = self._get_process_inflows(process_id, year)
        for flow in inflows:
            total += flow.evaluated_value
        return total

    def get_process_outflows_total(self, process_id: str, year: str = -1) -> float:
        """
        Get total outflows (baseline) for Process ID.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: Sum of all outflows' evaluated value (baseline)
        """
        total = 0.0
        outflows = self._get_process_outflows(process_id, year)
        for flow in outflows:
            total += flow.evaluated_value
        return total

    def solve_timesteps(self) -> None:
        """
        Solves all timesteps.
        """
        bar = tqdm.tqdm(initial=0)
        self._create_dynamic_stocks()
        self._apply_flow_modifiers()
        for current_year in self._years:
            bar.set_description("Solving flows for year {}/{}".format(current_year, self._year_end))
            self._solve_timestep()
            self._advance_timestep()
            bar.update()
        bar.close()

    def get_year_to_process_to_flows(self) -> Dict[int, Dict[Process, Dict[str, Flow]]]:
        """
        Get year to Process to Flow entry mappings

        :return: Year to Process to Flow entry mappings
        """
        year_to_process_to_flows = {}
        for year, process_id_to_process in self._year_to_process_id_to_process.items():
            year_to_process_to_flows[year] = {}
            for process_id, process in process_id_to_process.items():
                flow_ids = self._year_to_process_id_to_flow_ids[year][process_id]

                flows_in = []
                for flow_id in flow_ids["in"]:
                    flows_in.append(self._year_to_flow_id_to_flow[year][flow_id])

                flows_out = []
                for flow_id in flow_ids["out"]:
                    flows_out.append(self._year_to_flow_id_to_flow[year][flow_id])

                year_to_process_to_flows[year][process] = {"in": flows_in, "out": flows_out}

        return year_to_process_to_flows

    def get_process_flows(self, process_id: str, year: int = -1) -> Dict[str, List[Flow]]:
        """
        Get target Process ID flows for target year (both inflows and outflows).

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: Dictionary (keys: "Inflows", "Outflows"). Key points to List of Flows
        """
        process_inflows = self._get_process_inflows(process_id, year)
        process_outflows = self._get_process_outflows(process_id, year)
        return {"Inflows": process_inflows, "Outflows": process_outflows}

    def get_process_inflows(self, process_id: str, year: int = -1) -> List[Flow]:
        """
        Get target Process ID inflows.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: List of inflows
        """
        return self._get_process_inflows(process_id, year)

    def get_process_outflows(self, process_id: str, year: int = -1) -> List[Flow]:
        """
        Get target Process ID outflows.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: List of outflows
        """
        return self._get_process_outflows(process_id, year)

    def is_root_process(self, process_id: str, year: int = -1) -> bool:
        """
        Check if Process has no inflows at target year.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: True if Process has no inflows, False otherwise
        """
        return len(self._get_process_inflows(process_id, year)) == 0

    def is_leaf_process(self, process_id: str, year: int = -1) -> bool:
        """
        Check if Process ID has no outflows at target year.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: True if Process has no outflows, False otherwise
        """
        return len(self._get_process_outflows(process_id, year)) == 0

    def is_all_process_inflows_evaluated(self, process_id: str, year: int = -1) -> bool:
        """
        Check if all inflows to target Process ID are evaluated at the target year.

        :param process_id: Target Process ID (str)
        :param year: Target year (int)
        :return: True if all inflows are evaluated, False otherwise.
        """
        inflows = self._get_process_inflows(process_id, year)
        return all([flow.is_evaluated for flow in inflows])

    def has_flow(self, flow_id: str, year: int = -1) -> bool:
        """
        Check if Flow with ID exists at target year.
        If year is not provided then internally uses the current timestep year inside FlowSolver.

        :param flow_id: Flow ID (str)
        :param year: Target year (int)
        :return: True if Flow with ID exists for year, False otherwise.
        """

        if year >= 0:
            return flow_id in self._year_to_flow_id_to_flow[year]

        return flow_id in self._current_flow_id_to_flow

    def has_process(self, process_id: str, year: int = -1) -> bool:
        """
        Check if Process ID exists at target year.

        :param process_id: Process ID
        :param year: Selected year. If not defined then uses the current year inside FlowSolver.
        :return: True if Process with ID exists for year, False otherwise.
        """
        if year >= 0:
            return process_id in self._year_to_process_id_to_process[year]

        return process_id in self._current_process_id_to_process

    def accumulate_dynamic_stock_inflows(self, dsm: DynamicStockModel, total_inflows: float, year: int = -1) -> None:
        """
        Update and accumulate inflows to DynamicStockModel.

        :param dsm: Target DynamicStockModel
        :param total_inflows: Total inflows for the stock (float)
        :param year: Target year (int)
        :return: None
        """

        year_index = self._years.index(year)

        # Resetting some DynamicStockModel properties are needed to make
        # timestep stock accumulation and other calculations work
        dsm.i[year_index] = total_inflows

        # Recalculate stock by cohort
        dsm.s_c = None
        dsm.compute_s_c_inflow_driven()

        # Recalculate outflow by cohort
        dsm.o_c = None
        dsm.compute_o_c_from_s_c()

        # Recalculate stock total
        dsm.s = None
        dsm.compute_stock_total()

        # Get stock total
        dsm.compute_stock_change()

        # Recalculate stock outflow
        dsm.o = None
        dsm.compute_outflow_total()

    def _get_year_to_process_id_to_process(self) -> Dict[int, Dict[str, Process]]:
        return self._year_to_process_id_to_process

    def _get_current_year_flow_id_to_flow(self) -> Dict[str, Flow]:
        """
        Get current year flow ID to Flow mappings.

        :return: Dictionary (Flow ID -> Flow)
        """
        return self._year_to_flow_id_to_flow[self._year_current]

    def _get_current_year_process_id_to_process(self) -> Dict[str, Process]:
        """
        Get current year process ID to Process mappings.

        :return: Dictionary (Process ID -> Process)
        """
        return self._year_to_process_id_to_process[self._year_current]

    def _get_current_year_process_id_to_to_flow_ids(self) -> Dict[str, List[str]]:
        """
        Get current year Process ID to Flow ID mappings.

        :return: Dictionary (Process ID -> List of Flow IDs)
        """
        return self._year_to_process_id_to_flow_ids[self._year_to_process_id_to_process]



    # TODO: NEW
    def _get_year_to_flow_id_to_flow(self) -> Dict[int, Dict[str, Flow]]:
        return self._year_to_flow_id_to_flow

    def _get_process_inflow_ids(self, process_id: str, year: int = -1) -> List[str]:
        result = []
        if year >= 0:
            result = self._year_to_process_id_to_flow_ids[year][process_id]["in"]
        else:
            result = self._current_process_id_to_flow_ids[process_id]["in"]

        # If year -> process ID does not exist, return empty array
        if not result:
            result = []

        return result

    def _get_process_outflow_ids(self, process_id: str, year: int = -1) -> List[str]:
        result = []
        if year >= 0:
            result = self._year_to_process_id_to_flow_ids[year][process_id]["out"]
        else:
            result = self._current_process_id_to_flow_ids[process_id]["out"]

        if not result:
            result = []
        return result

    def _get_process_inflows(self, process_id: str, year: int = -1) -> List[Flow]:
        """
        Get list of all inflows for Process ID in target year.

        :param process_id: Target Process ID
        :param year: Target year
        :return: List of Flows
        """
        # Get list of process inflows for current year
        flows = []
        inflow_ids = self._get_process_inflow_ids(process_id, year)
        for flow_id in inflow_ids:
            flows.append(self.get_flow(flow_id, year))
        return flows

    # Get list of outflows (DataFlows)
    def _get_process_outflows(self, process_id: str, year: int = -1) -> List[Flow]:
        """
        Get list of Process outflows for the selected year.

        :param process_id: Process ID
        :param year: Selected year
        :return: List of Flows
        """
        # Get list of outflows for current year
        flows = []
        outflow_ids = self._get_process_outflow_ids(process_id, year)
        for flow_id in outflow_ids:
            flow = self.get_flow(flow_id, year)
            flows.append(flow)
        return flows

    def _get_process_outflows_abs(self, process_id: str, year: int = -1) -> List[Flow]:
        """
        Get list of absolute outflows from Process for the selected year.

        :param process_id: Process ID
        :param year: Selected year
        :return: List of absolute outflows (Flow)
        """
        outflows_abs = []
        flows = self._get_process_outflows(process_id, year)
        for flow in flows:
            if flow.is_unit_absolute_value:
                outflows_abs.append(flow)
        return outflows_abs


    def _get_process_outflows_rel(self, process_id: str, year: int = -1) -> List[Flow]:
        """
        Get list of relative outflows from Process for the selected year.

        :param process_id: Process ID
        :param year: Selected year
        :return: List of relative outflows (Flow)
        """

        outflows_rel = []
        flows = self._get_process_outflows(process_id, year)
        for flow in flows:
            if not flow.is_unit_absolute_value:
                outflows_rel.append(flow)
        return outflows_rel

    def _get_process_indicator_inflows_total(self, process_id: str, indicator_name: str, year: int = -1) -> float:
        """
        Get total evaluated inflows for Indicator for Process ID at target year.

        :param process_id: Target Process ID
        :param indicator_name: Target Indicator name
        :param year: Target year
        :return: Total inflows of indicator name (float)
        """
        total = 0.0
        flows = self._get_process_inflows(process_id, year)
        for flow in flows:
            total += flow.get_evaluated_value_for_indicator(indicator_name)
        return total

    def _get_process_indicator_outflows_total(self, process_id: str, indicator_name: str, year: int = -1) -> float:
        """
        Get total evaluated outflows for Indicator for Process ID at target year.

        :param process_id: Target Process ID
        :param indicator_name: Target Indicator name
        :param year: Target year
        :return: Total outflows of indicator name (float)
        """

        total = 0.0
        flows = self._get_process_outflows(process_id, year)
        for flow in flows:
            total += flow.get_evaluated_value_for_indicator(indicator_name)
        return total

    def _prepare_flows_for_timestep(self, flow_id_to_flow: Dict[str, Flow], year: int):
        """
        Prepare flows for timestep:
        - Mark all absolute flows as evaluated and set flow.value to flow.evaluated_value
        - Normalize all relative flow values from [0%, 100%] range to [0, 1] range

        :param flow_id_to_flow: Dictionary (Flow ID to Flow)
        """
        for flow_id, flow in flow_id_to_flow.items():
            if not isinstance(flow, Flow):
                continue

            if flow.is_unit_absolute_value:
                flow.is_evaluated = True
                flow.evaluated_share = 1.0
                flow.evaluated_value = flow.value
                flow.evaluate_indicator_values_from_baseline_value()
            else:
                # Normalize relative flow value from [0, 100] % range to 0 - 1 range
                flow.is_evaluated = False
                flow.evaluated_share = flow.value / 100.0
                flow.evaluated_value = 0.0

            # Mark flow prioritized
            process = self.get_process(flow.target_process_id, year)
            if process.location in self._prioritized_locations:
                flow.is_prioritized = True

            if process.transformation_stage in self._prioritized_transformation_stages:
                flow.is_prioritized = True

    def _evaluate_process(self, process_id: str, year: int) -> tuple[bool, List]:
        is_evaluated = False
        outflows = self._get_process_outflows(process_id, year)

        # Root process should have only absolute outflow
        if self.is_root_process(process_id, year):
            is_evaluated = True
            return is_evaluated, outflows

        # Distribute outflows (stock or direct) only if all the inflows are already evaluated
        if self.is_all_process_inflows_evaluated(process_id, year):
            # Total baseline inflows
            total_inflows = self.get_process_inflows_total(process_id, year)
            if process_id in self.get_baseline_dynamic_stocks():
                # All inflows are evaluated but process has stocks

                # Flow prioritization:
                # Ignore inflow amount to stock for outflows that are prioritized.
                total_outflows_prioritized = 0.0
                prioritized_outflows = {}
                for flow in outflows:
                    if not flow.is_prioritized:
                        continue

                    if not flow.is_unit_absolute_value:
                        raise Exception("Relative flow as prioritized flow!")

                    flow.is_evaluated = True
                    flow.evaluated_value = flow.value
                    prioritized_outflows[flow.id] = flow
                    total_outflows_prioritized += flow.evaluated_value

                if total_outflows_prioritized > total_inflows:
                    s = "Not enough inflows for prioritized outflows at process '{}' in year {}".format(
                        process_id, year)
                    raise Exception(s)

                # Reduce total inflows to baseline stock by total prioritized outflows
                total_inflows_to_stock = total_inflows - total_outflows_prioritized

                # Update baseline DSM
                baseline_dsm = self.get_baseline_dynamic_stocks()[process_id]
                self.accumulate_dynamic_stock_inflows(baseline_dsm, total_inflows_to_stock, year)

                # Update stock inflows to indicator DSMs
                indicator_dynamic_stocks = self.get_indicator_dynamic_stocks()
                if process_id in indicator_dynamic_stocks:
                    inflows = self.get_process_inflows(process_id)
                    indicator_name_to_dsm = indicator_dynamic_stocks[process_id]
                    for indicator_name, indicator_dsm in indicator_name_to_dsm.items():
                        # Flow evaluated indicator values are based on the actual inflows to process with stock
                        # but with prioritized flows these values do not include the reduction of the prioritized flow.
                        # Fix this by...
                        # - calculating how much each inflow contributes to the original total inflows to get
                        #   correction factor)
                        # - Multiply total_inflows_to_stock by this factor to get correct value how much
                        #   flow indicator contributes to the indicator stock
                        total_indicator_inflows_to_stock = 0.0
                        for flow in inflows:
                            evaluated_indicator_value = flow.get_evaluated_value_for_indicator(indicator_name)
                            correction_factor = evaluated_indicator_value / total_inflows
                            corrected_flow_value = correction_factor * total_inflows_to_stock
                            total_indicator_inflows_to_stock += corrected_flow_value

                        self.accumulate_dynamic_stock_inflows(indicator_dsm, total_indicator_inflows_to_stock, year)

                # Distribute baseline total outflow values
                baseline_stock_outflow = self._get_dynamic_stock_outflow_value(baseline_dsm, year)

                # Check that if process has absolute outflow then outflow value must be
                # less than stock outflow. If absolute outflow is greater than stock outflow
                # then there is user error with the data
                outflows_abs = self._get_process_outflows_abs(process_id, year)
                outflows_rel = self._get_process_outflows_rel(process_id, year)

                # Get all outflows except prioritized outflows
                total_outflows_abs = np.sum([flow.evaluated_value for flow in outflows_abs if not flow.is_prioritized])
                total_outflows_rel = baseline_stock_outflow - total_outflows_abs
                if total_outflows_rel < 0.0:
                    # This is error: Total absolute outflows are greater than stock outflow.
                    # It means that there is not enough flows to distribute between remaining
                    # relative outflows
                    s = "Process {}: stock outflow is less than sum of absolute outflows in year {}!".format(
                        process_id, year)
                    raise Exception(s)

                # total_outflows_rel is the remaining outflows to be distributed between all relative outflows
                for flow in outflows_rel:
                    flow.is_evaluated = True
                    flow.evaluated_value = flow.evaluated_share * total_outflows_rel
                    flow.evaluate_indicator_values_from_baseline_value()

            else:
                # All inflows are evaluated but the current process does not have stocks
                outflows_abs = self._get_process_outflows_abs(process_id, year)
                outflows_rel = self._get_process_outflows_rel(process_id, year)
                total_outflows_abs = np.sum([flow.evaluated_value for flow in outflows_abs])

                # Ignore root and leaf processes because those have zero inflows and zero outflows
                is_root = self.is_root_process(process_id)
                is_leaf = self.is_leaf_process(process_id)

                # Check that virtual flows are actually needed
                diff = abs(total_inflows - total_outflows_abs)
                need_virtual_flows = total_inflows < total_outflows_abs and (diff > self._virtual_flows_epsilon)
                if not is_root and not is_leaf and total_inflows < total_outflows_abs:
                    if self._use_virtual_flows and need_virtual_flows:

                        # TODO: Show error message if inflows are not able to satisfy the defined outflow
                        print("{}: Create virtual inflow".format(year))
                        diff = total_inflows - total_outflows_abs
                        process = self.get_process(process_id, year)
                        v_process = self._create_virtual_process_ex(process)
                        v_flow = self._create_virtual_flow_ex(v_process, process, abs(diff))
                        v_flow.evaluate_indicator_values_from_baseline_value()

                        # Create virtual Flows and Processes to current year data
                        self._year_to_process_id_to_process[year][v_process.id] = v_process
                        self._year_to_process_id_to_flow_ids[year][v_process.id] = {"in": [], "out": []}
                        self._unique_process_id_to_process[v_process.id] = v_process

                        self._year_to_flow_id_to_flow[year][v_flow.id] = v_flow
                        self._year_to_process_id_to_flow_ids[year][v_flow.target_process_id]["in"].append(v_flow.id)
                        self._year_to_process_id_to_flow_ids[year][v_flow.source_process_id]["out"].append(v_flow.id)
                        self._unique_flow_id_to_flow[v_flow.id] = v_flow

                        # Recalculate total_inflows again
                        total_inflows = self.get_process_inflows_total(process_id)

                # Remaining outflows to be distributed between all relative outflows
                total_outflows_rel = total_inflows - total_outflows_abs
                for flow in outflows_rel:
                    flow.is_evaluated = True
                    flow.evaluated_value = flow.evaluated_share * total_outflows_rel
                    flow.evaluate_indicator_values_from_baseline_value()

            is_evaluated = True
            return is_evaluated, outflows

        for flow in outflows:
            if flow.is_unit_absolute_value:
                flow.is_evaluated = True

        return is_evaluated, outflows

    def _solve_timestep(self) -> None:
        self._current_flow_id_to_flow = self._year_to_flow_id_to_flow[self._year_current]
        self._current_process_id_to_flow_ids = self._year_to_process_id_to_flow_ids[self._year_current]
        self._current_process_id_to_process = self._year_to_process_id_to_process[self._year_current]

        # Mark all absolute flows as evaluated at the start of each timestep and also
        # mark all flows that have target process ID in prioritized transform stage as prioritized
        self._prepare_flows_for_timestep(self._current_flow_id_to_flow, self._year_current)

        # Each year evaluate dynamic stock outflows and related outflows as evaluated
        # NOTE: All outflows from process with stocks are initialized as evaluated relative flows
        # Without this mechanism the relative outflows from stocks are not possible, and it
        # would prevent in some cases the whole evaluation of scenarios with stocks.
        self._evaluate_dynamic_stock_outflows(self._year_current)

        # TODO: At the start of the second timestep there already is Virtual process in list of Processes to evaluate
        # TODO: Is this still the case?

        # Add all root processes (= processes with no inflows) to unvisited list
        unevaluated_process_ids = []
        evaluated_process_ids = []
        current_year_process_ids = list(self._current_process_id_to_process.keys())
        for process_id in current_year_process_ids:
            inflows = self._get_process_inflows(process_id, year=self._year_current)
            if not inflows:
                unevaluated_process_ids.append(process_id)

        # Process flow value propagation until all inflows to processes are calculated
        current_iteration = 0
        while unevaluated_process_ids:
            process_id = unevaluated_process_ids.pop(0)
            if process_id in evaluated_process_ids:
                continue

            is_evaluated, outflows = self._evaluate_process(process_id, self._year_current)
            if is_evaluated:
                evaluated_process_ids.append(process_id)
                for flow in outflows:
                    target_process_id = flow.target_process_id
                    if target_process_id not in unevaluated_process_ids:
                        unevaluated_process_ids.insert(0, target_process_id)

            else:
                # Check all outflow target process ids
                for flow in outflows:
                    target_process_id = flow.target_process_id
                    if target_process_id not in unevaluated_process_ids:
                        unevaluated_process_ids.insert(0, target_process_id)

                # Add this process_id back to unevaluated list
                if process_id not in unevaluated_process_ids:
                    unevaluated_process_ids.append(process_id)

            # NOTE: Break out of infinite loop if running over big amount of iterations
            # This will happen if graph has loops that contain only relative flows between them
            current_iteration += 1
            if current_iteration >= self._max_iterations:
                print("Encountered processes that could not be evaluated in year {}:".format(self._year_current))
                print("The following processes have no inflows and have ONLY relative outflows (= error in data)")
                print("Possible ways to to fix:")
                print("- Introducing a valid inflow to the process")
                print("- Ensure that a valid inflow is present for the process in the model's initial year")
                print("")

                # Get list of unevaluated flows
                # The possible process causing the error is probably one of the flows' source processes
                unevaluated_inflows = []
                for p_id in current_year_process_ids:
                    for flow in self._get_process_inflows(p_id, self._year_current):
                        if not flow.is_evaluated:
                            unevaluated_inflows.append(flow)

                # Check all flow source processes and check for problematic processes:
                # Invalid process means:
                # - no inflows
                # - only relative outflows
                # This is definitely error in data
                unique_process_ids = set()
                for flow in unevaluated_inflows:
                    source_process_inflows = self._get_process_inflows(flow.source_process_id, self._year_current)
                    source_process_outflows = self._get_process_outflows(flow.source_process_id, self._year_current)
                    has_no_inflows = len(source_process_inflows) == 0
                    has_only_relative_outflows = len(source_process_outflows) > 0 and all(
                        [not flow.is_unit_absolute_value for flow in source_process_outflows])

                    if has_no_inflows and has_only_relative_outflows:
                        unique_process_ids.add(flow.source_process_id)

                print("List of invalid process IDs:")
                for source_process_id in unique_process_ids:
                    print("\t{}".format(source_process_id))
                print("")

                print("List of unevaluated flows:")
                for flow in unevaluated_inflows:
                    print("\t{}".format(flow))

                # print("Unevaluated process IDs:")
                # for pid in unevaluated_process_ids:
                #     print("\t{}".format(pid))
                raise SystemExit(-100)

        # Check for unreported inflows or outflows (= process mass balance != 0)
        # and create virtual flows to balance out those processes
        if self._use_virtual_flows:
            # epsilon is max allowed difference of input and outputs, otherwise create virtual processes and flows
            self._create_virtual_flows(self._year_current, self._virtual_flows_epsilon)

    def _advance_timestep(self) -> None:
        self._year_prev = self._year_current
        self._year_current += 1

    def _create_virtual_process_id(self, process: Process):
        return self._virtual_process_id_prefix + process.id

    def _create_virtual_process_name(self, process: Process):
        return self._virtual_process_id_prefix + process.name

    def _create_virtual_process_transformation_stage(self):
        return self._virtual_process_transformation_stage

    def _create_virtual_process(self, process_id: str, process_name: str, transformation_stage: str) -> Process:
        new_virtual_process = Process()
        new_virtual_process.id = process_id
        new_virtual_process.name = process_name
        new_virtual_process.stock_lifetime = 1
        new_virtual_process.conversion_factor = 1.0
        new_virtual_process.transformation_stage = transformation_stage
        new_virtual_process.is_virtual = True
        return new_virtual_process

    def _create_virtual_process_ex(self, process: Process) -> Process:
        v_id = self._create_virtual_process_id(process)
        v_name = self._create_virtual_process_name(process)
        v_ts = self._create_virtual_process_transformation_stage()
        v_process = self._create_virtual_process(v_id, v_name, v_ts)
        return v_process

    def _create_virtual_flow(self, source_process_id: str, target_process_id: str, value: float, unit: str) -> Flow:
        new_virtual_flow = Flow()
        new_virtual_flow.source_process_id = source_process_id
        new_virtual_flow.target_process_id = target_process_id
        new_virtual_flow.value = value
        new_virtual_flow.is_evaluated = True
        new_virtual_flow.evaluated_value = value
        new_virtual_flow.unit = unit
        new_virtual_flow.is_virtual = True

        # Copy indicators to virtual flows
        for indicator_name, indicator in self._indicators.items():
            new_indicator = copy.deepcopy(indicator)
            new_virtual_flow.indicator_name_to_indicator[new_indicator.name] = new_indicator
            new_virtual_flow.indicator_name_to_evaluated_value[new_indicator.name] = 0.0

        return new_virtual_flow

    def _create_virtual_flow_ex(self, source_process: Process, target_process: Process, value: float) -> Flow:
        v_flow = self._create_virtual_flow(source_process.id, target_process.id, value, "")
        return v_flow

    def _create_virtual_flows(self, year: int, epsilon: float = 0.1) -> None:
        # Virtual outflow is unreported flow of process
        created_virtual_processes = {}
        created_virtual_flows = {}
        for process_id, process in self._current_process_id_to_process.items():
            # Skip virtual processes that were included during previous timesteps
            # to prevent cascading effect of creating infinite number of virtual processes and flows
            if process.is_virtual:
                continue

            # Ignore root and leaf processes (= root process has no inflows and leaf process has no outflows)
            is_root_process = self.is_root_process(process_id, year)
            is_leaf_process = self.is_leaf_process(process_id, year)
            if is_root_process or is_leaf_process:
                continue

            inflows_total = self.get_process_inflows_total(process_id, year)
            outflows_total = self.get_process_outflows_total(process_id, year)

            # If process has stock then consider only the stock outflows
            if process_id in self._process_id_to_stock:
                # Distribute baseline total outflow values
                baseline_dsm = self.get_baseline_dynamic_stocks()[process.id]
                baseline_stock_outflow = self._get_dynamic_stock_outflow_value(baseline_dsm, year)

                # Check that if process has absolute outflow then outflow value must be
                # less than stock outflow. If absolute outflow is greater than stock outflow
                # then there is user error with the data
                outflows_abs = self._get_process_outflows_abs(process_id, year)
                outflows_rel = self._get_process_outflows_rel(process_id, year)
                total_outflows_abs = np.sum([flow.evaluated_value for flow in outflows_abs if not flow.is_prioritized])
                total_outflows_rel = np.sum([flow.evaluated_value for flow in outflows_rel])
                process_mass_balance = baseline_stock_outflow - total_outflows_abs - total_outflows_rel
            else:
                # Process has no stock
                process_mass_balance = inflows_total - outflows_total
                if abs(process_mass_balance) < epsilon:
                    # Inflows and outflows are balanced, do nothing and continue to next process
                    continue

            need_virtual_inflow = process_mass_balance < 0.0
            need_virtual_outflow = process_mass_balance > 0.0
            if not need_virtual_inflow and not need_virtual_outflow:
                continue

            if need_virtual_inflow:
                # Create new virtual Process
                v_process = self._create_virtual_process_ex(process)
                created_virtual_processes[v_process.id] = v_process

                # Create new virtual inflow
                source_process_id = v_process.id
                target_process_id = process_id
                value = process_mass_balance * -1.0
                unit = ""
                new_virtual_flow = self._create_virtual_flow(source_process_id, target_process_id, value, unit)
                created_virtual_flows[new_virtual_flow.id] = new_virtual_flow

            if need_virtual_outflow:
                # Create new virtual Process
                v_process = self._create_virtual_process_ex(process)
                created_virtual_processes[v_process.id] = v_process

                # Create new virtual outflow
                source_process_id = process_id
                target_process_id = v_process.id
                value = process_mass_balance
                unit = ""
                new_virtual_flow = self._create_virtual_flow(source_process_id, target_process_id, value, unit)
                created_virtual_flows[new_virtual_flow.id] = new_virtual_flow

        # Add create virtual Flows and Processes to current year data
        for v_id, virtual_process in created_virtual_processes.items():
            self._year_to_process_id_to_process[year][v_id] = virtual_process
            self._year_to_process_id_to_flow_ids[year][v_id] = {"in": [], "out": []}
            self._unique_process_id_to_process[v_id] = virtual_process

        for v_flow_id, virtual_flow in created_virtual_flows.items():
            self._year_to_flow_id_to_flow[year][v_flow_id] = virtual_flow
            self._year_to_process_id_to_flow_ids[year][virtual_flow.target_process_id]["in"].append(v_flow_id)
            self._year_to_process_id_to_flow_ids[year][virtual_flow.source_process_id]["out"].append(v_flow_id)
            self._unique_flow_id_to_flow[v_flow_id] = virtual_flow

        num_virtual_processes = len(created_virtual_processes)
        num_virtual_flows = len(created_virtual_flows)
        if num_virtual_processes or num_virtual_flows:
            print("Created {} virtual processes and {} virtual flows for year {}".format(
                num_virtual_processes, num_virtual_flows, year))

            for v_id, virtual_process in created_virtual_processes.items():
                print("\t- Virtual process ID '{}'".format(v_id))

            for v_flow_id, virtual_flow in created_virtual_flows.items():
                print("\t- Virtual flow ID '{} (value={:.5})'".format(v_flow_id, virtual_flow.evaluated_value))

            print("")

    def _create_dynamic_stocks(self):
        """
        Convert Stocks to ODYM DynamicStockModels.
        """
        # Create DynamicStockModels for Processes that contain Stock
        for stock in self.get_all_stocks():
            # If stock.distribution_params is float then use as default StdDev value
            # Otherwise check if the StdDev is defined for the cell
            stddev = 0.0
            shape = 1.0
            scale = 1.0
            if type(stock.stock_distribution_params) is float:
                stddev = stock.stock_distribution_params

            condition = None
            if type(stock.stock_distribution_params) is dict:
                stddev = stock.stock_distribution_params.get("stddev", 1.0)
                shape = stock.stock_distribution_params.get("shape", 1.0)
                scale = stock.stock_distribution_params.get("scale", 1.0)

                # For new decay functions
                landfill_decay_types = [StockDistributionType.LandfillDecayWood, StockDistributionType.LandfillDecayWood]
                if stock.stock_distribution_type in landfill_decay_types:
                    condition = stock.stock_distribution_params[StockDistributionParameter.Condition]

            # Stock parameters
            stock_years = np.array(self._years)
            stock_total_inflows = np.zeros(len(stock_years))
            stock_total = np.zeros(len(stock_years))
            stock_lifetime_params = {
                'Type': stock.stock_distribution_type,
                'Mean': [stock.stock_lifetime],
                'StdDev': [stddev],
                'Shape': [shape],
                'Scale': [scale],
                StockDistributionParameter.Condition: [condition],
            }

            # Baseline DSM
            baseline_dsm = DynamicStockModel(t=copy.deepcopy(stock_years),
                                             i=copy.deepcopy(stock_total_inflows),
                                             s=copy.deepcopy(stock_total),
                                             lt=copy.deepcopy(stock_lifetime_params))

            baseline_dsm.compute_s_c_inflow_driven()
            baseline_dsm.compute_o_c_from_s_c()
            baseline_dsm.compute_stock_total()
            baseline_dsm.compute_stock_change()
            baseline_dsm.compute_outflow_total()

            # Stock ID -> DSM
            self._stock_id_to_baseline_dsm[stock.id] = baseline_dsm

            # Create indicator DSMs for each indicator name
            for indicator_name in self.get_indicator_names():
                indicator_dsm = DynamicStockModel(t=copy.deepcopy(stock_years),
                                                  i=copy.deepcopy(stock_total_inflows),
                                                  s=copy.deepcopy(stock_total),
                                                  lt=copy.deepcopy(stock_lifetime_params))

                indicator_dsm.compute_s_c_inflow_driven()
                indicator_dsm.compute_o_c_from_s_c()
                indicator_dsm.compute_stock_total()
                indicator_dsm.compute_stock_change()
                indicator_dsm.compute_outflow_total()

                # Stock ID -> Indicator name -> DSM
                indicator_name_to_dsm = self._stock_id_to_indicator_name_to_dsm.get(stock.id, {})
                indicator_name_to_dsm[indicator_name] = indicator_dsm
                self._stock_id_to_indicator_name_to_dsm[stock.id] = indicator_name_to_dsm

    def _evaluate_dynamic_stock_outflows(self, year: int):
        """
        Evaluate dynamic stock outflows and distribute stock outflow among all outflows.
        Marks stock outflows as evaluated.

        This method must be called at the beginning of every timestep before starting evaluating Processes.

        :param year: Year
        """
        # Get stock outflow for year, distribute that to outflows and mark those Flows as evaluated
        year_index = self._years.index(year)
        for stock_id, dsm in self.get_baseline_dynamic_stocks().items():
            stock_total_outflow = dsm.compute_outflow_total()[year_index]
            outflows = self._get_process_outflows(stock_id)

            for flow in outflows:
                if flow.is_unit_absolute_value:
                    continue

                flow.is_evaluated = True
                flow.evaluated_value = flow.evaluated_share * stock_total_outflow

    def _get_dynamic_stock_outflow_value(self, dsm: DynamicStockModel, year: int) -> float:
        """
        Get dynamic stock total outflow value.

        :param dsm: Target DynamicStockModel
        :param year: Target year
        :return: Total stock outflow (float)
        """
        year_index = self._years.index(year)
        stock_outflow_total = dsm.compute_outflow_total()
        return stock_outflow_total[year_index]

    def get_solved_scenario_data(self) -> ScenarioData:
        # Make deep copies and return ScenarioData containing the data
        years = copy.deepcopy(self._years)
        year_to_process_id_to_process = copy.deepcopy(self._year_to_process_id_to_process)
        year_to_process_id_to_flow_ids = copy.deepcopy(self._year_to_process_id_to_flow_ids)
        year_to_flow_id_to_flow = copy.deepcopy(self._year_to_flow_id_to_flow)
        unique_process_id_to_process = copy.deepcopy(self._unique_process_id_to_process)
        unique_flow_id_to_flow = copy.deepcopy(self._unique_flow_id_to_flow)
        process_id_to_stock = copy.deepcopy(self._process_id_to_stock)
        stocks = copy.deepcopy(self._all_stocks)
        use_virtual_flows = copy.deepcopy(self._use_virtual_flows)
        virtual_flows_epsilon = copy.deepcopy(self._virtual_flows_epsilon)
        baseline_value_name = copy.deepcopy(self._baseline_value_name)
        baseline_unit_name = copy.deepcopy(self._baseline_unit_name)
        indicator_name_to_indicator = copy.deepcopy(self._indicator_name_to_indicator)

        scenario_data = ScenarioData(years=years,
                                     year_to_process_id_to_process=year_to_process_id_to_process,
                                     year_to_process_id_to_flow_ids=year_to_process_id_to_flow_ids,
                                     year_to_flow_id_to_flow=year_to_flow_id_to_flow,
                                     unique_process_id_to_process=unique_process_id_to_process,
                                     unique_flow_id_to_flow=unique_flow_id_to_flow,
                                     process_id_to_stock=process_id_to_stock,
                                     stocks=stocks,
                                     use_virtual_flows=use_virtual_flows,
                                     virtual_flows_epsilon=virtual_flows_epsilon,
                                     baseline_value_name=baseline_value_name,
                                     baseline_unit_name=baseline_unit_name,
                                     indicator_name_to_indicator=indicator_name_to_indicator
        )
        return scenario_data

    def _apply_flow_modifiers(self):
        """
        Apply flow modifiers if Scenario has those defined.
        Baseline scenario does not have those so return immediately
        if there isn't anything to process.
        """
        if not self._scenario.scenario_definition.flow_modifiers:
            # This is the case when dealing with baseline scenario, do nothing and just return
            return

        # Keep track of minimum value of flows
        row_to_opposite_flow_id_to_min_value = {}
        row_to_target_flow_id_to_min_value = {}

        # Keep track which year the minimum flow happened
        row_to_opposite_flow_id_to_year = {}
        row_to_target_flow_id_to_year = {}

        print("*** Applying flow modifiers for scenario '{}' ***".format(self._scenario.name))
        flow_modifiers = self._scenario.scenario_definition.flow_modifiers
        for flow_modifier in flow_modifiers:
            year_range = [year for year in range(flow_modifier.start_year, flow_modifier.end_year + 1)]
            source_process_id = flow_modifier.source_process_id
            target_process_id = flow_modifier.target_process_id
            source_to_target_flow_id = flow_modifier.target_flow_id

            new_values = []
            if flow_modifier.function_type == FunctionType.Constant:
                # NOTE: Constant replaces the values during the year range
                new_values = [flow_modifier.target_value for _ in year_range]

            # Change in value (delta)
            if flow_modifier.use_change_in_value:
                if flow_modifier.function_type == FunctionType.Linear:
                    new_values = np.linspace(start=0, stop=flow_modifier.change_in_value, num=len(year_range))

                if flow_modifier.function_type == FunctionType.Exponential:
                    new_values = np.logspace(start=0, stop=1, num=len(year_range))

                if flow_modifier.function_type == FunctionType.Sigmoid:
                    new_values = np.linspace(start=-flow_modifier.change_in_value,
                                               stop=flow_modifier.change_in_value,
                                               num=len(year_range))

                    new_values = flow_modifier.change_in_value / (1.0 + np.exp(-new_values))

            # Target value (current to target)
            if flow_modifier.use_target_value:
                source_to_target_flow = self.get_flow(source_to_target_flow_id, year_range[0])
                value_start = source_to_target_flow.value

                if flow_modifier.function_type == FunctionType.Linear:
                    new_values = np.linspace(start=value_start, stop=flow_modifier.target_value, num=len(year_range))

                if flow_modifier.function_type == FunctionType.Exponential:
                    # NOTE: Is this function working properly with target value?
                    new_values = np.logspace(start=0, stop=1, num=len(year_range))

                if flow_modifier.function_type == FunctionType.Sigmoid:
                    # NOTE: Is this function working properly with target value?
                    new_values = np.linspace(start=-flow_modifier.change_in_value,
                                             stop=flow_modifier.change_in_value,
                                             num=len(year_range))

                    new_values = flow_modifier.change_in_value / (1.0 + np.exp(-new_values))

            for year_index, year in enumerate(year_range):
                source_to_target_flow = self.get_flow(source_to_target_flow_id, year)
                value_old = 0.0
                value_new = 0.0

                # Replace the value for the flow value for the year instead of adding the change
                # Using the Constant-function: replace the value for the year and ignore all the
                # opposite target nodes
                if flow_modifier.function_type == FunctionType.Constant:
                    # NOTE: Using CONSTANT will ignore the opposite target process IDs
                    source_to_target_flow.value = new_values[year_index]
                    continue

                # Apply change in value (either absolute or relative) for the flow
                # and also to target opposite flows
                if flow_modifier.use_change_in_value:
                    if flow_modifier.is_change_type_value:
                        value_old, value_new = self._apply_absolute_change_to_flow(
                            source_to_target_flow, new_values[year_index])

                    if flow_modifier.is_change_type_proportional:
                        value_old, value_new = self._apply_relative_change_to_flow(
                            source_to_target_flow, new_values[year_index])

                    print(value_old, value_new)

                    # Clamp flow values:
                    if source_to_target_flow.is_unit_absolute_value:
                        # NOTE: Clamp only lower bound [0.0, no limits] to prevent absolute becoming negative
                        value_old = source_to_target_flow.value
                        value_new = self._clamp_flow_value(source_to_target_flow, 0.0, None)
                        if value_old < value_new:
                            s = "Clamped absolute target flow '{}' to 0.0 at year {}"
                            s += " because flow value was negative ({})"
                            s = s.format(source_to_target_flow_id, year, value_old)
                            print(s)
                    else:
                        # NOTE: Clamp relative flow value between [0, 100] % (here flow value = flow share)
                        value_old = source_to_target_flow.value
                        value_new = self._clamp_flow_value(source_to_target_flow, 0.0, 100.0)
                        if value_old < value_new:
                            s = "Clamped relative target flow '{}' to 0.0 at year {}"
                            s += " because flow value was negative ({})"
                            s = s.format(source_to_target_flow_id, year, value_old)
                            print(s)

                # Apply target value to the flow
                if flow_modifier.use_target_value:
                    value_old, value_new = self._apply_target_value_to_flow(source_to_target_flow, new_values[year_index])

                    # Clamp flow values:
                    if source_to_target_flow.is_unit_absolute_value:
                        # NOTE: Clamp only lower bound [0.0, no limits] to prevent absolute becoming negative
                        # TODO: Inform user that the value if the value is clamped
                        value_new = self._clamp_flow_value(source_to_target_flow, 0.0, None)

                    else:
                        # NOTE: Clamp relative flow value between [0, 100] % (here flow value = flow share)
                        # TODO: Inform user that the value if the value is clamped
                        value_new = self._clamp_flow_value(source_to_target_flow, 0.0, 100.0)

                value_diff = value_new - value_old
                if flow_modifier.has_opposite_targets:
                    # NOTE: Apply changes to all opposite targets equally
                    opposite_target_flow_share = 1.0 / len(flow_modifier.opposite_target_process_ids)
                    for opposite_target_process_id in flow_modifier.opposite_target_process_ids:
                        opposite_flow_id = "{} {}".format(source_process_id, opposite_target_process_id)
                        opposite_flow = self.get_flow(opposite_flow_id, year)

                        if flow_modifier.is_change_type_value:
                            opposite_value = -value_diff
                            opposite_value *= opposite_target_flow_share
                            self._apply_absolute_change_to_flow(opposite_flow, opposite_value)

                            # Keep track of minimum value for opposite flows
                            if opposite_flow.value < 0.0:
                                row = flow_modifier.row_number
                                if flow_modifier.row_number not in row_to_opposite_flow_id_to_min_value:
                                    row_to_opposite_flow_id_to_min_value[row] = {}
                                    row_to_opposite_flow_id_to_year[row] = {}

                                opposite_flow_id_to_min_value = row_to_opposite_flow_id_to_min_value[row]
                                opposite_flow_id_to_year = row_to_opposite_flow_id_to_year[row]
                                if opposite_flow.id not in opposite_flow_id_to_min_value:
                                    opposite_flow_id_to_min_value[opposite_flow_id] = opposite_flow.value
                                    opposite_flow_id_to_year[opposite_flow_id] = year
                                else:
                                    prev_min_value = opposite_flow_id_to_min_value[opposite_flow_id]
                                    if opposite_flow.value < prev_min_value:
                                        opposite_flow_id_to_min_value[opposite_flow_id] = opposite_flow.value
                                        opposite_flow_id_to_year[opposite_flow_id] = year

                        if flow_modifier.is_change_type_proportional:
                            opposite_value = -(value_diff / opposite_flow.value) * 100.0
                            opposite_value *= opposite_target_flow_share
                            self._apply_relative_change_to_flow(opposite_flow, opposite_value)

                            # Keep track of minimum value for opposite flows
                            if opposite_flow.value < 0.0:
                                row = flow_modifier.row_number
                                if flow_modifier.row_number not in row_to_opposite_flow_id_to_min_value:
                                    row_to_opposite_flow_id_to_min_value[row] = {}
                                    row_to_opposite_flow_id_to_year[row] = {}

                                opposite_flow_id_to_min_value = row_to_opposite_flow_id_to_min_value[row]
                                opposite_flow_id_to_year = row_to_opposite_flow_id_to_year[row]
                                if opposite_flow.id not in opposite_flow_id_to_min_value:
                                    opposite_flow_id_to_min_value[opposite_flow_id] = opposite_flow.value
                                    opposite_flow_id_to_year[opposite_flow_id] = year
                                else:
                                    prev_min_value = opposite_flow_id_to_min_value[opposite_flow_id]
                                    if opposite_flow.value < prev_min_value:
                                        opposite_flow_id_to_min_value[opposite_flow_id] = opposite_flow.value
                                        opposite_flow_id_to_year[opposite_flow_id] = year

                else:
                    # Apply change to all same type outflows as flow_modifier
                    # NOTE: Apply changes to all opposite targets equally
                    is_source_flow_abs = source_to_target_flow.is_unit_absolute_value
                    flows_out = self.get_process_outflows(source_process_id, year)

                    # Get list of same type flows as the source to target Process flow
                    target_flows = [flow for flow in flows_out if flow.is_unit_absolute_value == is_source_flow_abs
                                    and flow.target_process_id != target_process_id]

                    for target_flow in target_flows:
                        target_flow_share = 1.0 / len(target_flows)

                        if flow_modifier.is_change_type_value:
                            opposite_value = -value_diff
                            opposite_value *= target_flow_share
                            self._apply_absolute_change_to_flow(target_flow, opposite_value)

                            # Keep track of minimum value for target flows
                            if target_flow.value < 0.0:
                                row = flow_modifier.row_number
                                if flow_modifier.row_number not in row_to_target_flow_id_to_min_value:
                                    row_to_target_flow_id_to_min_value[row] = {}
                                    row_to_target_flow_id_to_year[row] = {}

                                target_flow_to_min_value = row_to_target_flow_id_to_min_value[row]
                                target_flow_id_to_year = row_to_target_flow_id_to_year[row]
                                if target_flow.id not in target_flow_to_min_value:
                                    target_flow_to_min_value[target_flow.id] = target_flow.value
                                    target_flow_id_to_year[target_flow.id] = year
                                else:
                                    prev_min_value = target_flow_to_min_value[target_flow.id]
                                    if target_flow.value < prev_min_value:
                                        target_flow_to_min_value[target_flow.id] = target_flow.value
                                        target_flow_id_to_year[target_flow.id] = year

                        if flow_modifier.is_change_type_proportional:
                            opposite_value = -(value_diff / target_flow.value) * 100.0
                            opposite_value *= target_flow_share
                            self._apply_relative_change_to_flow(target_flow, opposite_value)

                            # Keep track of minimum value for target flows
                            if target_flow.value < 0.0:
                                row = flow_modifier.row_number
                                if flow_modifier.row_number not in row_to_target_flow_id_to_min_value:
                                    row_to_target_flow_id_to_min_value[row] = {}
                                    row_to_target_flow_id_to_year[row] = {}

                                target_flow_to_min_value = row_to_target_flow_id_to_min_value[row]
                                target_flow_id_to_year = row_to_target_flow_id_to_year[row]
                                if target_flow.id not in target_flow_to_min_value:
                                    target_flow_to_min_value[target_flow.id] = target_flow.value
                                    target_flow_id_to_year[target_flow.id] = year
                                else:
                                    prev_min_value = target_flow_to_min_value[target_flow.id]
                                    if target_flow.value < prev_min_value:
                                        target_flow_to_min_value[target_flow.id] = target_flow.value
                                        target_flow_id_to_year[target_flow.id] = year

            # Show errors about applied flow modifier if any
            has_error = False
            if row_to_opposite_flow_id_to_min_value:
                has_error = True
                row = list(row_to_opposite_flow_id_to_min_value.keys())[0]

                print("Following errors happened when applying flow modifier from row {}:".format(row))
                opposite_flow_id_to_min_value = row_to_opposite_flow_id_to_min_value[row]
                opposite_flow_id_to_year = row_to_opposite_flow_id_to_year[row]
                for opposite_flow_id, min_value in opposite_flow_id_to_min_value.items():
                    year = opposite_flow_id_to_year[opposite_flow_id]
                    s = "Opposite target flow '{}' reached minimum negative flow value ({:.5f}) at year {}".format(
                        opposite_flow_id, min_value, year)
                    print("\t{}".format(s))

                print("\n\tThis is caused by the source process not having enough inflows to satisfy all process outflows")

            if row_to_target_flow_id_to_min_value:
                has_error = True
                row = list(row_to_target_flow_id_to_min_value.keys())[0]

                print("Following errors happened when applying flow modifier from row {}:".format(row))
                target_flow_id_to_min_value = row_to_target_flow_id_to_min_value[row]
                target_flow_id_to_year = row_to_target_flow_id_to_year[row]
                for target_flow_id, min_value in target_flow_id_to_min_value.items():
                    year = target_flow_id_to_year[target_flow_id]
                    s = "Target flow '{}' reached minimum negative flow value ({:.5f}) at year {}".format(
                        target_flow_id, min_value, year)
                    print("\t{}".format(s))

                print("\n\tThis is caused by the source process not having enough inflows to satisfy all process outflows")

            if has_error:
                raise Exception("Flow modifier error")


    def _apply_absolute_change_to_flow(self, flow: Flow, value: float) -> Tuple[float, float]:
        """
        Apply absolute change to Flow.

        :param flow: Target Flow
        :param value: Value,
        :return Tuple (old value: float, new value: float)
        """
        value_old = flow.value
        flow.value += value
        value_new = flow.value
        return value_old, value_new

    def _apply_relative_change_to_flow(self, flow: Flow, value: float) -> Tuple[float, float]:
        """
        Apply relative (= percentual) change to Flow.
        Value should not be normalized.

        :param flow: Target Flow
        :param value: Value (not normalized)
        :return Tuple (old value: float, new value: float)
        """
        value_old = flow.value
        flow.value += flow.value * (value / 100.0)
        value_new = flow.value
        return value_old, value_new

    def _apply_target_value_to_flow(self, flow: Flow, value: float) -> Tuple[float, float]:
        """
        Appy target value to Flow.
        Value should not be normalized.

        :param flow:
        :param value:
        :return: Tuple (old value: float, new value: float)
        """
        value_old = flow.value
        flow.value = value
        value_new = flow.value
        return value_old, value_new


    def _clamp_flow_value(self,
                          flow: Flow,
                          mini: Union[float, None] = 0.0,
                          maxi: Union[float, None] = 100.0) -> float:
        """
        Clamp Flow value to range [mini, maxi].
        Mini and maxi are both included in the range.
        Default range is [0.0, 100.0].

        If mini is None then do not check for lower bound.
        If maxi is None then do not check for upper bound

        :param flow: Target Flow
        :param mini: Lower bound value
        :param maxi: Upper bound value
        :return Clamped value
        """
        has_mini = mini is not None
        has_maxi = maxi is not None
        apply_both_bounds = has_mini and has_maxi
        apply_only_lower_bound = has_mini and not has_maxi
        apply_only_higher_bound = not has_mini and has_maxi
        if apply_both_bounds:
            flow.value = np.clip(flow.value, mini, maxi)

        if apply_only_lower_bound:
            if flow.value < mini:
                flow.value = mini

        if apply_only_higher_bound:
            if flow.value > maxi:
                flow.value = maxi

        return flow.value

