import os

from core.flowsolver import FlowSolver
import plotly.graph_objects as go
from PIL import Image


class DataVisualizer(object):
    def __init__(self):
        self._process_name_override_mappings = dict()
        self._button_font_size = 13
        self._fig = None
        self._script = ""

    def show(self):
        #pass
        self._fig.show(renderer="browser", post_script=[self._script], config={'displayModeBar': False})

    def build(self, flowsolver: FlowSolver, params: dict):
        small_node_threshold = params["small_node_threshold"]
        process_transformation_stage_colors = params["process_transformation_stage_colors"]
        virtual_process_graph_labels = params["virtual_process_graph_labels"]
        flow_alpha = params["flow_alpha"]
        virtual_process_color = params["virtual_process_color"]
        virtual_flow_color = params["virtual_flow_color"]

        year_to_data = {}
        year_to_process_to_flows = flowsolver.get_year_to_process_to_flows()
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

                    link_color = virtual_flow_color
                    if not flow.is_virtual:
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
            colors = year_data["node_colors"]
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
            title="Year {}".format(min(year_to_process_to_flows.keys())),
            font=dict(size=18, color='#000', family="Arial"),
            plot_bgcolor='#ccc',
            paper_bgcolor="#ffffff",
            sliders=sliders,
            updatemenus=[
                dict(
                    buttons=list([
                        dict(
                            name="buttonToggleSmallNodes",
                            label="Show all",
                            args=['toggleSmallNodes', 'true'],
                            method="restyle"
                        ),
                        dict(
                            name="buttonToggleSmallNodes",
                            args=['toggleSmallNodes', 'false'],
                            label="Hide small (<{})  ".format(small_node_threshold),
                            method="restyle"
                        ),
                    ]),
                    direction="up",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    active=0,
                    x=0.0, xanchor="left",
                    y=0.0, yanchor="top",
                    bgcolor="rgba(0.7, 0.7, 0.7, 0.9)",
                    font=dict(size=self._button_font_size)
                ),
                dict(
                    buttons=list([
                        dict(
                            name="buttonShowNodeInfo",
                            label="Show node info",
                            args=['showNodeInfo', 'true'],
                            method="restyle"
                        ),
                        dict(
                            name="buttonShowNodeInfo",
                            label="Hide node info",
                            args=['showNodeInfo', 'false'],
                            method="restyle"
                        ),
                    ]),
                    direction="up",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    active=1,
                    x=0.0, xanchor="left",
                    y=0.08, yanchor="top",
                    bgcolor="rgba(0.7, 0.7, 0.7, 0.9)",
                    font=dict(size=self._button_font_size)
                ),
                dict(
                    buttons=list([
                        dict(
                            name="buttonShowVirtualNodes",
                            label="Show virtual nodes",
                            args=['showVirtualNodes', 'true'],
                            method="restyle"
                        ),
                        dict(
                            name="buttonShowVirtualNodes",
                            label="Hide virtual nodes",
                            args=['showVirtualNodes', 'false'],
                            method="restyle"
                        ),
                    ]),
                    direction="up",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    active=0,
                    x=0.0, xanchor="left",
                    y=0.16, yanchor="top",
                    bgcolor="rgba(0.7, 0.7, 0.7, 0.9)",
                    font=dict(size=self._button_font_size)
                )
            ],
        )

        # Add logo watermark
        logo = Image.open("docs/images/aiphoria-logo.png")
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
        visualizer_js = ""
        filename = os.path.join(os.path.abspath("."), "core", "datavisualizer_plotly_post.js")
        with open(filename, "r") as fs:
            lines = fs.readlines()
            visualizer_js = "".join(lines)

        self._script = visualizer_js
