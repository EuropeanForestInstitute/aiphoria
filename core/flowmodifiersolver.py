import sys
from typing import Union, Tuple, List, Dict, Any
import numpy as np
import core.flowsolver as FlowSolver
from core.datastructures import Flow, Scenario, FlowModifier
from core.parameters import ParameterScenarioType
from core.types import FunctionType
from core.logger import log


class FlowModifierSolver(object):
    class FlowChangeEntry(object):
        """
        Helper class for storing evaluated flow values
        """
        def __init__(self,
                     year: int = 0,
                     flow_id: str = None,
                     value: float = 0.0,
                     evaluated_share: float = 0.0,
                     evaluated_value: float = 0.0,
                     evaluated_offset: float = 0.0,
                     evaluated_share_offset: float = 0.0,
                     ):
            self._year = year
            self._flow_id = flow_id
            self._value = value
            self._evaluated_share = evaluated_share
            self._evaluated_value = evaluated_value
            self._evaluated_offset = evaluated_offset
            self._evaluated_share_offset = evaluated_share_offset

        def __str__(self) -> str:
            return "FlowChangeEntry: year={}, flow_id={}, value={}, evaluated_share={}, evaluated_value={}, evaluated_offset={}, evaluated_share_offset={}".format(
                self.year, self.flow_id, self.value, self.evaluated_share, self.evaluated_value, self.evaluated_offset,
                self.evaluated_share_offset)

        @property
        def year(self) -> int:
            return self._year

        @property
        def flow_id(self) -> str:
            return self._flow_id

        @property
        def value(self) -> float:
            return self._value

        @property
        def evaluated_share(self) -> float:
            return self._evaluated_share

        @property
        def evaluated_value(self) -> float:
            return self._evaluated_value

        @property
        def evaluated_offset(self) -> float:
            return self._evaluated_offset

        @property
        def evaluated_share_offset(self) -> float:
            return self._evaluated_share_offset

    class FlowErrorEntry(object):
        def __init__(self, year: int, total_outflows: float, required_outflows: float, flow_modifier_index: int):
            self._year = year
            self._outflows_total = total_outflows
            self._outflows_required = required_outflows
            self._flow_modifier_index = flow_modifier_index

        @property
        def year(self) -> int:
            """
            Get year

            :return: Year (int)
            """
            return self._year

        @property
        def outflows_total(self) -> float:
            """
            Get total outflows

            :return: Total outflows (float)
            """
            return self._outflows_total

        @property
        def outflows_required(self) -> float:
            """
            Get required outflows

            :return: Required outflows (float)
            """
            return self._outflows_required

        @property
        def outflows_missing(self) -> float:
            """
            Calculate missing outflows (total outflows - required outflows)

            :return: Missing outflows (float)
            """
            return self.outflows_total - self.outflows_required

        @property
        def flow_modifier_index(self) -> int:
            """
            Get flow modifier index causing the error

            :return: Flow modifier index (int)
            """
            return self._flow_modifier_index

    def __init__(self, flow_solver: FlowSolver, scenario_type: ParameterScenarioType):
        self._flow_solver: FlowSolver = flow_solver
        self._scenario_type: ParameterScenarioType = scenario_type

    def solve(self):
        if self._scenario_type == ParameterScenarioType.Unconstrained:
            log("Solving unconstrained scenario...")
            ok, errors = self._solve_unconstrained_scenario()
            if not ok:
                sys.stdout.flush()
                log("Errors in unconstrained scenario:", level="error")
                for error in errors:
                    print("\t" + error)
                log("Unconstrained scenario contained errors, stopping now...", level="error")

        if self._scenario_type == ParameterScenarioType.Constrained:
            log("Solving constrained scenario...")
            ok, errors = self._solve_constrained_scenario()
            if not ok:
                sys.stdout.flush()
                log("Errors in constrained scenario:", level="error")
                for error in errors:
                    print("\t" + error)
                log("Unconstrained scenario contained errors, stopping now...", level="error")

        log("Scenario solving done")
        # exit(-100)

    def _solve_unconstrained_scenario(self) -> Tuple[bool, List[str]]:
        # ***************************************************************************
        # * Solve unconstrained scenario                                            *
        # * Introduces virtual flows if detecting that processes do not have enough *
        # * outflows and does not stop execution                                    *
        # ***************************************************************************
        errors: List[str] = []
        flow_solver: FlowSolver = self._flow_solver
        scenario: Scenario = self._flow_solver.get_scenario()

        scenario_type = ParameterScenarioType.Unconstrained
        flow_solver._reset_evaluated_values = True

        # Evaluate new values for each flow modifier in the requested year range
        # and group flow modifiers by source process ID. This is needed when multiple
        # flow modifiers are affecting the same source process.
        source_process_id_to_flow_modifier_indices = {}
        flow_modifier_index_to_new_values = {}
        flow_modifier_index_to_new_offsets = {}
        flow_modifiers = scenario.scenario_definition.flow_modifiers
        for flow_modifier_index, flow_modifier in enumerate(flow_modifiers):
            new_values, new_offsets = self._calculate_new_flow_values(flow_modifier)
            flow_modifier_index_to_new_values[flow_modifier_index] = new_values
            flow_modifier_index_to_new_offsets[flow_modifier_index] = new_offsets
            source_process_id = flow_modifier.source_process_id
            if source_process_id not in source_process_id_to_flow_modifier_indices:
                source_process_id_to_flow_modifier_indices[source_process_id] = []
            source_process_id_to_flow_modifier_indices[source_process_id].append(flow_modifier_index)

        # Separate into entries that affect relative and absolute flows by
        # checking what type of flow (absolute/relative) flow_modifier is targeting.
        # This is needed because the FlowModifiers only affect the same type of flows
        # as the source-to-target flow is.
        has_errors = False
        for source_process_id, flow_modifier_indices in source_process_id_to_flow_modifier_indices.items():
            flow_modifier_indices_for_abs_flows = []
            flow_modifier_indices_for_rel_flows = []
            for flow_modifier_index in flow_modifier_indices:
                flow_modifier = flow_modifiers[flow_modifier_index]
                flow = flow_solver.get_flow(flow_modifier.target_flow_id, flow_modifier.start_year)
                if flow.is_unit_absolute_value:
                    flow_modifier_indices_for_abs_flows.append(flow_modifier_index)
                else:
                    flow_modifier_indices_for_rel_flows.append(flow_modifier_index)

            # Cache process total absolute and relative outflows for every year
            # before any changes applied. This is used when recalculating new flow share
            year_to_total_outflows_abs = {}
            year_to_total_outflows_rel = {}
            for year in scenario.scenario_data.years:
                # NOTE: Every year might not contain all process IDs to skip those years
                has_total_abs = False
                has_total_rel = False
                try:
                    year_to_total_outflows_abs[year] = flow_solver.get_process_outflows_total_abs(source_process_id, year)
                    has_total_abs = True
                except KeyError:
                    pass
                try:
                    year_to_total_outflows_rel[year] = flow_solver.get_process_outflows_total_rel(source_process_id, year)
                    has_total_rel = True
                except KeyError:
                    pass

                if not has_total_abs and not has_total_rel:
                    continue

            # Solve absolute flows and relative flows independently
            abs_flow_modifier_index_to_error_entry, abs_changeset = self._process_absolute_flows(
                source_process_id,
                flow_solver,
                flow_modifier_indices_for_abs_flows,
                flow_modifiers,
                flow_modifier_index_to_new_values,
                flow_modifier_index_to_new_offsets,
                scenario_type)

            rel_flow_modifier_index_to_error_entry, rel_changeset = self._process_relative_flows(
                source_process_id,
                flow_solver,
                flow_modifier_indices_for_rel_flows,
                flow_modifiers,
                flow_modifier_index_to_new_values,
                flow_modifier_index_to_new_offsets,
                scenario_type)

            # *************************************************************
            # * Apply changesets (order: absolute flows, relative flows)  *
            # * This order is needed because relative flow values depends *
            # * on the remaining process outflows after applying absolute *
            # * flows values                                              *
            # *************************************************************
            # Apply changes targeting absolute flows
            for flow_modifier_index, changeset in abs_changeset.items():
                flow_modifier = flow_modifiers[flow_modifier_index]
                entry: FlowModifierSolver.FlowChangeEntry
                for entry in changeset:
                    flow = flow_solver.get_flow(entry.flow_id, entry.year)
                    if flow.id == flow_modifier.target_flow_id:
                        # Apply calculated changes to source-to-target flow
                        # This is because that entry is always first in the list
                        # Overwrites the flow value
                        flow.value = entry.value
                        flow.evaluated_value = entry.evaluated_value
                        flow.evaluated_share = entry.evaluated_share
                    else:
                        # Apply calculated offset to evaluated value, these are all sibling flows
                        # or the target opposite flows
                        flow.value += entry.evaluated_offset
                        flow.evaluated_value += entry.evaluated_offset

            # Apply changes targeting relative flows
            for flow_modifier_index, changeset in rel_changeset.items():
                flow_modifier = flow_modifiers[flow_modifier_index]
                entry: FlowModifierSolver.FlowChangeEntry
                for entry in changeset:
                    flow = flow_solver.get_flow(entry.flow_id, entry.year)
                    if flow.id == flow_modifier.target_flow_id:
                        # Apply calculated changes to source-to-target flow
                        # This is because that entry is always first in the list
                        # Overwrites the flow share
                        flow.value = entry.value
                        flow.evaluated_value = entry.evaluated_value
                        flow.evaluated_share = entry.evaluated_share
                    else:
                        # Apply calculated offset to evaluated value, these are all sibling flows
                        # or the target opposite flows
                        total_outflows_rel = year_to_total_outflows_rel[entry.year]
                        new_evaluated_value = flow.evaluated_value + entry.evaluated_offset
                        new_value = new_evaluated_value / total_outflows_rel * 100.0
                        new_evaluated_share = new_value / 100.0

                        flow.value += entry.evaluated_share_offset
                        flow.evaluated_value = new_evaluated_value
                        flow.evaluated_share = new_evaluated_share

            if abs_flow_modifier_index_to_error_entry:
                # Errors in absolute flows: Unpack error entries and show errors but do not stop execution
                print("[Unconstrained scenario] Found issues in scenarios targeting absolute flows:")
                has_errors = True
                min_error_entry = None
                flow_modifier_index: int
                error_entry: FlowModifierSolver.FlowErrorEntry
                for flow_modifier_index, error_entry in abs_flow_modifier_index_to_error_entry.items():
                    if not min_error_entry:
                        min_error_entry = error_entry
                        continue

                    if error_entry.outflows_missing < min_error_entry.outflows_missing:
                        min_error_entry = error_entry

                if min_error_entry:
                    year = min_error_entry.year
                    total = min_error_entry.outflows_total
                    required = min_error_entry.outflows_required
                    missing = min_error_entry.outflows_missing
                    flow_modifier = flow_modifiers[min_error_entry.flow_modifier_index]

                    s = "Process '{}'".format(source_process_id)
                    s += " "
                    s += "does not have enough outflows for absolute flows in year {}".format(year)
                    s += " "
                    s += "(total={}, required={}, missing={})".format(total, required, missing)
                    s += " "
                    s += "(row number {})".format(flow_modifier.row_number)
                    print("\tERROR: {}".format(s))

            if rel_flow_modifier_index_to_error_entry:
                # All flow modifiers in rel_flow_modifier_index_to_error_entry-map points to same source process ID
                print("[Unconstrained scenario] Found issues in scenarios targeting relative flows:")
                has_errors = True
                min_error_entry = None
                flow_modifier_index: int
                error_entry: FlowModifierSolver.FlowErrorEntry
                for flow_modifier_index, error_entry in rel_flow_modifier_index_to_error_entry.items():
                    if not min_error_entry:
                        min_error_entry = error_entry
                        continue

                    if error_entry.outflows_missing < min_error_entry.outflows_missing:
                        min_error_entry = error_entry

                if min_error_entry:
                    year = min_error_entry.year
                    total = min_error_entry.outflows_total
                    required = min_error_entry.outflows_required
                    missing = min_error_entry.outflows_missing
                    flow_modifier = flow_modifiers[min_error_entry.flow_modifier_index]

                    s = "Process '{}'".format(source_process_id)
                    s += " "
                    s += "does not have enough outflows for relative flows in year {}".format(year)
                    s += " "
                    s += "(total={}, required={}, missing={})".format(total, required, missing)
                    s += " "
                    s += "(row number {})".format(flow_modifier.row_number)
                    print("\tERROR: {}".format(s))

            if has_errors:
                pass

        # NOTE: Clamp all flows to minimum of 0.0 to introduce virtual flows
        for year, flow_id_to_flow in flow_solver._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                if flow.value < 0.0:
                    flow.value = 0.0

        return not errors, errors

    def _solve_constrained_scenario(self) -> Tuple[bool, List[str]]:
        # ********************************************************************************
        # * Solve constrained scenario                                                   *
        # * Difference to unconstrained scenario is that no virtual flows are introduced *
        # * and execution stops if errors are found                                      *
        # ********************************************************************************
        errors: List[str] = []
        flow_solver: FlowSolver = self._flow_solver
        scenario: Scenario = self._flow_solver.get_scenario()

        scenario_type = ParameterScenarioType.Constrained
        flow_solver._reset_evaluated_values = True

        # Evaluate new values for each flow modifier in the requested year range
        # and group flow modifiers by source process ID. This is needed when multiple
        # flow modifiers are affecting the same source process.
        source_process_id_to_flow_modifier_indices = {}
        flow_modifier_index_to_new_values = {}
        flow_modifier_index_to_new_offsets = {}
        flow_modifiers = scenario.scenario_definition.flow_modifiers
        for flow_modifier_index, flow_modifier in enumerate(flow_modifiers):
            new_values, new_offsets = self._calculate_new_flow_values(flow_modifier)
            flow_modifier_index_to_new_values[flow_modifier_index] = new_values
            flow_modifier_index_to_new_offsets[flow_modifier_index] = new_offsets
            source_process_id = flow_modifier.source_process_id
            if source_process_id not in source_process_id_to_flow_modifier_indices:
                source_process_id_to_flow_modifier_indices[source_process_id] = []
            source_process_id_to_flow_modifier_indices[source_process_id].append(flow_modifier_index)

        # Separate into entries that affect relative and absolute flows by
        # checking what type of flow (absolute/relative) flow_modifier is targeting.
        # This is needed because the FlowModifiers only affect the same type of flows
        # as the source-to-target flow is.
        has_errors = False
        for source_process_id, flow_modifier_indices in source_process_id_to_flow_modifier_indices.items():
            flow_modifier_indices_for_abs_flows = []
            flow_modifier_indices_for_rel_flows = []
            for flow_modifier_index in flow_modifier_indices:
                flow_modifier = flow_modifiers[flow_modifier_index]
                flow = flow_solver.get_flow(flow_modifier.target_flow_id, flow_modifier.start_year)
                if flow.is_unit_absolute_value:
                    flow_modifier_indices_for_abs_flows.append(flow_modifier_index)
                else:
                    flow_modifier_indices_for_rel_flows.append(flow_modifier_index)

            # Cache process total absolute and relative outflows for every year
            # before any changes applied. This is used when recalculating new flow share
            year_to_total_outflows_abs = {}
            year_to_total_outflows_rel = {}
            for year in scenario.scenario_data.years:
                # NOTE: Every year might not contain all process IDs to skip those years
                has_total_abs = False
                has_total_rel = False
                try:
                    year_to_total_outflows_abs[year] = flow_solver.get_process_outflows_total_abs(source_process_id, year)
                    has_total_abs = True
                except KeyError:
                    pass
                try:
                    year_to_total_outflows_rel[year] = flow_solver.get_process_outflows_total_rel(source_process_id, year)
                    has_total_rel = True
                except KeyError:
                    pass

                if not has_total_abs and not has_total_rel:
                    continue

            # Solve absolute flows and relative flows independently
            abs_flow_modifier_index_to_error_entry, abs_changeset = self._process_absolute_flows(
                source_process_id,
                flow_solver,
                flow_modifier_indices_for_abs_flows,
                flow_modifiers,
                flow_modifier_index_to_new_values,
                flow_modifier_index_to_new_offsets,
                scenario_type)

            rel_flow_modifier_index_to_error_entry, rel_changeset = self._process_relative_flows(
                source_process_id,
                flow_solver,
                flow_modifier_indices_for_rel_flows,
                flow_modifiers,
                flow_modifier_index_to_new_values,
                flow_modifier_index_to_new_offsets,
                scenario_type)

            # *************************************************************
            # * Apply changesets (order: absolute flows, relative flows)  *
            # * This order is needed because relative flow values depends *
            # * on the remaining process outflows after applying absolute *
            # * flows values                                              *
            # *************************************************************
            # Apply changes targeting absolute flows
            for flow_modifier_index, changeset in abs_changeset.items():
                flow_modifier = flow_modifiers[flow_modifier_index]
                entry: FlowModifierSolver.FlowChangeEntry
                for entry in changeset:
                    flow = flow_solver.get_flow(entry.flow_id, entry.year)
                    if flow.id == flow_modifier.target_flow_id:
                        # Apply calculated changes to source-to-target flow
                        # This is because that entry is always first in the list
                        # Overwrites the flow value
                        flow.value = entry.value
                        flow.evaluated_value = entry.evaluated_value
                        flow.evaluated_share = entry.evaluated_share
                    else:
                        # Apply calculated offset to evaluated value, these are all sibling flows
                        # or the target opposite flows
                        flow.value += entry.evaluated_offset
                        flow.evaluated_value += entry.evaluated_offset

            # Apply changes targeting relative flows
            for flow_modifier_index, changeset in rel_changeset.items():
                flow_modifier = flow_modifiers[flow_modifier_index]
                entry: FlowModifierSolver.FlowChangeEntry
                for entry in changeset:
                    flow = flow_solver.get_flow(entry.flow_id, entry.year)
                    if flow.id == flow_modifier.target_flow_id:
                        # Apply calculated changes to source-to-target flow
                        # This is because that entry is always first in the list
                        # Overwrites the flow share
                        flow.value = entry.value
                        flow.evaluated_value = entry.evaluated_value
                        flow.evaluated_share = entry.evaluated_share
                    else:
                        # Apply calculated offset to evaluated value, these are all sibling flows
                        # or the target opposite flows
                        total_outflows_rel = year_to_total_outflows_rel[entry.year]
                        new_evaluated_value = flow.evaluated_value + entry.evaluated_offset
                        new_value = new_evaluated_value / total_outflows_rel * 100.0
                        new_evaluated_share = new_value / 100.0

                        flow.value += entry.evaluated_share_offset
                        flow.evaluated_value = new_evaluated_value
                        flow.evaluated_share = new_evaluated_share

            if abs_flow_modifier_index_to_error_entry:
                # Errors in absolute flows: Unpack error entries and show errors but do not stop execution
                print("[Constrained scenario] Found issues in scenarios targeting absolute flows:")
                has_errors = True
                min_error_entry = None
                flow_modifier_index: int
                error_entry: FlowModifierSolver.FlowErrorEntry
                for flow_modifier_index, error_entry in abs_flow_modifier_index_to_error_entry.items():
                    if not min_error_entry:
                        min_error_entry = error_entry
                        continue

                    if error_entry.outflows_missing < min_error_entry.outflows_missing:
                        min_error_entry = error_entry

                if min_error_entry:
                    year = min_error_entry.year
                    total = min_error_entry.outflows_total
                    required = min_error_entry.outflows_required
                    missing = min_error_entry.outflows_missing
                    flow_modifier = flow_modifiers[min_error_entry.flow_modifier_index]

                    s = "Process '{}'".format(source_process_id)
                    s += " "
                    s += "does not have enough outflows for absolute flows in year {}".format(year)
                    s += " "
                    s += "(total={}, required={}, missing={})".format(total, required, missing)
                    s += " "
                    s += "(row number {})".format(flow_modifier.row_number)
                    print("\tERROR: {}".format(s))

            if rel_flow_modifier_index_to_error_entry:
                # All flow modifiers in rel_flow_modifier_index_to_error_entry-map points to same source process ID
                print("[Constrained scenario] Found issues in scenarios targeting relative flows:")
                has_errors = True
                min_error_entry = None
                flow_modifier_index: int
                error_entry: FlowModifierSolver.FlowErrorEntry
                for flow_modifier_index, error_entry in rel_flow_modifier_index_to_error_entry.items():
                    if not min_error_entry:
                        min_error_entry = error_entry
                        continue

                    if error_entry.outflows_missing < min_error_entry.outflows_missing:
                        min_error_entry = error_entry

                if min_error_entry:
                    year = min_error_entry.year
                    total = min_error_entry.outflows_total
                    required = min_error_entry.outflows_required
                    missing = min_error_entry.outflows_missing
                    flow_modifier = flow_modifiers[min_error_entry.flow_modifier_index]

                    s = "Process '{}'".format(source_process_id)
                    s += " "
                    s += "does not have enough outflows for relative flows in year {}".format(year)
                    s += " "
                    s += "(total={}, required={}, missing={})".format(total, required, missing)
                    s += " "
                    s += "(row number {})".format(flow_modifier.row_number)
                    print("\tERROR: {}".format(s))

        if has_errors:
            # Stop execution of constrained solver
            log("Errors in Constrained scenario solver, stopping execution...", level="error")
            exit(-1)

        return not errors, errors

    def _get_process_outflow_siblings(self,
                                      process_id: str = None,
                                      flow_id: str = None,
                                      year: int = -1,
                                      only_same_type: bool = False,
                                      excluded_flow_ids: List[str] = None
                                      ) -> List[Flow]:
        """
        Get all sibling outflows for process ID and outflow ID.
        If only_same_type is True then return only outflows that are same type as flow_id.
        NOTE: Target flow (flow_id) is not included in the list of siblings.

        :param flow_id: Target Flow ID (excluded from results)
        :param year: Target year
        :param only_same_type: True to return only same type sibling outflows as flow_id, False returns all siblings.
        :param excluded_flow_ids: List of Flow IDs to exclude from siblings (optional)
        :return: List of Flows (List[Flow])
        """

        if excluded_flow_ids is None:
            excluded_flow_ids = []
        unique_excluded_flow_ids = set(excluded_flow_ids)

        all_outflows = {flow.id: flow for flow in self._flow_solver.get_process_outflows(process_id, year)}
        target_flow = all_outflows[flow_id]
        sibling_outflows = []
        for outflow_id, outflow in all_outflows.items():
            if outflow_id == flow_id:
                continue

            if outflow_id in unique_excluded_flow_ids:
                continue

            if only_same_type:
                if outflow.is_unit_absolute_value == target_flow.is_unit_absolute_value:
                    sibling_outflows.append(outflow)
            else:
                sibling_outflows.append(outflow)
        return sibling_outflows

    def _process_absolute_flows(self,
                                source_process_id: str,
                                flow_solver: FlowSolver,
                                flow_modifier_indices: List[int],
                                flow_modifiers: List[FlowModifier],
                                flow_modifier_index_to_new_values: Dict[int, List[float]],
                                flow_modifier_index_to_new_offsets: Dict[int, List[float]],
                                scenario_type: ParameterScenarioType
                                ) -> Tuple[Dict[int, FlowErrorEntry], Dict[int, List[FlowChangeEntry]]]:
        """
        Process absolute flows for flow modifier.

        :param source_process_id: Source Process ID
        :param flow_solver: FlowSolver
        :param flow_modifier_indices: List of flow modifier indices that affect absolute flows
        :param flow_modifiers: List of FlowModifiers
        :param flow_modifier_index_to_new_values: Mapping of flow modifier index to list of new values
        :param flow_modifier_index_to_new_offsets: Mapping of flow modifier index to list of offset values
        :return: Tuple (Dictionary (flow modifier index to FlowErrorEntry), Dictionary (flow modifier index to changeset)
        """
        # Flow modifier index to list of error entries
        flow_modifier_index_to_error_entry = {}

        # Flow modifier index to list of FlowChangeEntry-objects
        flow_modifier_index_to_changeset = {}

        # Flow modifier index to list of evaluated flow offset values
        flow_modifier_index_to_new_values_offset = {}

        # Flow modifier index to list of evaluated flow values
        flow_modifier_index_to_new_values_actual = {}

        # Year to total outflows required
        year_to_total_outflows_required = {}

        # Build yearly required outflows mapping
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            new_values_offset = flow_modifier_index_to_new_offsets[flow_modifier_index]
            new_values = flow_modifier_index_to_new_values[flow_modifier_index]
            flow_modifier_index_to_new_values_offset[flow_modifier_index] = new_values_offset
            flow_modifier_index_to_new_values_actual[flow_modifier_index] = new_values
            for year_index, year in enumerate(flow_modifier.get_year_range()):
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += new_values[year_index]

        # Store year to source process total absolute outflows before applying changes
        year_to_process_total_outflows = {}
        for flow_modifier_index in flow_modifier_index_to_new_values_actual:
            flow_modifier = flow_modifiers[flow_modifier_index]
            for year in flow_modifier.get_year_range():
                # Update the yearly total absolute outflows only once because it stays the
                # same for all flow modifiers
                if year in year_to_process_total_outflows:
                    continue

                year_to_process_total_outflows[year] = flow_solver.get_process_outflows_total_abs(source_process_id, year)

            # Check if there is enough total outflows from the source process to fulfill the flow modifier requirements
            # before applying the changes
            year_to_total_outflows_available = {}
            for year, total_outflows in year_to_process_total_outflows.items():
                total_outflows_required = year_to_total_outflows_required[year]
                total_outflows_available = total_outflows - total_outflows_required
                year_to_total_outflows_available[year] = total_outflows_available

            # Find entry with minimum value in list
            year_to_value = {year: value for year, value in year_to_total_outflows_available.items() if value < 0.0}
            if year_to_value:
                entry = min(year_to_value.items(), key=lambda x: x[1])
                year, value = entry

                # Create new error entry
                outflows_total = year_to_process_total_outflows[year]
                outflows_required = year_to_total_outflows_required[year]
                new_error_entry = FlowModifierSolver.FlowErrorEntry(year,
                                                                    outflows_total,
                                                                    outflows_required,
                                                                    flow_modifier_index)

                flow_modifier_index_to_error_entry[flow_modifier_index] = new_error_entry

        # Exit early if there is errors
        if scenario_type == ParameterScenarioType.Constrained and flow_modifier_index_to_error_entry:
            return flow_modifier_index_to_error_entry, flow_modifier_index_to_changeset

        # Apply changes to source to target flows
        year_to_total_outflows_required = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            new_values_offset = flow_modifier_index_to_new_offsets[flow_modifier_index]
            new_values = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            for year_index, year in enumerate(flow_modifier.get_year_range()):
                target_flow_id = flow_modifier.target_flow_id
                target_flow = flow_solver.get_flow(target_flow_id, year)

                value_offset = new_values_offset[year_index]
                value_actual = new_values[year_index]
                new_value = value_actual
                new_evaluated_share = 1.0
                new_evaluated_value = new_value * new_evaluated_share
                new_evaluated_offset = value_offset

                # Build evaluated offset mapping
                new_entry = FlowModifierSolver.FlowChangeEntry(year,
                                                               target_flow_id,
                                                               new_value,
                                                               new_evaluated_share,
                                                               new_evaluated_value,
                                                               new_evaluated_offset)

                if flow_modifier_index not in flow_modifier_index_to_changeset:
                    flow_modifier_index_to_changeset[flow_modifier_index] = []
                flow_modifier_index_to_changeset[flow_modifier_index].append(new_entry)

                # Recalculate year_to_total_outflows_required
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += target_flow.evaluated_value

        # Get list of all unique flow IDs used in all flow modifiers, these flows should be excluded from sibling flows
        excluded_flow_ids = set()
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]

            # Ignore source to target flow ID
            source_to_target_flow_id = flow_modifier.target_flow_id
            excluded_flow_ids.add(source_to_target_flow_id)

            # Ignore all opposite target flow IDs
            for flow_id in flow_modifier.opposite_target_process_ids:
                excluded_flow_ids.add(flow_id)

        # Convert unique list of excluded flow IDs back to list
        excluded_flow_ids = list(excluded_flow_ids)

        # Apply flow modifiers to opposite targets or to all same type sibling flows
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            year_range = flow_modifier.get_year_range()

            # Flow value offset from first year flow value
            new_values_offset = flow_modifier_index_to_new_values_offset[flow_modifier_index]
            if flow_modifier.has_opposite_targets:
                for year_index, year in enumerate(year_range):
                    value_offset = new_values_offset[year_index]
                    opposite_flow_share = 1.0 / len(flow_modifier.opposite_target_process_ids)
                    for opposite_target_process_id in flow_modifier.opposite_target_process_ids:
                        opposite_flow_id = Flow.make_flow_id(source_process_id, opposite_target_process_id)
                        opposite_flow = flow_solver.get_flow(opposite_flow_id, year)

                        # Calculate changes, create new FlowChangeEntry and append it to changeset
                        new_value = (opposite_flow.evaluated_value - value_offset) * opposite_flow_share
                        new_evaluated_share = 1.0
                        new_evaluated_value = new_value
                        new_evaluated_offset = -value_offset * opposite_flow_share
                        new_entry = FlowModifierSolver.FlowChangeEntry(year,
                                                                       opposite_flow_id,
                                                                       new_value,
                                                                       new_evaluated_share,
                                                                       new_evaluated_value,
                                                                       new_evaluated_offset)

                        flow_modifier_index_to_changeset[flow_modifier_index].append(new_entry)

            else:
                # *************************************************************************
                # * Apply changes to proportionally to all siblings outflows of same type *
                # *************************************************************************
                for year_index, year in enumerate(year_range):
                    # Get total absolute outflows
                    total_outflows_abs = year_to_process_total_outflows[year]
                    total_outflows_required = year_to_total_outflows_required[year]
                    total_outflows_available = total_outflows_abs - total_outflows_required
                    value_offset = new_values_offset[year_index]

                    # Get all same type sibling outflows (= outflows that start from same source process
                    # and are same type as the source to target flow)
                    sibling_outflows = self._get_process_outflow_siblings(source_process_id,
                                                                          flow_modifier.target_flow_id,
                                                                          year,
                                                                          only_same_type=True,
                                                                          excluded_flow_ids=excluded_flow_ids)

                    # Get total sibling outflows, used to check if there is enough outflows
                    # to fulfill the flow_modifier request
                    total_sibling_outflows = np.sum([flow.evaluated_value for flow in sibling_outflows])

                    # Calculate new sibling values and update sibling flows
                    for flow in sibling_outflows:
                        # Calculate changes, create new FlowChangeEntry and append it to changeset
                        sibling_flow_id = flow.id
                        new_value = 0.0
                        new_evaluated_share = 1.0
                        new_evaluated_value = 0.0
                        new_evaluated_offset = 0.0
                        if total_sibling_outflows > 0.0:
                            sibling_share = flow.evaluated_value / total_sibling_outflows
                            sibling_offset = -value_offset
                            new_value = (total_outflows_available * sibling_share) + sibling_offset * sibling_share
                            new_evaluated_share = 1.0
                            new_evaluated_value = new_value
                            new_evaluated_offset = sibling_offset * sibling_share

                        new_entry = FlowModifierSolver.FlowChangeEntry(year,
                                                                       sibling_flow_id,
                                                                       new_value,
                                                                       new_evaluated_share,
                                                                       new_evaluated_value,
                                                                       new_evaluated_offset)

                        flow_modifier_index_to_changeset[flow_modifier_index].append(new_entry)

        return flow_modifier_index_to_error_entry, flow_modifier_index_to_changeset

    def _process_relative_flows(self,
                                source_process_id: str,
                                flow_solver: FlowSolver,
                                flow_modifier_indices: List[int],
                                flow_modifiers: List[FlowModifier],
                                flow_modifier_index_to_new_values: Dict[int, List[float]],
                                flow_modifier_index_to_new_offsets: Dict[int, List[float]],
                                scenario_type: ParameterScenarioType
                                ) -> Tuple[Dict[int, FlowErrorEntry], Dict[int, List[FlowChangeEntry]]]:
        """
        Process relative flows for flow modifier.

        :param source_process_id: Source Process ID
        :param flow_solver: FlowSolver
        :param flow_modifier_indices: List of flow modifier indices that affect relative flows
        :param flow_modifiers: List of FlowModifiers
        :param flow_modifier_index_to_new_values: Mapping of flow modifier index to list of new values
        :param flow_modifier_index_to_new_offsets: Mapping of flow modifier index to list of offset values
        :return: Tuple (Dictionary (flow modifier index to FlowErrorEntry), Dictionary (flow modifier index to changeset))
        """
        # Flow modifier index to list of error entries
        flow_modifier_index_to_error_entry = {}

        # Flow modifier index to list of FlowChangeEntry-objects
        flow_modifier_index_to_changeset = {}

        # Flow modifier index to list of evaluated flow offset values
        flow_modifier_index_to_new_values_offset = {}

        # Flow modifier index to list of evaluated flow values
        flow_modifier_index_to_new_values_actual = {}

        # Year to total outflows required
        year_to_total_outflows_required = {}

        # Build yearly required outflows mapping
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            new_values_offset = flow_modifier_index_to_new_offsets[flow_modifier_index]
            new_values = flow_modifier_index_to_new_values[flow_modifier_index]
            flow_modifier_index_to_new_values_offset[flow_modifier_index] = new_values_offset
            flow_modifier_index_to_new_values_actual[flow_modifier_index] = new_values
            for year_index, year in enumerate(flow_modifier.get_year_range()):
                total_outflows_rel = flow_solver.get_process_outflows_total_rel(flow_modifier.source_process_id, year)
                evaluated_value = (new_values[year_index] / 100.0) * total_outflows_rel
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += evaluated_value

        # Store year to source process total relative outflows before applying changes
        year_to_process_total_outflows = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            for year in flow_modifier.get_year_range():
                # Update the yearly total relative outflows only once because it stays the
                # same for all flow modifiers
                if year in year_to_process_total_outflows:
                    continue

                year_to_process_total_outflows[year] = flow_solver.get_process_outflows_total_rel(source_process_id, year)

            # Check if there is enough total outflows from the source process to fulfill the flow modifier requirements
            # before applying the changes
            year_to_total_outflows_available = {}
            for year, total_outflows in year_to_process_total_outflows.items():
                total_outflows_required = year_to_total_outflows_required[year]
                total_outflows_available = total_outflows - total_outflows_required
                year_to_total_outflows_available[year] = total_outflows_available

            # Find entry with minimum value in list
            year_to_value = {year: value for year, value in year_to_total_outflows_available.items() if value < 0.0}
            if year_to_value:
                entry = min(year_to_value.items(), key=lambda x: x[1])
                year, value = entry

                # Create new error entry
                outflows_total = year_to_process_total_outflows[year]
                outflows_required = year_to_total_outflows_required[year]
                new_error_entry = FlowModifierSolver.FlowErrorEntry(year,
                                                                    outflows_total,
                                                                    outflows_required,
                                                                    flow_modifier_index)

                flow_modifier_index_to_error_entry[flow_modifier_index] = new_error_entry

        # Exit early if there is errors
        if scenario_type == ParameterScenarioType.Constrained and flow_modifier_index_to_error_entry:
            return flow_modifier_index_to_error_entry, flow_modifier_index_to_changeset

        # Apply changes to source to target flows
        year_to_total_outflows_required = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            new_values_offset = flow_modifier_index_to_new_offsets[flow_modifier_index]
            new_values = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            for year_index, year in enumerate(flow_modifier.get_year_range()):
                target_flow_id = flow_modifier.target_flow_id
                target_flow = flow_solver.get_flow(target_flow_id, year)
                total_outflows_rel = year_to_process_total_outflows[year]

                value_offset = new_values_offset[year_index]
                value_actual = new_values[year_index]
                new_value = value_actual
                new_evaluated_share = new_value / 100.0
                new_evaluated_value = new_evaluated_share * total_outflows_rel
                new_evaluated_offset = value_offset

                # Build evaluated offset mapping
                new_entry = FlowModifierSolver.FlowChangeEntry(year,
                                                               target_flow_id,
                                                               new_value,
                                                               new_evaluated_share,
                                                               new_evaluated_value,
                                                               new_evaluated_offset)

                if flow_modifier_index not in flow_modifier_index_to_changeset:
                    flow_modifier_index_to_changeset[flow_modifier_index] = []
                flow_modifier_index_to_changeset[flow_modifier_index].append(new_entry)

                # Recalculate year_to_total_outflows_required
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += target_flow.evaluated_value

        # Get list of all unique flow IDs used in all flow modifiers, these flows should be excluded from sibling flows
        excluded_flow_ids = set()
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]

            # Ignore source to target flow ID
            source_to_target_flow_id = flow_modifier.target_flow_id
            excluded_flow_ids.add(source_to_target_flow_id)

            # Ignore all opposite target flow IDs
            for flow_id in flow_modifier.opposite_target_process_ids:
                excluded_flow_ids.add(flow_id)

        # Convert unique list of excluded flow IDs back to list
        excluded_flow_ids = list(excluded_flow_ids)

        # Apply flow modifiers to opposite targets or to all same type sibling flows
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            year_range = flow_modifier.get_year_range()

            # Flow share offset from first year flow share
            new_values_actual = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            new_values_offset = flow_modifier_index_to_new_values_offset[flow_modifier_index]
            if flow_modifier.has_opposite_targets:
                for year_index, year in enumerate(year_range):
                    value_actual = new_values_actual[year_index]
                    value_offset = new_values_offset[year_index]
                    total_outflows_rel = year_to_process_total_outflows[year]
                    opposite_flow_share = 1.0 / len(flow_modifier.opposite_target_process_ids)
                    for opposite_target_process_id in flow_modifier.opposite_target_process_ids:
                        opposite_flow_id = Flow.make_flow_id(source_process_id, opposite_target_process_id)
                        opposite_flow = flow_solver.get_flow(opposite_flow_id, year)

                        # Calculate changes, create new FlowChangeEntry and append it to changeset
                        new_value = (opposite_flow.evaluated_value - value_offset) * opposite_flow_share
                        new_evaluated_share = new_value / total_outflows_rel
                        new_evaluated_value = new_value
                        new_evaluated_offset = -value_offset * opposite_flow_share
                        new_evaluated_share_offset = -(new_values_actual[year_index] - new_values_actual[0]) * opposite_flow_share
                        new_entry = FlowModifierSolver.FlowChangeEntry(year,
                                                                       opposite_flow_id,
                                                                       new_value,
                                                                       new_evaluated_share,
                                                                       new_evaluated_value,
                                                                       new_evaluated_offset,
                                                                       new_evaluated_share_offset)

                        flow_modifier_index_to_changeset[flow_modifier_index].append(new_entry)

            else:
                # *************************************************************************
                # * Apply changes to proportionally to all siblings outflows of same type *
                # *************************************************************************
                for year_index, year in enumerate(year_range):
                    # Get total relative outflows for process
                    total_outflows_rel = year_to_process_total_outflows[year]
                    total_outflows_required = year_to_total_outflows_required[year]
                    total_outflows_available = total_outflows_rel - total_outflows_required
                    value_offset = new_values_offset[year_index]

                    # Get all same type sibling outflows (= outflows that start from same source process
                    # and are same type as the source to target flow)
                    sibling_outflows = self._get_process_outflow_siblings(source_process_id,
                                                                          flow_modifier.target_flow_id,
                                                                          year,
                                                                          only_same_type=True,
                                                                          excluded_flow_ids=excluded_flow_ids)

                    # Get total sibling outflows, used to check if there is enough outflows
                    # to fulfill the flow_modifier request
                    total_sibling_outflows = np.sum([flow.evaluated_value for flow in sibling_outflows])

                    # Calculate new sibling values and update sibling flows
                    for flow in sibling_outflows:
                        # Calculate changes, create new FlowChangeEntry and append it to changeset
                        sibling_flow_id = flow.id
                        new_value = 0.0
                        new_evaluated_share = 1.0
                        new_evaluated_value = 0.0
                        new_evaluated_offset = 0.0
                        new_evaluated_share_offset = 0.0
                        if total_sibling_outflows > 0.0:
                            sibling_share = flow.evaluated_value / total_sibling_outflows
                            sibling_offset = -value_offset
                            new_value = (total_outflows_available * sibling_share) + sibling_offset * sibling_share
                            new_evaluated_share = 1.0
                            new_evaluated_value = new_value
                            new_evaluated_offset = sibling_offset * sibling_share
                            new_evaluated_share_offset = -(new_values_actual[year_index] - new_values_actual[0]) * sibling_share

                        new_entry = FlowModifierSolver.FlowChangeEntry(year,
                                                                       sibling_flow_id,
                                                                       new_value,
                                                                       new_evaluated_share,
                                                                       new_evaluated_value,
                                                                       new_evaluated_offset,
                                                                       new_evaluated_share_offset)

                        flow_modifier_index_to_changeset[flow_modifier_index].append(new_entry)

        return flow_modifier_index_to_error_entry, flow_modifier_index_to_changeset

    def _calculate_new_flow_values(self, flow_modifier: FlowModifier) -> Tuple[List[float], List[float]]:
        """
        Calculate new flow values for flow modifier.
        If flow_modifier targets absolute flow, returns tuple of (evaluated values, evaluated offset values)
        If flow_modifier targest relative flow, returns tuple of (evaluated flow shares, evaluated offset values)

        Does not modify the target flow.

        :param flow_modifier: Target FlowModifier
        :return: Tuple (list of evaluated flow values, list of evaluated flow value offsets)
        """

        flow_solver: FlowSolver = self._flow_solver
        year_range = flow_modifier.get_year_range()
        source_to_target_flow_id = flow_modifier.target_flow_id

        # ******************************************
        # * Create offset values for flow modifier *
        # ******************************************
        # Absolute flows: new evaluated flow value, relative flows: new evaluated flow share (0 - 100 range)
        new_values = [0.0 for _ in year_range]

        # Evaluated value from evaluated base value, always evaluated flow value (not share)
        new_offsets = [0.0 for _ in year_range]

        # Get total outflows (absolute + relative) for first year
        first_year = year_range[0]
        total_outflows_abs = flow_solver.get_process_outflows_total_abs(flow_modifier.source_process_id, first_year)
        total_outflows_rel = flow_solver.get_process_outflows_total_rel(flow_modifier.source_process_id, first_year)
        total_outflows = total_outflows_abs + total_outflows_rel
        first_year_flow = self._flow_solver.get_flow(source_to_target_flow_id, first_year)

        if flow_modifier.function_type == FunctionType.Constant:
            # NOTE: Constant replaces the values during the year range
            new_values = [flow_modifier.target_value for _ in year_range]

        # Change in value (delta)
        if flow_modifier.use_change_in_value:
            value_start = 0.0
            if first_year_flow.is_unit_absolute_value:
                # Absolute flow, use flow evaluated value as value_start
                value_start = first_year_flow.evaluated_value
            else:
                # Relative flow, use flow share as value_start
                value_start = first_year_flow.evaluated_share * 100.0

            if flow_modifier.function_type == FunctionType.Linear:
                new_values = np.linspace(start=0, stop=flow_modifier.change_in_value, num=len(year_range))

            if flow_modifier.function_type == FunctionType.Exponential:
                # NOTE: Is this function working properly with target value?
                new_values = np.logspace(start=0, stop=1, num=len(year_range))

            if flow_modifier.function_type == FunctionType.Sigmoid:
                # NOTE: Is this function working properly with target value?
                new_values = np.linspace(start=-flow_modifier.change_in_value,
                                         stop=flow_modifier.change_in_value,
                                         num=len(year_range))

                new_values = flow_modifier.change_in_value / (1.0 + np.exp(-new_values))

        # Target value (current to target)
        if flow_modifier.use_target_value:
            value_start = 0.0
            if first_year_flow.is_unit_absolute_value:
                # Absolute flow, use flow evaluated value as value_start
                value_start = first_year_flow.evaluated_value
            else:
                # Relative flow, use flow share as value_start
                value_start = first_year_flow.evaluated_share * 100.0

            if flow_modifier.function_type == FunctionType.Linear:
                new_values = np.linspace(start=value_start, stop=flow_modifier.target_value, num=len(year_range))

            if flow_modifier.function_type == FunctionType.Exponential:
                new_values = np.logspace(start=0, stop=1, num=len(year_range))

            if flow_modifier.function_type == FunctionType.Sigmoid:
                new_values = np.linspace(start=-flow_modifier.change_in_value,
                                         stop=flow_modifier.change_in_value,
                                         num=len(year_range))

                new_values = flow_modifier.change_in_value / (1.0 + np.exp(-new_values))

        # *******************************************************************************
        # * Calculate target values for flow modifier from start year and offset values *
        # *******************************************************************************
        for year_index, year in enumerate(year_range):
            base_value = first_year_flow.value
            base_evaluated_value = first_year_flow.evaluated_value
            base_evaluated_share = first_year_flow.evaluated_share

            # Absolute flow
            if first_year_flow.is_unit_absolute_value:
                if flow_modifier.is_change_type_value:
                    # Change by absolute value, either delta change or move toward target value
                    if flow_modifier.use_change_in_value:
                        # Increase/decrease by absolute value
                        offset = new_values[year_index]
                        new_values[year_index] = base_evaluated_value + offset

                        # Calculate evaluated offset from base evaluated value
                        new_offsets[year_index] = offset

                    if flow_modifier.use_target_value:
                        # Move toward absolute target value each year
                        offset = new_values[year_index]
                        new_values[year_index] = offset

                        # Calculate evaluated offset from base evaluated value
                        new_offsets[year_index] = offset - base_evaluated_value

                if flow_modifier.is_change_type_proportional:
                    # Proportional/percentual change of value, use delta change only
                    offset = new_values[year_index]
                    new_values[year_index] = base_evaluated_value + base_evaluated_value * offset / 100.0

                    # Calculate evaluated offset from base evaluated value
                    new_offsets[year_index] = base_evaluated_value * offset / 100.0

            # Relative flow
            else:
                if flow_modifier.use_change_in_value:
                    offset = new_values[year_index]
                    new_values[year_index] = base_value + base_evaluated_share * offset

                    # Calculate evaluated offset from base evaluated value
                    new_offsets[year_index] = base_evaluated_value * offset / 100.0

                if flow_modifier.use_target_value:
                    offset = new_values[year_index]
                    new_values[year_index] = offset

                    # Calculate evaluated offset from new flow share
                    new_offset = offset - base_evaluated_share * 100
                    new_evaluated_offset = (new_offset / 100.0) * total_outflows
                    new_offsets[year_index] = new_evaluated_offset

        return new_values, new_offsets
