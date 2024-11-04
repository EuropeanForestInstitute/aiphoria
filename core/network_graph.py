import webbrowser
import os
import json
import pandas as pd
from typing import List, Dict


class NetworkGraph(object):
    def __init__(self):
        self._echarts = ""
        self._visualizer = ""
        self._html = ""

        # Load ECharts from file
        with open("./core/echarts_min.js", mode="r", encoding="utf-8") as fs:
            self._echarts = fs.read()

        # Load visualizer script from file
        with open("./core/network_graph.js", mode="r", encoding="utf-8") as fs:
            self._visualizer = fs.read()

    def build(self, df_process_to_flows: pd.DataFrame, years_to_check: List[int]) -> None:
        """
        Compile and insert data to HTML file.

        :param df_process_to_flows: DataFrame
        :param years_to_check: List of years that are included
        """
        year_to_data = {}
        for year in years_to_check:
            rows = df_process_to_flows.loc[year]
            node_index_to_data = {}
            edge_index_to_data = {}

            # Create nodes and edges
            new_node_index = 0
            new_edge_index = 0
            for row in rows:
                process = row["process"]
                outflows = row["flows"]["out"]

                # Create node data
                new_node_data = {
                    "process_id": process.id,
                    "transformation_stage": process.transformation_stage,
                }
                node_index_to_data[new_node_index] = new_node_data
                new_node_index += 1

                # Create edges from nodes (= process outflows)
                for flow in outflows:
                    new_edge_data = {
                        "flow_id": flow.id,
                        "source_process_id": flow.source_process_id,
                        "target_process_id": flow.target_process_id,
                        "is_unit_absolute_value": flow.is_unit_absolute_value,
                        "value": flow.value,
                        "unit": flow.unit,
                    }
                    edge_index_to_data[new_edge_index] = new_edge_data
                    new_edge_index += 1

            year_to_data[year] = {
                "node_index_to_data": node_index_to_data,
                "edge_index_to_data": edge_index_to_data,
            }

        # Replace data in visualizer
        script = self._visualizer
        script = script.replace("{year_to_data}", json.dumps(year_to_data))
        self._visualizer = script

        with open("./core/network_graph.html", "r", encoding="utf-8") as fs:
            self._html = fs.read()

        # Replace 'echarts_content' and 'visualizer
        self._html = self._html.replace("{echarts_content}", self._echarts)
        self._html = self._html.replace("{visualizer_content}", self._visualizer)

    def show(self, output_filename: str = "network_graph.html") -> None:
        """
        Build HTML file and open it in browser.

        :param output_filename: Filename for the HTML file
        """
        filename = output_filename
        with open(filename, "w", encoding="utf-8") as fs:
            fs.write(self._html)
        webbrowser.open("file://" + os.path.realpath(filename))
