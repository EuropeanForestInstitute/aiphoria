import sys
from typing import Union, Tuple, List, Dict
import numpy as np
import core.flowsolver as FlowSolver
from core.datastructures import Flow, Scenario, FlowModifier
from core.parameters import ParameterScenarioType
from core.types import FunctionType
from core.logger import log


class FlowModifierSolver(object):
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

    def _solve_unconstrained_scenario(self) -> Tuple[bool, List[str]]:
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
        flow_modifiers = scenario.scenario_definition.flow_modifiers
        for flow_modifier_index, flow_modifier in enumerate(flow_modifiers):
            new_values = self._calculate_new_flow_values(flow_modifier)
            flow_modifier_index_to_new_values[flow_modifier_index] = new_values

            source_process_id = flow_modifier.source_process_id
            if source_process_id not in source_process_id_to_flow_modifier_indices:
                source_process_id_to_flow_modifier_indices[source_process_id] = []
            source_process_id_to_flow_modifier_indices[source_process_id].append(flow_modifier_index)

        # Separate into entries that affect relative and absolute flows by
        # checking what type of flow (absolute/relative) flow_modifier is targeting.
        # This is needed because the FlowModifiers only affect the same type of flows
        # as the source-to-target flow is.
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

            self._process_absolute_flows(source_process_id,
                                         flow_solver,
                                         flow_modifier_indices_for_abs_flows,
                                         flow_modifiers,
                                         flow_modifier_index_to_new_values,
                                         scenario_type)

            self._process_relative_flows(source_process_id,
                                         flow_solver,
                                         flow_modifier_indices_for_rel_flows,
                                         flow_modifiers,
                                         flow_modifier_index_to_new_values,
                                         scenario_type)

            return not errors, errors

    def _solve_constrained_scenario(self) -> Tuple[bool, List[str]]:
        log("Constrained scenario solving not yet implemented, using Unconstrained-mode now", level="error")
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
        flow_modifiers = scenario.scenario_definition.flow_modifiers
        for flow_modifier_index, flow_modifier in enumerate(flow_modifiers):
            new_values = self._calculate_new_flow_values(flow_modifier)
            flow_modifier_index_to_new_values[flow_modifier_index] = new_values

            source_process_id = flow_modifier.source_process_id
            if source_process_id not in source_process_id_to_flow_modifier_indices:
                source_process_id_to_flow_modifier_indices[source_process_id] = []
            source_process_id_to_flow_modifier_indices[source_process_id].append(flow_modifier_index)

        # Separate into entries that affect relative and absolute flows by
        # checking what type of flow (absolute/relative) flow_modifier is targeting.
        # This is needed because the FlowModifiers only affect the same type of flows
        # as the source-to-target flow is.
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

            self._process_absolute_flows(source_process_id,
                                         flow_solver,
                                         flow_modifier_indices_for_abs_flows,
                                         flow_modifiers,
                                         flow_modifier_index_to_new_values,
                                         scenario_type)

            self._process_relative_flows(source_process_id,
                                         flow_solver,
                                         flow_modifier_indices_for_rel_flows,
                                         flow_modifiers,
                                         flow_modifier_index_to_new_values,
                                         scenario_type)

            return not errors, errors

    def _make_flow_id(self, source_process_id: str, target_process_id: str) -> str:
        """
        Make flow ID.
        :param source_process_id: Source Process ID
        :param target_process_id: Target Process ID
        :return: Flow ID
        """
        return "{} {}".format(source_process_id, target_process_id)

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

    def _process_absolute_flows(self, source_process_id: str,
                                flow_solver: FlowSolver,
                                flow_modifier_indices: List[int],
                                flow_modifiers: List[FlowModifier],
                                flow_modifier_index_to_new_values: Dict[int, List[float]],
                                scenario_type: ParameterScenarioType
                                ) -> None:
        """
        Process absolute flows for flow modifier.

        :param source_process_id: Source Process ID
        :param flow_solver: FlowSolver
        :param flow_modifier_indices: List of flow modifier indices that affect absolute flows
        :param flow_modifiers: List of FlowModifiers
        :param flow_modifier_index_to_new_values: Mapping of flow modifier index to list of new values
        :return: None
        """

        # TODO: Implement handling of constrained scenarios here, now targeting only Unconstrained

        flow_modifier_index_to_new_values_offset = {}
        flow_modifier_index_to_new_values_actual = {}
        year_to_total_outflows_required = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            new_values = flow_modifier_index_to_new_values[flow_modifier_index]
            year_range = flow_modifier.get_year_range()
            first_year_flow = flow_solver.get_flow(flow_modifier.target_flow_id, year_range[0])
            base_value = first_year_flow.evaluated_value

            # new_values_offset = list of evaluated flow value offset
            # new_values_actual = list of evaluated flow values
            new_values_offset = [value - base_value for value in new_values]
            new_values_actual = [value for value in new_values]
            flow_modifier_index_to_new_values_offset[flow_modifier_index] = new_values_offset
            flow_modifier_index_to_new_values_actual[flow_modifier_index] = new_values_actual
            for year_index, year in enumerate(year_range):
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += new_values_actual[year_index]

        # Store year to source process total absolute outflows before applying changes
        has_errors = False
        year_to_process_total_outflows = {}
        for flow_modifier_index in flow_modifier_index_to_new_values_actual:
            flow_modifier = flow_modifiers[flow_modifier_index]
            year_range = flow_modifier.get_year_range()
            for year in year_range:
                if year not in year_to_process_total_outflows:
                    # Update the yearly total absolute outflows only once because it stays the
                    # same for all flow modifiers
                    year_to_process_total_outflows[year] = flow_solver.get_process_outflows_total_abs(source_process_id, year)

            # Check if there is enough total outflows from the source process to fulfill the flow modifier requirements
            # before applying the changes
            # Check if there is enough total outflows from the source process to fulfill the flow modifier requirements
            # before applying the changes
            errors = []
            for year, total_outflows in year_to_process_total_outflows.items():
                total_outflows_required = year_to_total_outflows_required[year]
                total_outflows_available = total_outflows - total_outflows_required
                if total_outflows_available < 0.0:
                    s = "INFO: Process '{}' does not have enough outflows for absolute flows in year {} (required={}, available={})".format(
                        source_process_id, year, total_outflows_required, total_outflows)
                    errors.append(s)

            if errors:
                has_errors = True
                print("Following issues found when processing flow modifier in row {} (flow '{}'):".format(
                    flow_modifier.row_number, flow_modifier.target_flow_id))
                for error in errors:
                    print("\t{}".format(error))
                print("")

        # if has_errors and scenario_type == ParameterScenarioType.Constrained:
        #     raise Exception()

        # Apply changes to source to target flows
        year_to_total_outflows_required = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            year_range = flow_modifier.get_year_range()
            new_values_actual = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            for year_index, year in enumerate(year_range):
                flow = flow_solver.get_flow(flow_modifier.target_flow_id, year)

                # Evaluated flow share
                value_actual = new_values_actual[year_index]
                new_value = value_actual
                new_evaluated_share = 1.0
                new_evaluated_value = new_value * new_evaluated_share
                flow.value = new_value
                flow.evaluated_share = new_evaluated_share
                flow.evaluated_value = new_evaluated_value

                # Recalculate year_to_total_outflows_required
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += flow.evaluated_value

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
            new_values_offset = flow_modifier_index_to_new_values_offset[flow_modifier_index]
            new_values_actual = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            if flow_modifier.has_opposite_targets:
                for year_index, year in enumerate(year_range):
                    value_offset = new_values_offset[year_index]
                    total_outflows_abs = year_to_process_total_outflows[year]
                    opposite_flow_share = 1.0 / len(flow_modifier.opposite_target_process_ids)
                    for opposite_target_process_id in flow_modifier.opposite_target_process_ids:
                        opposite_flow_id = self._make_flow_id(source_process_id, opposite_target_process_id)
                        opposite_flow = flow_solver.get_flow(opposite_flow_id, year)

                        new_value = opposite_flow.value - value_offset
                        new_evaluated_share = 1.0
                        new_evaluated_value = new_evaluated_share * total_outflows_abs
                        opposite_flow.value = new_value * opposite_flow_share
                        opposite_flow.evaluated_share = new_evaluated_share * opposite_flow_share
                        opposite_flow.evaluated_value = new_evaluated_value * opposite_flow_share

            else:
                # *************************************************************************
                # * Apply changes to proportionally to all siblings outflows of same type *
                # *************************************************************************
                errors = []
                for year_index, year in enumerate(year_range):
                    # Get total absolute outflows
                    total_outflows_abs = year_to_process_total_outflows[year]
                    total_outflows_required = year_to_total_outflows_required[year]
                    total_outflows_available = total_outflows_abs - total_outflows_required

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
                    source_to_target_flow = flow_solver.get_flow(flow_modifier.target_flow_id, year)
                    required_flow_value = source_to_target_flow.evaluated_value
                    if total_outflows_available < 0.0:
                        # Total of all sibling flows is not enough to cover the change in value
                        s = "INFO: Not enough absolute outflows to fill flow modifier in row {} for year {}".format(
                            flow_modifier.row_number, year)
                        errors.append(s)

                        s = "INFO: Total outflows in process '{}' = {}, flow '{}' required={}, available to sibling flows = {}".format(
                            source_process_id, total_outflows_abs, source_to_target_flow.id, required_flow_value,
                            total_outflows_available)
                        errors.append(s)

                    # Calculate new sibling values and update sibling flows
                    for flow in sibling_outflows:
                        # Check if dividing by zero, default to 0.0 in that case
                        new_sibling_value = 0.0
                        if total_sibling_outflows > 0.0:
                            sibling_share = flow.value / total_sibling_outflows
                            new_sibling_value = sibling_share * total_outflows_available

                        flow.value = new_sibling_value
                        flow.evaluated_value = new_sibling_value

                if errors:
                    print("Following issues found when processing flow modifier in row {}:".format(flow_modifier.row_number))
                    for error in errors:
                        print("\t{}".format(error))
                    print("")

        # NOTE: Clamp all flows to minimum of 0.0 to introduce virtual flows
        for year, flow_id_to_flow in flow_solver._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                if flow.value < 0.0:
                    flow.value = 0.0

    def _process_relative_flows(self, source_process_id: str,
                                flow_solver: FlowSolver,
                                flow_modifier_indices: List[int],
                                flow_modifiers: List[FlowModifier],
                                flow_modifier_index_to_new_values: Dict[int, List[float]],
                                scenario_type: ParameterScenarioType
                                ) -> None:
        """
        Process relative flows for flow modifier.

        :param source_process_id: Source Process ID
        :param flow_solver: FlowSolver
        :param flow_modifier_indices: List of flow modifier indices that affect relative flows
        :param flow_modifiers: List of FlowModifiers
        :param flow_modifier_index_to_new_values: Mapping of flow modifier index to list of new values
        :return:
        """

        # TODO: Implement handling of constrained scenarios here, now targeting only Unconstrained

        flow_modifier_index_to_new_values_offset = {}
        flow_modifier_index_to_new_values_actual = {}
        year_to_total_outflows_required = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            new_values = flow_modifier_index_to_new_values[flow_modifier_index]
            year_range = flow_modifier.get_year_range()
            first_year_flow = flow_solver.get_flow(flow_modifier.target_flow_id, year_range[0])
            base_value = first_year_flow.evaluated_share * 100.0

            # new_values_offset = list of flow share offsets
            # new_values_actual = list of evaluated flow shares
            new_values_offset = [value - base_value for value in new_values]
            new_values_actual = [value for value in new_values]
            flow_modifier_index_to_new_values_offset[flow_modifier_index] = new_values_offset
            flow_modifier_index_to_new_values_actual[flow_modifier_index] = new_values_actual
            for year_index, year in enumerate(year_range):
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += new_values_actual[year_index]

        # Store year to source process total relative outflows before applying changes
        has_errors = False
        year_to_process_total_outflows = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            year_range = flow_modifier.get_year_range()
            for year in year_range:
                if year not in year_to_process_total_outflows:
                    # Update the yearly total relative outflows only once because it stays the
                    # same for all flow modifiers
                    year_to_process_total_outflows[year] = flow_solver.get_process_outflows_total_rel(source_process_id, year)

            # Check if there is enough total outflows from the source process to fulfill the flow modifier requirements
            # before applying the changes
            errors = []
            for year, total_outflows in year_to_process_total_outflows.items():
                total_outflows_required = year_to_total_outflows_required[year]
                total_outflows_available = total_outflows - total_outflows_required
                if total_outflows_available < 0.0:
                    s = "INFO: Process '{}' does not have enough outflows for relative flows in year {} (required={}, available={})".format(
                        source_process_id, year, total_outflows_required, total_outflows)
                    errors.append(s)

            if errors:
                has_errors = True
                print("Following issues found when processing flow modifier in row {} (flow '{}'):".format(
                    flow_modifier.row_number, flow_modifier.target_flow_id))
                for error in errors:
                    print("\t{}".format(error))
                print("")

        # if has_errors and scenario_type == ParameterScenarioType.Constrained:
        #     raise Exception()

        # Apply changes to source to target flows
        year_to_total_outflows_required = {}
        for flow_modifier_index in flow_modifier_indices:
            flow_modifier = flow_modifiers[flow_modifier_index]
            year_range = flow_modifier.get_year_range()
            new_values_actual = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            for year_index, year in enumerate(year_range):
                flow = flow_solver.get_flow(flow_modifier.target_flow_id, year)
                total_outflows_rel = year_to_process_total_outflows[year]

                # Evaluated flow share
                value_actual = new_values_actual[year_index]
                new_value = value_actual
                new_evaluated_share = new_value / 100.0
                new_evaluated_value = new_evaluated_share * total_outflows_rel
                flow.value = new_value
                flow.evaluated_share = new_evaluated_share
                flow.evaluated_value = new_evaluated_value

                # Recalculate year_to_total_outflows_required
                if year not in year_to_total_outflows_required:
                    year_to_total_outflows_required[year] = 0.0
                year_to_total_outflows_required[year] += flow.evaluated_value

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
            new_values_offset = flow_modifier_index_to_new_values_offset[flow_modifier_index]
            new_values_actual = flow_modifier_index_to_new_values_actual[flow_modifier_index]
            if flow_modifier.has_opposite_targets:
                for year_index, year in enumerate(year_range):
                    value_offset = new_values_offset[year_index]
                    total_outflows_rel = year_to_process_total_outflows[year]
                    opposite_flow_share = 1.0 / len(flow_modifier.opposite_target_process_ids)
                    for opposite_target_process_id in flow_modifier.opposite_target_process_ids:
                        opposite_flow_id = self._make_flow_id(source_process_id, opposite_target_process_id)
                        opposite_flow = flow_solver.get_flow(opposite_flow_id, year)
                        new_value = opposite_flow.value - value_offset
                        new_evaluated_share = new_value / 100.0
                        new_evaluated_value = new_evaluated_share * total_outflows_rel
                        opposite_flow.value = new_value * opposite_flow_share
                        opposite_flow.evaluated_share = new_evaluated_share * opposite_flow_share
                        opposite_flow.evaluated_value = new_evaluated_value * opposite_flow_share

            else:
                # *************************************************************************
                # * Apply changes to proportionally to all siblings outflows of same type *
                # *************************************************************************
                for year_index, year in enumerate(year_range):
                    # Get total relative outflows for process
                    total_outflows_rel = year_to_process_total_outflows[year]
                    total_outflows_required = year_to_total_outflows_required[year]
                    total_outflows_available = total_outflows_rel - total_outflows_required

                    # Get all same type sibling outflows (= outflows that start from same source process
                    # and are same type as the source to target flow)
                    sibling_outflows = self._get_process_outflow_siblings(source_process_id,
                                                                          flow_modifier.target_flow_id,
                                                                          year,
                                                                          only_same_type=True,
                                                                          excluded_flow_ids=excluded_flow_ids)

                    # Get total sibling outflows, used to check if there is enough outflows
                    # to fulfill the flow_modifier request
                    total_sibling_share = np.sum([flow.evaluated_value for flow in sibling_outflows])
                    source_to_target_flow = flow_solver.get_flow(flow_modifier.target_flow_id, year)
                    required_flow_value = source_to_target_flow.evaluated_value
                    if total_outflows_available < 0.0:
                        # Total of all sibling flows is not enough to cover the change in value
                        print("total_other_outflows not able to support request flow_modifier amount")
                        print("Requested={}, available={}, missing={}".format(required_flow_value,
                                                                              total_outflows_rel,
                                                                              abs(total_outflows_available)))

                    for flow in sibling_outflows:
                        # Check if dividing by zero, default to 0.0 in that case
                        new_sibling_value = 0.0
                        new_sibling_share = 0.0
                        if total_sibling_share > 0.0:
                            sibling_share_factor = flow.value / total_sibling_share
                            new_sibling_value = sibling_share_factor * total_outflows_available
                            new_sibling_share = (new_sibling_value / total_outflows_rel) * 100.0

                        flow.value = new_sibling_share
                        flow.evaluated_value = new_sibling_value

        # NOTE: Clamp all flows to minimum of 0.0 to introduce virtual flows
        for year, flow_id_to_flow in flow_solver._year_to_flow_id_to_flow.items():
            for flow_id, flow in flow_id_to_flow.items():
                if flow.value < 0.0:
                    flow.value = 0.0

        # exit(-1)

    def _calculate_new_flow_values(self, flow_modifier: FlowModifier):
        """
        Calculate new flow values for flow modifier.
        If flow_modifier targets absolute flow, returns list of evaluated values.
        If flow_modifier targest relative flow, returns list of evaluated flow shares.

        Does not modify the target flow.

        :param flow_modifier: Target FlowModifier
        :return: List of evaluated flow values
        """
        flow_solver: FlowSolver = self._flow_solver
        year_range = flow_modifier.get_year_range()
        source_to_target_flow_id = flow_modifier.target_flow_id

        # ******************************************
        # * Create offset values for flow modifier *
        # ******************************************
        new_values = []
        if flow_modifier.function_type == FunctionType.Constant:
            # NOTE: Constant replaces the values during the year range
            new_values = [flow_modifier.target_value for _ in year_range]

        # Change in value (delta)
        if flow_modifier.use_change_in_value:
            first_year_flow = self._flow_solver.get_flow(source_to_target_flow_id, year_range[0])

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
            first_year_flow = self._flow_solver.get_flow(source_to_target_flow_id, year_range[0])

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
            first_year_flow = flow_solver.get_flow(source_to_target_flow_id, year_range[0])
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
                        new_flow_value = base_evaluated_value + offset
                        new_values[year_index] = new_flow_value

                    if flow_modifier.use_target_value:
                        # Move toward absolute target value each year
                        offset = new_values[year_index]
                        new_flow_value = offset
                        new_values[year_index] = new_flow_value

                if flow_modifier.is_change_type_proportional:
                    # Proportional/percentual change of value, use delta change only
                    offset = new_values[year_index]
                    new_flow_value = base_evaluated_value + (base_evaluated_value * offset / 100.0)
                    new_values[year_index] = new_flow_value

            # Relative flow
            else:
                if flow_modifier.use_change_in_value:
                    offset = new_values[year_index]
                    new_flow_share = base_value + base_evaluated_share * offset
                    new_values[year_index] = new_flow_share

                if flow_modifier.use_target_value:
                    offset = new_values[year_index]
                    new_flow_share = offset
                    new_values[year_index] = new_flow_share

        return new_values
