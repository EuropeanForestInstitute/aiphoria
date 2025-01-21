import os
import json
from typing import List, Dict, Any
from core.datastructures import Scenario, Color
import plotly.graph_objects as go
from PIL import Image

from core.parameters import ParameterName


class DataVisualizer(object):
    def __init__(self, mode: str = "network"):
        self._process_name_override_mappings = dict()
        self._button_font_size = 13
        self._fig = None
        self._script = ""

    def show(self):
        self._fig.show(renderer="browser", post_script=[self._script], config={'displayModeBar': False})

    def build(self, scenario: Scenario, params: dict, separate_outputs: bool = True):
        flow_solver = scenario.flow_solver

        small_node_threshold = params["small_node_threshold"]
        process_transformation_stage_colors = params["process_transformation_stage_colors"]
        virtual_process_graph_labels = params["virtual_process_graph_labels"]
        flow_alpha = params["flow_alpha"]
        virtual_process_color = params["virtual_process_color"]
        virtual_flow_color = params["virtual_flow_color"]

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
            year_node_customdata = []
            year_link_values = []
            year_link_colors = []
            year_link_customdata = []

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

                outflows = process_to_flows[process]["out"]
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
                        red, green, blue = tuple(int(link_color[i:i+2], 16) for i in (0, 2, 4))
                        link_color = "rgba({},{},{},{})".format(red, green, blue, flow_alpha)
                    else:
                        link_color = process_transformation_stage_colors[process.transformation_stage]
                        link_color = link_color.lstrip("#")
                        red, green, blue = tuple(int(link_color[i:i+2], 16) for i in (0, 2, 4))
                        link_color = "rgba({},{},{},{})".format(red / 255, green / 255, blue / 255, flow_alpha)

                    year_link_colors.append(link_color)

                    # Custom data for link
                    year_link_customdata.append(dict(is_visible=True, is_virtual=flow.is_virtual))

                # Custom data for node
                year_node_customdata.append(dict(node_id=process.id, is_visible=True, is_virtual=process.is_virtual))

            year_to_data[year] = {
                "labels": year_node_labels,
                "sources": year_sources,
                "targets": year_targets,
                "values": year_link_values,
                "node_colors": year_node_colors,
                "link_colors": year_link_colors,
                "node_positions_x": year_node_positions_x,
                "node_positions_y": year_node_positions_y,
                "node_customdata": year_node_customdata
            }

        # Metadata for all the traces
        fig_metadata = []
        for process in process_to_flows:
            fig_metadata.append(process.id)

        # Create Sankey chart for each year
        fig = go.Figure()

        # Create Sankey traces for each year and add those to fig
        for year, year_data in year_to_data.items():
            year_node_labels = year_data["labels"]
            year_sources = year_data["sources"]
            year_targets = year_data["targets"]
            year_link_values = year_data["values"]
            year_node_colors = year_data["node_colors"]
            year_node_customdata = year_data["node_customdata"]

            new_trace = go.Sankey(
                uid=year,
                arrangement='freeform',
                # arrangement='snap',
                # arrangement='perpendicular',
                node=dict(
                    label=year_node_labels,
                    pad=10,
                    color=year_node_colors,
                    line=dict(width=2, color="rgba(0, 0, 0, 0)"),
                    x=year_node_positions_x,
                    y=year_node_positions_y,
                    customdata=year_node_customdata,
                ),
                link=dict(
                    arrowlen=5,
                    source=year_sources,
                    target=year_targets,
                    value=year_link_values,
                    color=year_link_colors,
                    customdata=year_link_customdata
                ),
                # orientation='v',  # Vertical orientation
                orientation='h',
                customdata=[
                    {
                        "year": year,
                    }
                ],
                meta=fig_metadata
            )
            fig.add_trace(new_trace)

        for data in fig.data:
            data.visible = False
        fig.data[0].visible = True

        # Create and add slider
        steps = []
        for index, data in enumerate(fig.data):
            customdata = data["customdata"][0]
            year = customdata["year"]

            step = dict(
                method="update",
                label="{}".format(year),
                args=[
                    {
                        "visible": [False] * len(fig.data),
                    },
                    {
                        "title": "Year {}".format(year)
                    },
                    {
                        "year": year,
                    },
                ],
            )
            step["args"][0]["visible"][index] = True
            steps.append(step)

        sliders = [
            dict(
                name="sliderYearSelection",
                active=0,
                currentvalue={"prefix": "Selected timestep: "},
                pad={"t": 50},
                steps=steps,
            ),
        ]

        # Show dropdown for showing normalized position or not
        fig.update_layout(
            autosize=True,
            title=dict(
                text="Year {}".format(min(year_to_process_to_flows.keys())),
                subtitle=dict(
                    text="Scenario: {}".format(scenario.name),
                    font=dict(color='#000', size=15)
                )
            ),
            font={"size": 18, "color": '#000', "family": "Arial"},
            plot_bgcolor='#ccc',
            paper_bgcolor="#ffffff",
            sliders=sliders,
            updatemenus=[
                dict(
                    buttons=
                    [
                        {
                            "name": "buttonToggleSmallNodes",
                            "label": "Show all",
                            "args": ['toggleSmallNodes', 'true'],
                            "method": "restyle"
                        },
                        {
                            "name": "buttonToggleSmallNodes",
                            "args": ['toggleSmallNodes', 'false'],
                            "label": "Hide small (<{})  ".format(small_node_threshold),
                            "method": "restyle"
                        },
                    ],
                    direction="up",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    active=0,
                    x=0.0, xanchor="left",
                    y=0.0, yanchor="top",
                    bgcolor="rgba(0.7, 0.7, 0.7, 0.9)",
                    font=dict(size=self._button_font_size),
                ),
                # dict(
                #     buttons=list([
                #         dict(
                #             name="buttonShowNodeInfo",
                #             label="Show node info",
                #             args=['showNodeInfo', 'true'],
                #             method="restyle"
                #         ),
                #         dict(
                #             name="buttonShowNodeInfo",
                #             label="Hide node info",
                #             args=['showNodeInfo', 'false'],
                #             method="restyle"
                #         ),
                #     ]),
                #     direction="up",
                #     pad={"r": 10, "t": 10},
                #     showactive=True,
                #     active=1,
                #     x=0.2, xanchor="right",
                #     y=0.0, yanchor="top",
                #     bgcolor="rgba(0.7, 0.7, 0.7, 0.9)",
                #     font=dict(size=self._button_font_size)
                # ),
                # dict(
                #     buttons=list([
                #         dict(
                #             name="buttonShowVirtualNodes",
                #             label="Show virtual nodes",
                #             args=['showVirtualNodes', 'true'],
                #             method="restyle"
                #         ),
                #         dict(
                #             name="buttonShowVirtualNodes",
                #             label="Hide virtual nodes",
                #             args=['showVirtualNodes', 'false'],
                #             method="restyle"
                #         ),
                #     ]),
                #     direction="up",
                #     pad={"r": 10, "t": 10},
                #     showactive=True,
                #     active=0,
                #     x=0.25, xanchor="left",
                #     y=0.0, yanchor="top",
                #     bgcolor="rgba(0.7, 0.7, 0.7, 0.9)",
                #     font=dict(size=self._button_font_size)
                # )
            ],
        )

        # Add aiphoria logo watermark
        logo = Image.open("docs/_static/aiphoria-logo.png")
        fig.add_layout_image(
            dict(source=logo,
                xref="paper", yref="paper",
                x=1.03, y=1.12,
                sizex=0.10, sizey=0.10,
                xanchor="right", yanchor="top"
            )
        )

        self._fig = fig

        # Add JS script that is run after the Plotly has loaded
        filename = os.path.join(os.path.abspath("."), "core", "datavisualizer_data/datavisualizer_plotly_post.js")

        visualizer_js = ""
        with open(filename, "r", encoding="utf-8") as fs:
            visualizer_js = fs.read()

        visualizer_js = visualizer_js.replace("{small_node_threshold}", str(small_node_threshold))
        self._script = visualizer_js

    def build_and_show(self, scenarios: List[Scenario],
                       visualizer_params: dict,
                       model_params: dict,
                       combine_to_one_file: bool = False):
        scenario_name_to_data = {}
        for scenario in scenarios:
            scenario_data = self._build_scenario_data(scenario, visualizer_params)
            scenario_name_to_data[scenario.name] = scenario_data

        if combine_to_one_file:
            # # TODO: Implement this
            # # Build combined file with all the scenarios included
            # fig, script = self._build_plotly_data_combine(scenario_name_to_data, visualizer_params)
            #
            # output_path = os.path.join(model_params[ParameterName.OutputPath], scenario_name)
            # filename = "{}_sankey.html".format(scenario_name)
            # abs_path_to_file = os.path.join(output_path, filename)
            #
            # # Write results to file and open the file in browser
            # fig.write_html(file=abs_path_to_file, post_script=[script], config={'displayModeBar': False},
            #                full_html=True, auto_open=True)
            #
            # # Open directly in browser
            # #fig.show(renderer="browser", post_script=[script], config={'displayModeBar': False})
            print("Not implemented yet")

        else:
            # Build separate files for each scenario
            for scenario_name, year_to_data in scenario_name_to_data.items():
                fig, script = self._build_plotly_data_separate(scenario_name, year_to_data, visualizer_params)

                output_path = os.path.join(model_params[ParameterName.OutputPath], scenario_name)
                filename = "{}_sankey.html".format(scenario_name)
                abs_path_to_file = os.path.join(output_path, filename)

                # Write results to file and open the file in browser
                fig.write_html(file=abs_path_to_file, post_script=[script], config={'displayModeBar': False},
                               full_html=True, auto_open=True)

                # Open directly in browser
                #fig.show(renderer="browser", post_script=[script], config={'displayModeBar': False})

    def _build_scenario_data(self, scenario: Scenario, params: Dict):
        flow_solver = scenario.flow_solver

        small_node_threshold = params["small_node_threshold"]
        process_transformation_stage_colors = params["process_transformation_stage_colors"]
        virtual_process_graph_labels = params["virtual_process_graph_labels"]
        flow_alpha = params["flow_alpha"]
        virtual_process_color = params["virtual_process_color"]
        virtual_flow_color = params["virtual_flow_color"]

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

                outflows = process_to_flows[process]["out"]
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
                    year_link_custom_data.append(dict(is_visible=True, is_virtual=flow.is_virtual))

                # Custom data for node
                year_node_custom_data.append(dict(node_id=process.id, is_visible=True, is_virtual=process.is_virtual))

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

    def _build_plotly_data_separate(self, scenario_name: str, year_to_data: Dict[str, Dict] = None, params: Dict = None):
        # Metadata for all the traces
        fig_metadata = []
        # for process in process_to_flows:
        #     fig_metadata.append(process.id)

        # Create Sankey chart for each year
        fig = go.Figure()

        # Create Sankey traces for each year and add those to fig
        for year, year_data in year_to_data.items():
            year_node_labels = year_data["labels"]
            year_sources = year_data["sources"]
            year_targets = year_data["targets"]
            year_link_values = year_data["values"]
            year_link_colors = year_data["link_colors"]
            year_link_custom_data = year_data["link_custom_data"]
            year_node_colors = year_data["node_colors"]
            year_node_positions_x = year_data["node_positions_x"]
            year_node_positions_y = year_data["node_positions_y"]
            year_node_custom_data = year_data["node_custom_data"]

            new_trace = go.Sankey(
                uid=year,
                arrangement='freeform',
                # arrangement='snap',
                # arrangement='perpendicular',
                node=dict(
                    label=year_node_labels,
                    pad=10,
                    color=year_node_colors,
                    line=dict(width=2, color="rgba(0, 0, 0, 0)"),
                    x=year_node_positions_x,
                    y=year_node_positions_y,
                    customdata=year_node_custom_data,
                ),
                link=dict(
                    arrowlen=5,
                    source=year_sources,
                    target=year_targets,
                    value=year_link_values,
                    color=year_link_colors,
                    customdata=year_link_custom_data
                ),
                # orientation='v',  # Vertical orientation
                orientation='h',
                customdata=[
                    {
                        "year": year,
                    }
                ],
                meta=fig_metadata
            )
            fig.add_trace(new_trace)

        for data in fig.data:
            data.visible = False
        fig.data[0].visible = True

        # Create and add slider
        steps = []
        for index, data in enumerate(fig.data):
            customdata = data["customdata"][0]
            year = customdata["year"]

            step = dict(
                method="update",
                label="{}".format(year),
                args=[
                    {"visible": [False] * len(fig.data)},
                    {"title": "Year {}".format(year)},
                    {"year": year},
                ],
            )
            step["args"][0]["visible"][index] = True
            steps.append(step)

        sliders = [
            dict(
                name="sliderYearSelection",
                active=0,
                currentvalue={"prefix": "Selected timestep: "},
                pad={"t": 50},
                steps=steps,
            ),
        ]

        # Show dropdown for showing normalized position or not
        fig.update_layout(
            autosize=True,
            title=dict(
                text="Year {}".format(list(year_to_data.keys())[0]),
                subtitle={
                    "text": "Scenario: {}".format(scenario_name)
                }

            ),
            font={"size": 18, "color": '#000', "family": "Arial"},
            plot_bgcolor='#ccc',
            paper_bgcolor="#ffffff",
            sliders=sliders,
        )
        # # Show dropdown for showing normalized position or not
        # fig.update_layout(
        #     autosize=True,
        #     title=dict(
        #         text="Year {}".format(list(year_to_data.keys())[0]),
        #         subtitle=dict(
        #             text="Scenario: {}".format(scenario_name),
        #             font=dict(color='#000', size=15)
        #         )
        #     ),
        #     font={"size": 18, "color": '#000', "family": "Arial"},
        #     plot_bgcolor='#ccc',
        #     paper_bgcolor="#ffffff",
        #     sliders=sliders,
        # )

        # Add aiphoria logo watermark
        logo = Image.open("docs/_static/aiphoria-logo.png")
        fig.add_layout_image(
            dict(source=logo,
                xref="paper", yref="paper",
                x=1.03, y=1.12,
                sizex=0.10, sizey=0.10,
                xanchor="right", yanchor="top"
            )
        )

        result_fig = fig

        # Add JS script that is run after the Plotly has loaded
        filename = os.path.join(os.path.abspath("."), "core", "datavisualizer_data/datavisualizer_plotly_post.js")

        visualizer_js = ""
        with open(filename, "r", encoding="utf-8") as fs:
            visualizer_js = fs.read()

        small_node_threshold = params["small_node_threshold"]
        # process_transformation_stage_colors = params["process_transformation_stage_colors"]
        # virtual_process_graph_labels = params["virtual_process_graph_labels"]
        # flow_alpha = params["flow_alpha"]
        # virtual_process_color = params["virtual_process_color"]
        # virtual_flow_color = params["virtual_flow_color"]

        visualizer_js = visualizer_js.replace("{small_node_threshold}", str(small_node_threshold))
        result_script = visualizer_js

        return result_fig, result_script

    def _build_scenario_data(self, scenario: Scenario, params: Dict):
        flow_solver = scenario.flow_solver

        small_node_threshold = params["small_node_threshold"]
        process_transformation_stage_colors = params["process_transformation_stage_colors"]
        virtual_process_graph_labels = params["virtual_process_graph_labels"]
        flow_alpha = params["flow_alpha"]
        virtual_process_color = params["virtual_process_color"]
        virtual_flow_color = params["virtual_flow_color"]

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
                    year_link_custom_data.append(dict(is_visible=True, is_virtual=flow.is_virtual))

                # Custom data for node
                year_node_custom_data.append(
                    dict(
                        node_id=process.id,
                        is_visible=True,
                        is_virtual=process.is_virtual,
                        total_inflows=total_inflows,
                        total_outflows=total_outflows,
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

    def _build_plotly_data_combine(self, scenario_name_to_data: Dict[str, Dict[int, Any]], params: Dict = None):
        # Metadata for all the traces
        fig_metadata = []
        # for process in process_to_flows:
        #     fig_metadata.append(process.id)

        # Create Sankey chart for each year
        fig = go.Figure()

        scenario_name = list(scenario_name_to_data.keys())[0]
        scenario_year_to_data = scenario_name_to_data[scenario_name]
        year_to_data = scenario_year_to_data

        # Create Sankey traces for each year and add those to fig
        for year, year_data in year_to_data.items():
            year_node_labels = year_data["labels"]
            year_sources = year_data["sources"]
            year_targets = year_data["targets"]
            year_link_values = year_data["values"]
            year_link_colors = year_data["link_colors"]
            year_link_custom_data = year_data["link_custom_data"]
            year_node_colors = year_data["node_colors"]
            year_node_positions_x = year_data["node_positions_x"]
            year_node_positions_y = year_data["node_positions_y"]
            year_node_custom_data = year_data["node_custom_data"]

            new_trace = go.Sankey(
                uid=year,
                arrangement='freeform',
                node=dict(
                    label=year_node_labels,
                    pad=10,
                    color=year_node_colors,
                    line=dict(width=2, color="rgba(0, 0, 0, 0)"),
                    x=year_node_positions_x,
                    y=year_node_positions_y,
                    customdata=year_node_custom_data,
                ),
                link=dict(
                    arrowlen=5,
                    source=year_sources,
                    target=year_targets,
                    value=year_link_values,
                    color=year_link_colors,
                    customdata=year_link_custom_data
                ),
                orientation='h',
                customdata=[{"year": year}],
                meta=fig_metadata
            )
            fig.add_trace(new_trace)

        for data in fig.data:
            data.visible = False
        fig.data[0].visible = True

        # Create and add slider
        steps = []
        for index, data in enumerate(fig.data):
            custom_data = data["customdata"][0]
            year = custom_data["year"]

            step = dict(
                method="update",
                label="{}".format(year),
                args=[
                    {"visible": [False] * len(fig.data)},
                    {"title": "Year {}".format(year)},
                    {"year": year},
                ],
            )
            step["args"][0]["visible"][index] = True
            steps.append(step)

        sliders = [
            dict(
                name="sliderYearSelection",
                active=0,
                currentvalue={"prefix": "Selected timestep: "},
                pad={"t": 50},
                steps=steps,
            ),
        ]

        # Show dropdown for showing normalized position or not
        fig.update_layout(
            autosize=True,
            title=dict(
                text="Year 1000",
                subtitle=dict(
                    text="Scenario: {}".format(scenario_name),
                    font=dict(color='#000', size=15)
                )
            ),
            font={"size": 18, "color": '#000', "family": "Arial"},
            plot_bgcolor='#ccc',
            paper_bgcolor="#ffffff",
            sliders=sliders,
        )

        # Add aiphoria logo watermark
        logo = Image.open("docs/_static/aiphoria-logo.png")
        fig.add_layout_image(
            dict(source=logo,
                xref="paper", yref="paper",
                x=1.03, y=1.12,
                sizex=0.10, sizey=0.10,
                xanchor="right", yanchor="top"
            )
        )

        result_fig = fig

        # Add JS script that is run after the Plotly has loaded
        filename = os.path.join(os.path.abspath("."), "core", "datavisualizer_data/datavisualizer_plotly_post_dev.js")

        visualizer_js = ""
        with open(filename, "r", encoding="utf-8") as fs:
            visualizer_js = fs.read()

        small_node_threshold = params["small_node_threshold"]
        # process_transformation_stage_colors = params["process_transformation_stage_colors"]
        # virtual_process_graph_labels = params["virtual_process_graph_labels"]
        # flow_alpha = params["flow_alpha"]
        # virtual_process_color = params["virtual_process_color"]
        # virtual_flow_color = params["virtual_flow_color"]

        visualizer_js = visualizer_js.replace("{small_node_threshold}", str(small_node_threshold))
        result_script = visualizer_js.replace("{year_to_data}", json.dumps(scenario_name_to_data))

        return result_fig, result_script

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
