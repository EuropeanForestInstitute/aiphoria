from typing import List, Dict
import pandas as pd
from pandas import DataFrame
from core.datastructures import Process, Flow, Stock

VIRTUAL_PROCESS_ID_PREFIX = "VP_"
VIRTUAL_FLOW_ID_PREFIX = "VF_"
MAX_ITERATION_COUNT = 100000
VIRTUAL_PROCESS_TRANSFORMATION_STAGE = "Virtual"


# Solves flows to absolute values
class FlowSolver(object):
    def __init__(self, graph_data={}, use_virtual_flows=True, virtual_flow_epsilon=0.1):
        self._use_virtual_flows = use_virtual_flows
        self._virtual_flow_epsilon = virtual_flow_epsilon
        self._df_process_to_flows = graph_data["df_process_to_flows"]
        self._df_flows = graph_data["df_flows"]

        # Create year -> process ID -> process
        self._year_to_process_id_to_process = {}
        for year in self._df_process_to_flows.index:
            self._year_to_process_id_to_process[year] = {}
            for process_id in self._df_process_to_flows.columns:
                cell = self._df_process_to_flows.at[year, process_id]
                self._year_to_process_id_to_process[year][process_id] = cell["process"]

        # Create year -> process ID -> flow IDs
        self._year_to_process_id_to_flow_ids = {}
        for year in self._df_process_to_flows.index:
            self._year_to_process_id_to_flow_ids[year] = {}
            for process_id in self._df_process_to_flows.columns:
                cell = self._df_process_to_flows.at[year, process_id]
                inflow_ids = [flow.id for flow in cell["flows"]["in"]]
                outflow_ids = [flow.id for flow in cell["flows"]["out"]]
                self._year_to_process_id_to_flow_ids[year][process_id] = {"in": inflow_ids, "out": outflow_ids}

        # Create year -> flow ID -> flow
        self._year_to_flow_id_to_flow = {}
        for year in self._df_flows.index:
            self._year_to_flow_id_to_flow[year] = {}
            for flow_id in self._df_flows.columns:
                cell = self._df_flows.at[year, flow_id]
                if pd.isnull(cell):
                    continue

                self._year_to_flow_id_to_flow[year][flow_id] = cell

        self._process_id_to_stock = graph_data["process_id_to_stock"]
        self._all_processes = graph_data["all_processes"]
        self._all_flows = graph_data["all_flows"]
        self._all_stocks = graph_data["all_stocks"]
        self._unique_processes_id_to_process = graph_data["unique_process_id_to_process"]
        self._unique_flow_id_to_flow = graph_data["unique_flow_id_to_flow"]

        # Time range
        self._year_start = graph_data["year_start"]
        self._year_end = graph_data["year_end"]
        self._years = graph_data["years"]
        self._year_current = self._year_start
        self._year_prev = 0

        # Current timestep data
        self._current_process_id_to_process = self._year_to_process_id_to_process[self._year_current]
        self._current_process_id_to_flow_ids = self._year_to_process_id_to_flow_ids[self._year_current]
        self._current_flow_id_to_flow = self._year_to_flow_id_to_flow[self._year_current]

        # Initialization of FlowSolver data
        self._year_current = self._year_start
        self._year_prev = self._year_current

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

    def get_all_processes(self):
        return self._all_processes

    def get_all_flows(self):
        return self._all_flows

    def get_all_stocks(self):
        return self._all_stocks

    def get_unique_processes(self) -> Dict[str, Process]:
        return self._unique_processes_id_to_process

    def get_unique_flows(self) -> Dict[str, Flow]:
        return self._unique_flow_id_to_flow

    # Utility methods
    def get_processes_as_dataframe(self):
        df = pd.DataFrame({"Year": [], "Process ID": [], "Total inflows": [], "Total outflows": []})
        for year, process_id_to_process in self._year_to_process_id_to_process.items():
            for process_id, process in process_id_to_process.items():
                inflows_total = self.get_process_inflows_total(process_id)
                outflows_total = self.get_process_outflows_total(process_id)
                new_row = [year, process_id, inflows_total, outflows_total]
                df.loc[len(df.index)] = new_row
        return df

    def get_flows_as_dataframe(self) -> DataFrame:
        df = pd.DataFrame({"Year": [], "Flow ID": [], "Source process ID": [], "Target process ID": [], "Value": []})
        for year, flow_id_to_flow in self._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                new_row = [year, flow_id, flow.source_process_id, flow.target_process_id, flow.evaluated_value]
                df.loc[len(df.index)] = new_row
        return df

    def get_evaluated_flow_values_as_dataframe(self) -> DataFrame:
        # Populate flow values per year, initialize flow values to 0.0
        unique_flows = self.get_unique_flows()
        df_flow_values = pd.DataFrame(index=self._years)
        for flow_id in unique_flows:
            df_flow_values[flow_id] = [0.0 for year in self._years]

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

    def get_process(self, process_id, year=-1) -> Process:
        if year >= 0:
            return self._year_to_process_id_to_process[year][process_id]

        return self._current_process_id_to_flow_ids[process_id]

    def get_flow(self, flow_id, year=-1) -> Flow:
        if year >= 0:
            return self._year_to_flow_id_to_flow[year][flow_id]

        return self._current_flow_id_to_flow[flow_id]

    def get_stock(self, process_id) -> Stock:
        return self._process_id_to_stock[process_id]

    def get_process_inflows_total(self, process_id, year=-1):
        total = 0.0
        inflows = self._get_process_inflows(process_id, year)
        for flow in inflows:
            total += flow.evaluated_value
        return total

    def get_process_outflows_total(self, process_id, year=-1):
        total = 0.0
        outflows = self._get_process_outflows(process_id, year)
        for flow in outflows:
            total += flow.evaluated_value
        return total


    def solve_timesteps(self):
        """
        Solves all timesteps.
        :return: True if successful, False otherwise
        """
        for year in self._years:
            self._solve_timestep()
            self._advance_timestep()

        return True

    def get_year_to_process_to_flows(self):
        year_to_process_to_flows = {}
        for year, current_process_id_to_process in self._year_to_process_id_to_process.items():
            year_to_process_to_flows[year] = {}
            current_process_id_to_flow_ids = self._year_to_process_id_to_flow_ids[year]
            current_flow_id_to_flow = self._year_to_flow_id_to_flow[year]
            for process_id, process in self._current_process_id_to_process.items():
                flow_ids = current_process_id_to_flow_ids[process_id]
                inflow_ids = flow_ids["in"]
                outflow_ids = flow_ids["out"]

                process_flows = {"in": [], "out": []}
                for flow_id in inflow_ids:
                    process_flows["in"].append(current_flow_id_to_flow[flow_id])

                for flow_id in outflow_ids:
                    process_flows["out"].append(current_flow_id_to_flow[flow_id])

                year_to_process_to_flows[year][process] = process_flows

        return year_to_process_to_flows

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

    def _get_process_inflows(self, process_id, year=-1) -> List[Flow]:
        # Get list of process inflows for current year
        flows = []
        inflow_ids = self._get_process_inflow_ids(process_id, year)
        for flow_id in inflow_ids:
            flows.append(self.get_flow(flow_id, year))
        return flows

    # Get list of outflows (DataFlows)
    def _get_process_outflows(self, process_id, year=-1) -> List[Flow]:
        # Get list of outflows for current year
        flows = []
        outflow_ids = self._get_process_outflow_ids(process_id, year)
        for flow_id in outflow_ids:
            flows.append(self.get_flow(flow_id, year))
        return flows

    def _evaluate_process(self, process_id, year):
        is_evaluated = False
        inflows = self._get_process_inflows(process_id, year)
        outflows = self._get_process_outflows(process_id, year)

        # Root process, all outflows are absolute
        total_inflows = 0.0
        if not inflows:
            is_evaluated = True
            return is_evaluated, outflows

        for flow in inflows:
            if flow.is_evaluated:
                total_inflows += flow.evaluated_value

        if all([flow.is_evaluated for flow in inflows]):
            # All inflows are now evaluated:
            # Subtract absolute outflows from total inflows
            # and distribute the remaining total between all relative flows
            total_outflows = 0
            flows_relative = []
            for flow in outflows:
                if flow.is_unit_absolute_value:
                    total_outflows += flow.evaluated_value
                else:
                    flows_relative.append(flow)

            # Calculate values for all relative outflows
            total_rel = total_inflows - total_outflows
            for flow in flows_relative:
                flow.is_evaluated = True
                flow.evaluated_value = flow.evaluated_share * total_rel

            is_evaluated = True
            return is_evaluated, outflows

        for flow in outflows:
            if flow.is_unit_absolute_value:
                flow.is_evaluated = True

        return is_evaluated, outflows

    def _solve_timestep(self):
        self._current_flow_id_to_flow = self._year_to_flow_id_to_flow[self._year_current]
        self._current_process_id_to_flow_ids = self._year_to_process_id_to_flow_ids[self._year_current]

        # Add all root processes (= processes with no inflows) to unvisited list
        unevaluated_process_ids = []
        evaluated_process_ids = []
        for process in self._all_processes:
            inflows = self._get_process_inflows(process.id)
            if not inflows:
                unevaluated_process_ids.append(process.id)

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
            if current_iteration >= MAX_ITERATION_COUNT:
                print("Infinite loop detected!")

                # Print out the unevaluated process ids that are part of the loop
                print("Unevaluated process IDs:")
                for pid in unevaluated_process_ids:
                    print(pid)

                raise SystemExit(-100)

        # Check for unreported inflows or outflows (= process mass balance != 0)
        # and create virtual flows to balance out those processes
        if self._use_virtual_flows:
            # epsilon is max allowed difference of input and outputs, otherwise create virtual processes and flows
            self._create_virtual_flows(self._virtual_flow_epsilon)

        # Skip carrying values over to next year if next year is not valid anymore
        next_year = self._year_current + 1
        if next_year > self._year_end:
            return

        # # TODO: If target process contains loop then no carryover happens?
        # # Check for processes that carryover values to next timestep
        # for process_id in self.current_process_id_to_flow_ids:
        #     process = self.get_process(process_id, self.year_current)
        #     if process.is_virtual:
        #         continue
        #
        #     outflows = self.get_process_outflows(process_id, self.year_current)
        #     num_populated_outflows = 0
        #     for flow in outflows:
        #         if flow.value != 0:
        #             num_populated_outflows += 1
        #
        #     # Carry over values from processes that have no outflows and have no stocks
        #     has_no_stock = process_id not in self.process_id_to_stock
        #     if not num_populated_outflows and has_no_stock:
        #         total_inflows = self.get_process_inflows_total(process_id, self.year_current)
        #         outflows_next = self.get_process_outflows(process_id, next_year)
        #
        #         # Distribute total absolute inflows among all outflows next year
        #         # TODO: Now distribute all only to first outflow!
        #         if outflows_next:
        #             flow_id = outflows_next[0].id
        #             self.year_to_flow_id_to_flow[next_year][flow_id].value += total_inflows
        #             self.year_to_flow_id_to_flow[next_year][flow_id].evaluated_value += total_inflows

    def _advance_timestep(self):
        self._year_prev = self._year_current
        self._year_current += 1

    def _create_virtual_process(self, process_id: str, process_name: str, transformation_stage: str) -> Process:
        new_virtual_process = Process()
        new_virtual_process.id = process_id
        new_virtual_process.name = process_name
        new_virtual_process.lifetime = 1
        new_virtual_process.conversion_factor = 1.0
        new_virtual_process.transformation_stage = transformation_stage
        new_virtual_process.is_virtual = True
        return new_virtual_process

    def _create_virtual_flow(self, source_process_id, target_process_id, value, unit):
        new_virtual_flow = Flow()
        new_virtual_flow.source_process_id = source_process_id
        new_virtual_flow.target_process_id = target_process_id
        new_virtual_flow.value = value
        new_virtual_flow.is_evaluated = True
        new_virtual_flow.evaluated_value = value
        new_virtual_flow.unit = unit
        new_virtual_flow.is_virtual = True
        return new_virtual_flow

    def _create_virtual_flows(self, epsilon=0.1):
        # Virtual outflow is unreported flow of process
        created_virtual_processes = {}
        created_virtual_flows = {}

        for process_id, process in self._current_process_id_to_process.items():
            # Skip virtual processes that were included during previous timesteps
            # to prevent cascading effect of creating infinite number of virtual processes and flows
            if process.is_virtual:
                continue

            inflows = self._get_process_inflows(process_id)
            outflows = self._get_process_outflows(process_id)
            inflows_total = self.get_process_inflows_total(process_id)
            outflows_total = self.get_process_outflows_total(process_id)

            # Ignore root and leaf processes (= input and output processes to the system)
            # because those root processes do not have any inflows and
            # leaf processes do not have any outflows
            if not inflows or not outflows:
                continue

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
                v_id = VIRTUAL_PROCESS_ID_PREFIX + process.id
                v_name = VIRTUAL_PROCESS_ID_PREFIX + process.name
                v_ts = VIRTUAL_PROCESS_TRANSFORMATION_STAGE
                v_process = self._create_virtual_process(v_id, v_name, v_ts)
                created_virtual_processes[v_process.id] = v_process

                # Create new virtual inflow
                source_process_id = v_id
                target_process_id = process_id
                value = process_mass_balance * -1.0
                unit = ""
                new_virtual_flow = self._create_virtual_flow(source_process_id, target_process_id, value, unit)
                created_virtual_flows[new_virtual_flow.id] = new_virtual_flow

            if need_virtual_outflow:
                # Create new virtual Process
                v_id = VIRTUAL_PROCESS_ID_PREFIX + process.id
                v_name = VIRTUAL_PROCESS_ID_PREFIX + process.name
                v_ts = VIRTUAL_PROCESS_TRANSFORMATION_STAGE
                v_process = self._create_virtual_process(v_id, v_name, v_ts)
                created_virtual_processes[v_process.id] = v_process

                # Create new virtual outflow
                source_process_id = process_id
                target_process_id = v_id
                value = process_mass_balance
                unit = ""
                new_virtual_flow = self._create_virtual_flow(source_process_id, target_process_id, value, unit)
                created_virtual_flows[new_virtual_flow.id] = new_virtual_flow

        # Add create virtual Flows and Processes to current year data
        for v_id, virtual_process in created_virtual_processes.items():
            self._year_to_process_id_to_process[self._year_current][v_id] = virtual_process
            self._year_to_process_id_to_flow_ids[self._year_current][v_id] = {"in": [], "out": []}
            self._unique_processes_id_to_process[v_id] = virtual_process

        for v_flow_id, virtual_flow in created_virtual_flows.items():
            self._year_to_flow_id_to_flow[self._year_current][v_flow_id] = virtual_flow
            self._year_to_process_id_to_flow_ids[self._year_current][virtual_flow.target_process_id]["in"].append(v_flow_id)
            self._year_to_process_id_to_flow_ids[self._year_current][virtual_flow.source_process_id]["out"].append(v_flow_id)
            self._unique_flow_id_to_flow[v_flow_id] = virtual_flow

        num_virtual_processes = len(created_virtual_processes)
        num_virtual_flows = len(created_virtual_flows)
        if num_virtual_processes or num_virtual_flows:
            print("Created {} virtual processes and {} virtual flows for year {}".format(
                num_virtual_processes, num_virtual_flows, self._year_current))

            for v_id, virtual_process in created_virtual_processes.items():
                print("\t- Virtual process ID '{}'".format(v_id))

            for v_flow_id, virtual_flow in created_virtual_flows.items():
                print("\t- Virtual flow ID '{}'".format(v_flow_id))

            print("")

