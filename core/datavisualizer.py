import json
import os
import webbrowser
from typing import List, Dict, Any

import plotly.graph_objects as go
from PIL import Image

from core.datastructures import Scenario, Color
from core.parameters import ParameterName


class DataVisualizer(object):
    def __init__(self):
        pass

    def build_and_show(self, scenarios: List[Scenario],
                       visualizer_params: dict,
                       model_params: dict,
                       combine_to_one_file: bool = False) -> None:
        """
        Build and show the scenarios in the browser.

        :param scenarios: List of Scenario-objects
        :param visualizer_params: Dictionary of visualizer parameters
        :param model_params: Dictionary of model parameters (refer to Builder.py / build_results)
        :param combine_to_one_file: Combine multiple scenarios to one output file (default: False)
        :return: None
        """

        scenario_name_to_info = {}  # Scenario name to info
        scenario_name_to_data = {}  # Scenario name to year to data
        for scenario in scenarios:
            scenario_name_to_info[scenario.name] = self._build_scenario_info(scenario)
            scenario_name_to_data[scenario.name] = self._build_scenario_year_to_data(scenario, visualizer_params)

        if combine_to_one_file:
            # NOTE: Implement for the next version
            print("Combine to one file not implemented yet")

        else:
            # Build separate files for each scenario
            for scenario_name in scenario_name_to_data:
                # Generate HTML file for scenario
                scenario_info = scenario_name_to_info[scenario_name]
                scenario_year_to_data = scenario_name_to_data[scenario_name]

                html = self._build_scenario_graph(scenario_name,
                                                  scenario_info,
                                                  scenario_year_to_data,
                                                  visualizer_params)

                output_path = os.path.join(model_params[ParameterName.OutputPath], scenario_name)
                output_filename = "{}_sankey.html".format(scenario_name)
                abs_path_to_file = os.path.join(output_path, output_filename)

                with open(abs_path_to_file, "w", encoding="utf-8") as fs:
                    fs.write(html)

                if model_params[ParameterName.ShowPlots]:
                    webbrowser.open("file://" + os.path.realpath(abs_path_to_file))

    def _build_scenario_year_to_data(self, scenario: Scenario, params: Dict):
        flow_solver = scenario.flow_solver

        small_node_threshold = params["small_node_threshold"]
        process_transformation_stage_colors = params["process_transformation_stage_colors"]
        virtual_process_graph_labels = params["virtual_process_graph_labels"]
        flow_alpha = params["flow_alpha"]
        virtual_process_color = params["virtual_process_color"]
        virtual_flow_color = params["virtual_flow_color"]

        # Baseline value name and unit names are used for flow data
        baseline_value_name = scenario.model_params[ParameterName.BaselineValueName]
        baseline_unit_name = scenario.model_params[ParameterName.BaselineUnitName]

        # Check if all transformation stages have defined color
        unique_transformation_stages = set()
        year_to_process_to_flows = flow_solver.get_year_to_process_to_flows()
        first_year = list(year_to_process_to_flows.keys())[0]
        for process in year_to_process_to_flows[first_year]:
            unique_transformation_stages.add(process.transformation_stage)

        # Build colors for missing transformation stages or create default color palette
        self._build_default_transformation_stage_colors(unique_transformation_stages,
                                                        process_transformation_stage_colors)

        year_to_data = {}
        year_to_process_to_flows = flow_solver.get_year_to_process_to_flows()
        for year, process_to_flows in year_to_process_to_flows.items():
            year_to_data[year] = {}

            # Per year data
            process_id_to_index = {}
            for index, process in enumerate(process_to_flows):
                process_id_to_index[process.id] = index

            # Per year data of nodes and links for graph
            year_node_labels = []
            year_sources = []
            year_targets = []
            year_node_colors = []
            year_node_positions_x = []
            year_node_positions_y = []
            year_node_custom_data = []
            year_link_values = []
            year_link_colors = []
            year_link_custom_data = []

            for index, process in enumerate(process_to_flows):
                node_label = process.id + "({})".format(process.transformation_stage)
                if process.label_in_graph:
                    node_label = process.label_in_graph

                # Use virtual process color by default
                node_color = virtual_process_color
                if not process.is_virtual:
                    node_color = process_transformation_stage_colors[process.transformation_stage]
                else:
                    # Check if there is a new label for virtual process
                    if process.id in virtual_process_graph_labels:
                        node_label = virtual_process_graph_labels[process.id]

                year_node_labels.append(node_label)
                year_node_colors.append(node_color)
                year_node_positions_x.append(process.position_x)
                year_node_positions_y.append(process.position_y)

                inflows = process_to_flows[process]["in"]
                outflows = process_to_flows[process]["out"]

                # Calculate total inflows and total outflows for Process
                total_inflows = sum([flow.evaluated_value for flow in inflows])
                total_outflows = sum([flow.evaluated_value for flow in outflows])
                for flow in outflows:
                    if flow.source_process_id not in process_id_to_index:
                        print("Source {} not found in process_id_to_index!".format(flow.source_process_id))
                        continue

                    if flow.target_process_id not in process_id_to_index:
                        print("Target {} not found in process_id_to_index!".format(flow.target_process_id))
                        continue

                    source_index = process_id_to_index[flow.source_process_id]
                    target_index = process_id_to_index[flow.target_process_id]
                    year_sources.append(source_index)
                    year_targets.append(target_index)
                    year_link_values.append(flow.evaluated_value)

                    link_color = ""
                    if flow.is_virtual:
                        link_color = virtual_flow_color.lstrip("#")
                        r, g, b = tuple(int(link_color[i:i+2], 16) for i in (0, 2, 4))
                        link_color = "rgba({},{},{},{})".format(r, g, b, flow_alpha)
                    else:
                        link_color = process_transformation_stage_colors[process.transformation_stage]
                        link_color = link_color.lstrip("#")
                        r, g, b = tuple(int(link_color[i:i+2], 16) for i in (0, 2, 4))
                        link_color = "rgba({},{},{},{})".format(r / 255, g / 255, b / 255, flow_alpha)

                    year_link_colors.append(link_color)

                    # Custom data for link
                    year_link_custom_data.append(
                        dict(
                            is_visible=True,
                            is_virtual=flow.is_virtual,
                            evaluated_value=flow.evaluated_value,
                            evaluated_share=flow.evaluated_share,
                            baseline_unit_name=baseline_unit_name,
                            baseline_value_name=baseline_value_name,
                            unit=flow.unit,
                            indicator_names=flow.get_indicator_names(),
                            evaluated_indicator_values=flow.get_all_evaluated_values()
                        )
                    )

                # Custom data for node
                year_node_custom_data.append(
                    dict(
                        node_id=process.id,
                        is_visible=True,
                        is_virtual=process.is_virtual,
                        total_inflows=total_inflows,
                        total_outflows=total_outflows,
                        has_stock=process.stock_lifetime > 0,
                        transformation_stage=process.transformation_stage,
                        stock=dict(
                            distribution_type=process.stock_distribution_type,
                            distribution_params=process.stock_distribution_params,
                            lifetime=process.stock_lifetime,
                        ),
                        x=process.position_x,
                        y=process.position_y,
                    ))

            year_to_data[year] = {
                "labels": year_node_labels,
                "sources": year_sources,
                "targets": year_targets,
                "values": year_link_values,
                "node_colors": year_node_colors,
                "link_colors": year_link_colors,
                "link_custom_data": year_link_custom_data,
                "node_positions_x": year_node_positions_x,
                "node_positions_y": year_node_positions_y,
                "node_custom_data": year_node_custom_data
            }

        return year_to_data

    def _build_scenario_info(self, scenario: Scenario) -> Dict[str, Any]:
        """
        Build info from Scenario-object.

        :param scenario: Target Scenario-object
        :return: Dictionary (key, value)
        """
        scenario_info = {}
        scenario_info["scenario_name"] = scenario.name
        scenario_info["baseline_value_name"] = scenario.scenario_data.baseline_value_name
        scenario_info["baseline_unit_name"] = scenario.scenario_data.baseline_unit_name
        return scenario_info

    def _build_scenario_graph(self,
                              scenario_name: str,
                              scenario_info: Dict[str, Any],
                              scenario_data: Dict[str, Dict] = None,
                              params: Dict = None):
        # Add JS script that is run after the Plotly has loaded
        filename_plotly = os.path.join(os.path.abspath("."), "core", "datavisualizer_data/plotly-3.0.0.min.js")
        filename_html = os.path.join(os.path.abspath("."), "core", "datavisualizer_data/datavisualizer_plotly.html")

        # Read HTML file contents
        html = ""
        with open(filename_html, "r", encoding="utf-8") as fs:
            html = fs.read()

        # Read PlotlyJS file contents
        plotly_js = ""
        with open(filename_plotly, "r", encoding="utf-8") as fs:
            plotly_js = fs.read()

        # Replace contents with data
        # Plotly
        html = html.replace(
            '<script src="./plotly-3.0.0.min.js"></script>',
            f'<script type="text/javascript">{plotly_js}</script>')

        # Scenario info as JSON
        html = html.replace("// rawScenarioInfo:", "rawScenarioInfo:")
        html = html.replace("{rawScenarioInfo}", json.dumps(scenario_info))

        # Scenario year to data as JSON
        html = html.replace("// rawYearToData:", "rawYearToData:")
        html = html.replace("{rawYearToData}", json.dumps(scenario_data))

        return html

    def _build_default_transformation_stage_colors(self,
                                                   unique_transformation_stages: set,
                                                   process_transformation_stage_colors: Dict[str, str]):
        """
        Build and fill missing transformation stage colors with default color palette.

        :param unique_transformation_stages: Set of unique transformation stages
        :param process_transformation_stage_colors: Dictionary (transformation stage, Color)
        """

        # Default color palette for 8 transformation stages
        default_color_palette = [
            "#7dda60",
            "#eb5e34",
            "#8c76cf",
            "#5baa11",
            "#3281db",
            "#61b053",
            "#efc3ca",
            "#dfc57b",
        ]

        # Find missing transformation stage names
        defined_transformation_stage_names = set(list(process_transformation_stage_colors.keys()))
        missing_transformation_stage_names = unique_transformation_stages.difference(defined_transformation_stage_names)

        # Fill process_transformation_stage_colors with
        for index, transformation_stage in enumerate(missing_transformation_stage_names):
            color = default_color_palette[index % len(default_color_palette)]
            new_color = Color(params=[transformation_stage, color])
            process_transformation_stage_colors[transformation_stage] = new_color.value
