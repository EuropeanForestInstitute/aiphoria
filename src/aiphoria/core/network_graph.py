import json
import os
import webbrowser
from typing import Dict, Any
from .datastructures import ScenarioData
from importlib.resources import files


class NetworkGraph(object):
    def __init__(self):
        self._echarts = ""
        self._visualizer = ""
        self._html = ""

        # Load ECharts from file
        # path_echarts = os.path.join(os.path.abspath("."), "core", "network_graph_data", "echarts_min.js")
        path_echarts = files("aiphoria.core").joinpath("network_graph_data/echarts_min.js")
        with open(path_echarts, mode="r", encoding="utf-8") as fs:
            self._echarts = fs.read()

        # Load visualizer script from file
        # path_network_graph = os.path.join(os.path.abspath("."), "core", "network_graph_data", "network_graph.js")
        path_network_graph = files("aiphoria.core").joinpath("network_graph_data/network_graph.js")
        with open(path_network_graph, mode="r", encoding="utf-8") as fs:
            self._visualizer = fs.read()

    def build(self, scenario_data: ScenarioData = None, options: Dict[str, Any] = None) -> None:
        """
        Compile and insert data to HTML file.

        :param scenario_data: ScenarioData object
        :param options: Extra options to be provided to network graph
        """
        if scenario_data is None:
            scenario_data = {}

        if options is None:
            options = {}

        year_to_process_id_to_process = scenario_data.year_to_process_id_to_process
        year_to_process_id_to_flow_ids = scenario_data.year_to_process_id_to_flow_ids
        year_to_flow_id_to_flow = scenario_data.year_to_flow_id_to_flow

        year_to_data = {}
        for year, process_id_to_process in year_to_process_id_to_process.items():
            node_index_to_data = {}
            edge_index_to_data = {}

            # Create nodes and edges
            new_node_index = 0
            new_edge_index = 0
            for process_id, process in process_id_to_process.items():
                inflow_ids = year_to_process_id_to_flow_ids[year][process_id]["in"]
                outflow_ids = year_to_process_id_to_flow_ids[year][process_id]["out"]

                # Create node data
                new_node_data = {
                    "process_id": process.id,
                    "process_label": process.label_in_graph,
                    "num_inflows": len(inflow_ids),
                    "num_outflows": len(outflow_ids),
                    "transformation_stage": process.transformation_stage,

                    # Stock related
                    "is_stock": process.stock_lifetime > 0,
                    "stock_lifetime": process.stock_lifetime,
                    "stock_distribution_type": process.stock_distribution_type,
                    "stock_distribution_params": process.stock_distribution_params,

                    # Virtual flow
                    "is_virtual": process.is_virtual
                }
                node_index_to_data[new_node_index] = new_node_data
                new_node_index += 1

                # Create edges from nodes (= process outflows)
                for flow_id in outflow_ids:
                    flow = year_to_flow_id_to_flow[year][flow_id]
                    new_edge_data = {
                        "flow_id": flow.id,
                        "source_process_id": flow.source_process_id,
                        "target_process_id": flow.target_process_id,
                        "is_unit_absolute_value": flow.is_unit_absolute_value,
                        "value": flow.value,  # Flow share
                        "unit": flow.unit,  # Flow unit
                        "evaluated_value": flow.evaluated_value,
                        "evaluated_share": flow.evaluated_share,

                        "is_virtual": flow.is_virtual,
                        "indicators": {k: v for k, v in flow.indicator_name_to_evaluated_value.items()},
                    }
                    edge_index_to_data[new_edge_index] = new_edge_data
                    new_edge_index += 1

            year_to_data[year] = {
                "node_index_to_data": node_index_to_data,
                "edge_index_to_data": edge_index_to_data,
            }

        # Build graph scenario data: contains data that is used shared between all processes and flows
        transformation_stage_name_to_color = {}
        if "transformation_stage_name_to_color" in options:
            transformation_stage_name_to_color = options["transformation_stage_name_to_color"]

        graph_scenario_data = {
            "scenario_name": options["scenario_name"],
            "baseline_unit_name": scenario_data.baseline_unit_name,
            "baseline_value_name": scenario_data.baseline_value_name,
            "transformation_stage_name_to_color": transformation_stage_name_to_color,
        }

        # Replace data in visualizer
        script = self._visualizer
        script = script.replace("{year_to_data}", json.dumps(year_to_data))
        script = script.replace("{scenario_data}", json.dumps(graph_scenario_data))
        self._visualizer = script

        # path_network_graph = os.path.join(os.path.abspath("."), "core", "network_graph_data", "network_graph.html")
        path_network_graph = files("aiphoria.core").joinpath("network_graph_data/network_graph.html")

        with open(path_network_graph, "r", encoding="utf-8") as fs:
            self._html = fs.read()

        # Replace 'echarts_content' and 'visualizer
        self._html = self._html.replace("{echarts_content}", self._echarts)
        self._html = self._html.replace("{visualizer_content}", self._visualizer)

    def show(self, output_filename: str = "network_graph_data.html") -> None:
        """
        Build HTML file and open it in browser.

        :param output_filename: Filename for the HTML file
        """
        with open(output_filename, "w", encoding="utf-8") as fs:
            fs.write(self._html)
        webbrowser.open("file://" + os.path.realpath(output_filename))
