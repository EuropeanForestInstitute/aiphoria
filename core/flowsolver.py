import copy
import numpy as np
import pandas as pd
import tqdm as tqdm
from pandas import DataFrame
from core.datastructures import Process, Flow, Stock, ScenarioData, Scenario
from core.types import ChangeType, FunctionType
from lib.odym.modules.dynamic_stock_model import DynamicStockModel
from typing import List, Dict


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

        # Convert all relative flow values to [0, 1] range
        # and convert all absolute values to solid wood equivalent values
        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                if flow.is_unit_absolute_value:
                    flow.is_evaluated = True
                    flow.evaluated_share = 1.0
                    flow.evaluated_value = flow.value
                else:
                    # Relative flow, convert value to [0, 1] range
                    flow.is_evaluated = False
                    flow.evaluated_share = flow.value / 100.0
                    flow.evaluated_value = 0.0

        # Stock ID to ODYM DynamicStockModel
        self._stock_id_to_dsm_swe = {}
        self._stock_id_to_dsm_carbon = {}

    def get_all_stocks(self):
        return self._all_stocks

    def get_unique_processes(self) -> Dict[str, Process]:
        return self._unique_process_id_to_process

    def get_unique_flows(self) -> Dict[str, Flow]:
        return self._unique_flow_id_to_flow

    # Utility methods
    def get_processes_as_dataframe(self):
        df = pd.DataFrame({"Year": [], "Process ID": [], "Total inflows": [], "Total outflows": []})
        for year, process_id_to_process in self._year_to_process_id_to_process.items():
            for process_id, process in process_id_to_process.items():
                inflows_total = self.get_process_inflows_total(process_id, year)
                outflows_total = self.get_process_outflows_total(process_id, year)
                new_row = [year, process_id, inflows_total, outflows_total]
                df.loc[len(df.index)] = new_row
        return df

    def get_flows_as_dataframe(self) -> DataFrame:
        df = pd.DataFrame({
            "Year": [], "Flow ID": [], "Source process ID": [], "Target process ID": [],
            "Value (SWE)": [], "Value (Carbon)": []
        })
        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                new_row = [year, flow_id, flow.source_process_id, flow.target_process_id,
                           flow.evaluated_value, flow.evaluated_value_carbon]
                df.loc[len(df.index)] = new_row
        return df

    def get_evaluated_flow_values_as_dataframe(self) -> DataFrame:
        # Populate flow values per year, initialize flow values to 0.0
        unique_flows = self.get_unique_flows()
        df_flow_values = pd.DataFrame(index=self._years)
        for flow_id in unique_flows:
            df_flow_values[flow_id] = [0.0 for _ in self._years]

        year_to_process_to_flows = self.get_year_to_process_to_flows()

        # Populate flow values
        for year in df_flow_values.index:
            process_to_flows = year_to_process_to_flows[year]
            for flow_id in df_flow_values.columns:
                for process, flows in process_to_flows.items():
                    outflows = flows["out"]
                    for flow in outflows:
                        if flow.id == flow_id:
                            df_flow_values.at[year, flow_id] = flow.evaluated_value

        return df_flow_values

    def get_process(self, process_id: str, year=-1) -> Process:
        if year >= 0:
            return self._year_to_process_id_to_process[year][process_id]

        return self._current_process_id_to_flow_ids[process_id]

    def get_flow(self, flow_id: str, year=-1) -> Flow:
        if year >= 0:
            return self._year_to_flow_id_to_flow[year][flow_id]

        return self._current_flow_id_to_flow[flow_id]

    def get_stock(self, process_id: str) -> Stock:
        """
        Get stock by ID.
        NOTE: Process and stocks share the same ID

        :param process_id: Process ID
        :return:
        """
        return self._process_id_to_stock[process_id]

    def get_dynamic_stocks_swe(self) -> dict[str, DynamicStockModel]:
        """
        Get dictionary of stock ID to solid-wood equivalent DynamicStockModel.
        """
        return self._stock_id_to_dsm_swe

    def get_dynamic_stocks_carbon(self) -> dict[str, DynamicStockModel]:
        """
        Get dictionary of stock ID to carbon DynamicStockModel.
        """
        return self._stock_id_to_dsm_carbon

    def get_process_inflows_total(self, process_id, year=-1):
        """
        Get total inflows (SWE) for Process ID.

        :param process_id: Target Process ID
        :param year: Target year
        :return: Total of all inflows (SWE)
        """
        total = 0.0
        inflows = self._get_process_inflows(process_id, year)
        for flow in inflows:
            total += flow.evaluated_value
        return total

    def get_process_outflows_total(self, process_id, year=-1):
        """
        Get total outflows (SWE) for Process ID.

        :param process_id: Target Process ID
        :param year: Target year
        :return: Total of all outflows (SWE)
        """
        total = 0.0
        outflows = self._get_process_outflows(process_id, year)
        for flow in outflows:
            total += flow.evaluated_value
        return total

    def get_process_inflows_total_swe(self, process_id, year=-1):
        total = 0.0
        inflows = self._get_process_inflows(process_id, year)
        for flow in inflows:
            total += flow.evaluated_value
        return total

    def get_process_inflows_total_carbon(self, process_id, year=-1):
        total = 0.0
        inflows = self._get_process_inflows(process_id, year)
        for flow in inflows:
            total += flow.evaluated_value_carbon
        return total

    def get_process_outflows_total_swe(self, process_id, year=-1):
        total = 0.0
        outflows = self._get_process_outflows(process_id, year)
        for flow in outflows:
            total += flow.evaluated_value
        return total

    def get_process_outflows_total_carbon(self, process_id, year=-1):
        total = 0.0
        outflows = self._get_process_outflows(process_id, year)
        for flow in outflows:
            total += flow.evaluated_value_carbon
        return total

    def solve_timesteps(self):
        """
        Solves all time steps.
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

    def get_year_to_process_to_flows(self):
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

    def get_process_flows(self, process_id: str, year: int) -> Dict[str, List[Flow]]:
        process_inflows = self._get_process_inflows(process_id, year)
        process_outflows = self._get_process_outflows(process_id, year)
        return {"Inflows": process_inflows, "Outflows": process_outflows}

    def get_process_inflows(self, process_id: str, year: int) -> List[Flow]:
        return self._get_process_inflows(process_id, year)

    def get_process_outflows(self, process_id: str, year: int) -> List[Flow]:
        return self._get_process_inflows(process_id, year)

    def is_root_process(self, process_id: str, year: int = -1) -> bool:
        """
        Check if Process has no inflows in the given year.

        :param process_id: Process ID
        :param year: Selected year
        :return: True if Process has no inflows, False otherwise
        """
        return len(self._get_process_inflows(process_id, year)) == 0

    def is_leaf_process(self, process_id: str, year: int = -1) -> bool:
        """
        Check if Process has no outflows in the given year.

        :param process_id: Process ID
        :param year: Selected year
        :return: True if Process has no outflows, False otherwise
        """
        return len(self._get_process_outflows(process_id, year)) == 0

    def has_flow(self, flow_id: str, year=-1) -> bool:
        """
        Check if Flow with ID exists in the selected year.

        :param flow_id: Flow ID
        :param year: Selected year. If not defined then uses the current year inside FlowSolver.
        :return: True if Flow with ID exists for year, False otherwise.
        """

        if year >= 0:
            return flow_id in self._year_to_flow_id_to_flow[year]

        return flow_id in self._current_flow_id_to_flow

    def has_process(self, process_id: str, year=-1) -> bool:
        """
        Check if Process with ID exists in the selected year.

        :param process_id: Process ID
        :param year: Selected year. If not defined then uses the current year inside FlowSolver.
        :return: True if Process with ID exists for year, False otherwise.
        """
        if year >= 0:
            return process_id in self._year_to_process_id_to_process[year]

        return process_id in self._current_process_id_to_process

    def accumulate_dynamic_stock_inflows(self, dsm: DynamicStockModel, total_inflows: float, year: int) -> None:
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

    def _get_year_to_process_id_to_process(self) -> Dict[str, Dict[str, Process]]:
        return self._year_to_process_id_to_process

    def _get_year_to_process_id_to_flows(self):
        return self.year_to_process_id_to_flows

    def _get_year_to_flow_id_to_flow(self) -> Dict[int, Dict[str, Flow]]:
        return self._year_to_flow_id_to_flow

    def _get_process_inflow_ids(self, process_id, year=-1) -> List[str]:
        result = []
        if year >= 0:
            result = self._year_to_process_id_to_flow_ids[year][process_id]["in"]
        else:
            result = self._current_process_id_to_flow_ids[process_id]["in"]

        # If year -> process ID does not exists, return empty array
        if not result:
            result = []

        return result

    def _get_process_outflow_ids(self, process_id, year=-1) -> List[str]:
        result = []
        if year >= 0:
            result = self._year_to_process_id_to_flow_ids[year][process_id]["out"]
        else:
            result = self._current_process_id_to_flow_ids[process_id]["out"]

        if not result:
            result = []
        return result

    def _get_process_inflows(self, process_id: str, year: int = -1) -> List[Flow]:
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
        :param year: Selected uear
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
        :param year: Selected uear
        :return: List of relative outflows (Flow)
        """

        outflows_rel = []
        flows = self._get_process_outflows(process_id, year)
        for flow in flows:
            if not flow.is_unit_absolute_value:
                outflows_rel.append(flow)
        return outflows_rel

    def _evaluate_process(self, process_id: str, year: int) -> tuple[bool, List]:
        is_evaluated = False
        inflows = self._get_process_inflows(process_id, year)
        outflows = self._get_process_outflows(process_id, year)

        # Root process should have only absolute outflow
        if self.is_root_process(process_id, year):
            is_evaluated = True
            return is_evaluated, outflows

        total_inflows = 0.0
        total_inflows_carbon = 0.0
        for flow in inflows:
            if flow.is_evaluated:
                total_inflows += flow.evaluated_value
                total_inflows_carbon += flow.evaluated_value_carbon

        # Distribute outflows (stock or direct) only if all the inflows are already evaluated
        if all([flow.is_evaluated for flow in inflows]):
            total_outflows = 0.0

            # Subtract absolute outflows from total inflows
            # and distribute the remaining total between all relative flows
            if process_id in self._stock_id_to_dsm_swe:
                # All inflows are evaluated but process has stocks

                # Update DSM SWE
                dsm_swe = self._stock_id_to_dsm_swe[process_id]
                self.accumulate_dynamic_stock_inflows(dsm_swe, total_inflows, year)

                # Update DSM carbon
                dsm_carbon = self._stock_id_to_dsm_carbon[process_id]
                self.accumulate_dynamic_stock_inflows(dsm_carbon, total_inflows_carbon, year)

                # Distribute SWE total outflow values
                stock_outflow = self._get_dynamic_stock_outflow_value(dsm_swe, year)

                # Check that if process has absolute outflow then outflow value must be
                # less than stock outflow. If absolute outflow is greater than stock outflow
                # then there is user error with the data
                outflows_abs = self._get_process_outflows_abs(process_id, year)
                outflows_rel = self._get_process_outflows_rel(process_id, year)
                total_outflows_abs = np.sum([outflow.evaluated_value for outflow in outflows_abs])
                total_outflows_rel = stock_outflow - total_outflows_abs

                if total_outflows_rel < 0.0:
                    # This is error: Total absolute outflows are greater than stock outflow and
                    # it means that there is not enough flows to distribute between remaining
                    # relative outflows
                    s = "Process {}: stock outflow is less than sum of absolute outflows in year {}!".format(
                        process_id, year)
                    raise Exception(s)

                # total_outflows_rel is the remaining outflows to be distributed between all relative outflows
                for flow in outflows_rel:
                    flow.is_evaluated = True
                    flow.evaluated_value = flow.evaluated_share * total_outflows_rel

            else:
                # All inflows are evaluated but the current process does not have stocks
                outflows_abs = self._get_process_outflows_abs(process_id, year)
                outflows_rel = self._get_process_outflows_rel(process_id, year)
                total_outflows_abs = np.sum([flow.evaluated_value for flow in outflows_abs])

                # Ignore root and leaf processes because those have zero inflows and zero outflows
                is_root = self.is_root_process(process_id)
                is_leaf = self.is_leaf_process(process_id)
                if not is_root and not is_leaf and total_inflows < total_outflows_abs:
                    if self._use_virtual_flows:
                        # TODO: Show error message if inflows are not able to satisfy the defined outflow
                        print("{}: Create virtual inflow".format(year))
                        diff = total_inflows - total_outflows_abs
                        process = self.get_process(process_id, year)
                        v_process = self._create_virtual_process_ex(process)
                        v_flow = self._create_virtual_flow_ex(v_process, process, abs(diff))

                        # Create virtual Flows and Processes to current year data
                        self._year_to_process_id_to_process[year][v_process.id] = v_process
                        self._year_to_process_id_to_flow_ids[year][v_process.id] = {"in": [], "out": []}
                        self._unique_process_id_to_process[v_process.id] = v_process

                        self._year_to_flow_id_to_flow[year][v_flow.id] = v_flow
                        self._year_to_process_id_to_flow_ids[year][v_flow.target_process_id]["in"].append(v_flow.id)
                        self._year_to_process_id_to_flow_ids[year][v_flow.source_process_id]["out"].append(v_flow.id)
                        self._unique_flow_id_to_flow[v_flow] = v_flow

                        # Recalculate total_inflows again
                        total_inflows = self.get_process_inflows_total(process_id)

                # Remaining outflows to be distributed between all relative outflows
                total_outflows_rel = total_inflows - total_outflows_abs
                for flow in outflows_rel:
                    flow.is_evaluated = True
                    flow.evaluated_value = flow.evaluated_share * total_outflows_rel

            is_evaluated = True
            return is_evaluated, outflows

        for flow in outflows:
            if flow.is_unit_absolute_value:
                flow.is_evaluated = True

        return is_evaluated, outflows

    def _solve_timestep(self) -> None:
        self._current_flow_id_to_flow = self._year_to_flow_id_to_flow[self._year_current]
        self._current_process_id_to_flow_ids = self._year_to_process_id_to_flow_ids[self._year_current]

        # Check if any flow constraints should be applied at the start of each timestep
        self._apply_flow_constraints()

        # Each year evaluate dynamic stock outflows and related outflows as evaluated
        self._evaluate_dynamic_stock_outflows(self._year_current)

        # Mark all absolute flows as evaluated at the start of each timestep
        for flow_id, flow in self._current_flow_id_to_flow.items():
            if flow.is_unit_absolute_value:
                flow.is_evaluated = True
                flow.evaluated_share = 1.0
                flow.evaluated_value = flow.value
            else:
                flow.is_evaluated = False
                flow.evaluated_share = flow.value / 100.0
                flow.evaluated_value = 0.0
                # print("Inside solve_timestep: ", id(flow), flow)


        # Add all root processes (= processes with no inflows) to unvisited list
        unevaluated_process_ids = []
        evaluated_process_ids = []
        current_year_process_ids = list(self._year_to_process_id_to_process[self._year_current].keys())
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

            # NOTE: Break out of loop if running over big amount of iterations
            # This will happen if graph has loops that contain only relative flows between them
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

            # Break from infinite loop if detected one
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

            #print(inflows_total, outflows_total)

            # If process has stock then consider only the stock outflows
            if process_id in self._process_id_to_stock:
                # Distribute SWE total outflow values
                dsm_swe = self.get_dynamic_stocks_swe()[process.id]
                stock_outflow = self._get_dynamic_stock_outflow_value(dsm_swe, year)

                # Check that if process has absolute outflow then outflow value must be
                # less than stock outflow. If absolute outflow is greater than stock outflow
                # then there is user error with the data
                outflows_abs = self._get_process_outflows_abs(process_id, year)
                outflows_rel = self._get_process_outflows_rel(process_id, year)
                total_outflows_abs = np.sum([flow.evaluated_value for flow in outflows_abs])
                total_outflows_rel = np.sum([flow.evaluated_value for flow in outflows_rel])
                process_mass_balance = stock_outflow - total_outflows_abs - total_outflows_rel

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
                print("\t- Virtual flow ID '{}'".format(v_flow_id))

            print("")

    def _create_dynamic_stocks(self) -> None:
        """
        Convert Stocks to ODYM DynamicStockModels.
        :return: None
        """

        # Create DynamicStockModels for Processes that contain Stock
        for stock in self.get_all_stocks():
            stock_total = [0.0 for _ in self._years]
            stock_total_inflows = [0.0 for _ in self._years]

            # If stock.distribution_params is float then use as default StdDev value
            # Otherwise check if the StdDev is defined for the cell
            stddev = 0.0
            shape = 1.0
            scale = 1.0
            if type(stock.stock_distribution_params) is float:
                stddev = stock.stock_distribution_params

            if type(stock.stock_distribution_params) is dict:
                stddev = stock.stock_distribution_params.get("stddev", 1.0)
                shape = stock.stock_distribution_params.get("shape", 1.0)
                scale = stock.stock_distribution_params.get("scale", 1.0)

            stock_lifetime_params = {
                'Type': stock.stock_distribution_type,
                'Mean': [stock.stock_lifetime],
                'StdDev': [stddev],
                'Shape': [shape],
                'Scale': [scale],
            }

            new_dsm_swe = DynamicStockModel(t=np.array(self._years),
                                            i=stock_total_inflows,
                                            s=stock_total,
                                            lt=stock_lifetime_params)

            new_dsm_carbon = DynamicStockModel(t=np.array(self._years),
                                               i=copy.deepcopy(stock_total_inflows),
                                               s=copy.deepcopy(stock_total),
                                               lt=copy.deepcopy(stock_lifetime_params))

            # Compute initial SWE dynamic stock model data
            new_dsm_swe.compute_s_c_inflow_driven()
            new_dsm_swe.compute_o_c_from_s_c()
            new_dsm_swe.compute_stock_total()
            new_dsm_swe.compute_stock_change()
            new_dsm_swe.compute_outflow_total()

            # Compute initial carbon dynamic stock model data
            new_dsm_carbon.compute_s_c_inflow_driven()
            new_dsm_carbon.compute_o_c_from_s_c()
            new_dsm_carbon.compute_stock_total()
            new_dsm_carbon.compute_stock_change()
            new_dsm_carbon.compute_outflow_total()

            self._stock_id_to_dsm_swe[stock.id] = new_dsm_swe
            self._stock_id_to_dsm_carbon[stock.id] = new_dsm_carbon

    def _evaluate_dynamic_stock_outflows(self, year: int) -> None:
        """
        Evaluate dynamic stock outflows and distribute stock outflow among all outflows.
        Marks stock outflows as evaluated.

        This method must be called at the beginning of every timestep before starting evaluating Processes.

        :param year: Year
        :return: None
        """
        # Get stock outflow for year, distribute that to outflows and mark those Flows as evaluated
        year_index = self._years.index(year)
        for stock_id, dsm in self.get_dynamic_stocks_swe().items():
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
        :return: Total stock outflow  (float)
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

        scenario_data = ScenarioData(years=years,
                                     year_to_process_id_to_process=year_to_process_id_to_process,
                                     year_to_process_id_to_flow_ids=year_to_process_id_to_flow_ids,
                                     year_to_flow_id_to_flow=year_to_flow_id_to_flow,
                                     unique_process_id_to_process=unique_process_id_to_process,
                                     unique_flow_id_to_flow=unique_flow_id_to_flow,
                                     process_id_to_stock=process_id_to_stock,
                                     stocks=stocks,
                                     use_virtual_flows=use_virtual_flows,
                                     virtual_flows_epsilon=virtual_flows_epsilon
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

        print("*** Applying flow modifiers for scenario '{}' ***".format(self._scenario.name))
        flow_modifiers = self._scenario.scenario_definition.flow_modifiers
        for flow_modifier in flow_modifiers:
            year_range = [year for year in range(flow_modifier.start_year, flow_modifier.end_year + 1)]
            target_node_id = flow_modifier.target_node_id
            source_node_id = flow_modifier.source_node_id
            source_to_target_flow_id = "{} {}".format(source_node_id, target_node_id)

            # TODO: Not caring about the actual end year of the simulation now, check that later
            new_values = []
            if flow_modifier.function_type == FunctionType.Constant:
                # Replace the values during for the year range
                new_values = [flow_modifier.change_in_value for year in year_range]

            if flow_modifier.function_type == FunctionType.Linear:
                new_values = np.linspace(start=0, stop=flow_modifier.change_in_value, num=len(year_range))

            if flow_modifier.function_type == FunctionType.Exponential:
                new_values = np.logspace(start=0, stop=1, num=len(year_range))

            if flow_modifier.function_type == FunctionType.Sigmoid:
                new_values = np.linspace(start=-flow_modifier.change_in_value,
                                           stop=flow_modifier.change_in_value,
                                           num=len(year_range))

                new_values = flow_modifier.change_in_value / (1.0 + np.exp(-new_values))

            for year_index, year in enumerate(year_range):
                source_to_target_flow = self._year_to_flow_id_to_flow[year][source_to_target_flow_id]

                # Replace the value for the flow value for the year instead of adding the change
                # Using the Constant-function: replace the value for the year and ignore all the
                # opposite target nodes
                if flow_modifier.function_type == FunctionType.Constant:
                    source_to_target_flow.value = new_values[year_index]
                    #print("CONSTANT: ", source_to_target_flow, id(source_to_target_flow))
                    continue

                # Apply change in value (either absolute or relative) for the flow
                # and also to target opposite flows
                if flow_modifier.use_change_in_value:
                    if flow_modifier.is_change_type_absolute:
                        self._apply_absolute_change_to_flow(source_to_target_flow, new_values[year_index])

                    if flow_modifier.is_change_type_relative:
                        self._apply_relative_change_to_flow(new_values[year_index])

                    # Clamp flow values:
                    if source_to_target_flow.is_unit_absolute_value:
                        # TODO: Prevent absolute flow values < 0.0?
                        #self._clamp_flow_value(source_to_target_flow, 0.0, None)
                        pass
                    else:
                        # NOTE: Clamp relative flow value between [0, 100] % (here flow value = flow share)
                        self._clamp_flow_value(source_to_target_flow, 0.0, 100.0)

                # if flow_modifier.has_opposite_targets:
                #     print("Apply changes only to opposite target nodes")
                #     for opposite_target_node_id in flow_modifier.opposite_target_node_ids:
                #         source_to_opposite_node_id = "{} {}".format(source_node_id, opposite_target_node_id)
                #         opposite_flow = self._year_to_flow_id_to_flow[year][source_to_opposite_node_id]
                #
                #         # TODO: Check that the flow type matches (e.g. ABS with only ABS, REL with only REL)
                #         if flow_modifier.use_change_in_value:
                #             opposite_flow.value -= flow_modifier.change_in_value
                #         else:
                #             opposite_flow.value -= opposite_flow.value * (flow_modifier.change_in_value / 100.0)
                # else:
                #     # Apply change to all same type outflows as flow_modifier
                #     print("Apply change to all same type outflows")



    def _apply_absolute_change_to_flow(self, flow: Flow, value: float):
        """
        Apply absolute change to Flow.

        :param flow: Target Flow
        :param value: Value
        """
        flow.value += value

    def _apply_relative_change_to_flow(self, flow: Flow, value: float):
        """
        Apply relative (= percentual) change to Flow.
        Value should not be normalized.

        :param flow: Target Flow
        :param value: Value (not normalized)
        """
        flow.value += flow.value * (value / 100.0)

    def _clamp_flow_value(self, flow: Flow, mini: float = 0.0, maxi: float = 100.0):
        """
        Clamp Flow value to range [mini, maxi].
        Mini and maxi are both included in the range.
        Default range is [0.0, 100.0].

        If mini is None then do not check for lower bound.
        If maxi is None then do not check for upper bound

        :param flow: Target Flow
        :param mini: Lower bound value
        :param maxi: Upper bound value
        """
        has_mini = mini is not None
        has_maxi = maxi is not None
        apply_both_bounds = has_mini and has_maxi
        apply_only_lower_bound = has_mini and not has_maxi
        apply_only_higher_bound = not has_mini and has_maxi
        if apply_both_bounds:
            flow.value = np.clip(flow.value, mini, maxi)
            return

        if apply_only_lower_bound:
            if flow.value < mini:
                flow.value = mini
            return

        if apply_only_higher_bound:
            if flow.value > maxi:
                flow.value = maxi
            return

    def _apply_flow_constraints(self):
        # TODO:
        pass
