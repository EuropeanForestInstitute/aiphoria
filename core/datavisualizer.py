from core.flowsolver import FlowSolver
import plotly.graph_objects as go
from PIL import Image


class DataVisualizer(object):
    def __init__(self):
        self._process_name_override_mappings = dict()
        self._fig = None
        self._script = ""

    def show(self):
        self._fig.show(renderer="browser", post_script=[self._script], config={'displayModeBar': False})

    def build(self, flowgraph: FlowSolver, params: dict):
        small_node_threshold = params["small_node_threshold"]
        process_transformation_stage_colors = params["process_transformation_stage_colors"]
        virtual_process_graph_labels = params["virtual_process_graph_labels"]
        flow_alpha = params["flow_alpha"]
        virtual_process_color = params["virtual_process_color"]
        virtual_flow_color = params["virtual_flow_color"]

        year_to_data = {}
        year_to_process_to_flows = flowgraph.get_year_to_process_to_flows()
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
                        continue

                    if flow.target_process_id not in process_id_to_index:
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
        self._script = """
        // ****************
        // * Global state *
        // ****************
        const globals = {
            // Reference to the Plotly div
            graph: null,

            // Currently visible trace index, in this case selected year trace
            currentTraceIndex: -1,

            // Currently visible trace
            currentTrace: null,

            // Toggle showing small nodes and their immediate links on or off
            toggleSmallNodes: true, // true = show small nodes, false = hide small nodes

            // Nodes that have total inflows or total outflows less than this value will be
            // hidden
            smallNodeThreshold: """ + str(small_node_threshold) + """,

            // Toggle showing window that shows normalized node positions
            // This data can be copied and then pasted to Excel file for precise node placement
            showNodeInfoWindow: false,
            
            // Toggle showing virtual nodes and flows on or off
            showVirtualNodes: true,

            // Deep-copied initial data of all nodes and links
            initialData: [],

            // Current node data
            nodeDataCache: [],
        }


        // **********************************
        // * Initialization of global state *
        // **********************************
        function initializeGlobalState() {
            // Get generated element id by using placeholder {plot_id}
            globals.graph = document.getElementById('{plot_id}')

            // Store initial color data of nodes
            for(const trace of globals.graph.data) {
                const traceCopy = JSON.parse(JSON.stringify(trace))
                globals.initialData.push(traceCopy)
            }

            let visibleTraceIndex = -1
            for(let i = 0; i < globals.graph.data.length; i++) {
                if(globals.graph.data[i].visible) {
                    visibleTraceIndex = i
                }
            }
            globals.currentTraceIndex = visibleTraceIndex
            globals.currentTrace = globals.graph.data[globals.currentTraceIndex]
        }

        initializeGlobalState()

        // ********************
        // * Update functions *
        // ********************
        function updateToggleSmallNodes() {
            const trace = globals.currentTrace
            if(globals.toggleSmallNodes) {
                // Show all nodes (= set all nodes and link colors back to initial state
                const initialData = globals.initialData[globals.currentTraceIndex]

                // Reset nodes
                for(let nodeIndex = 0; nodeIndex < initialData.node.color.length; nodeIndex++) {
                    trace.node.label[nodeIndex] = initialData.node.label[nodeIndex]
                    trace.node.color[nodeIndex] = initialData.node.color[nodeIndex]
                    trace.node.customdata[nodeIndex].is_visible = true
                }

                // Reset links
                for(let linkIndex = 0; linkIndex < initialData.link.source.length; linkIndex++) {
                    trace.link.color[linkIndex] = initialData.link.color[linkIndex]
                    trace.link.customdata[linkIndex].is_visible = true
                }
            } else {
                // Hide all small nodes and links that...
                // - have no inflows and have total outflows < threshold
                // - total inflows < threshold and have no outflows
                // Get all unique node IDs and sort in ascending order
                const uniqueNodeIds = new Set()
                for(const nodeId of trace.link.source) {
                    uniqueNodeIds.add(nodeId)
                }
                for(const nodeId of trace.link.target) {
                    uniqueNodeIds.add(nodeId)
                }
                const nodeIds = Array.from(uniqueNodeIds).sort((a, b) => { return a - b })

                // Create node in and out connection data
                // Node ID -> { in: inflows[], out: outflows[] }
                const nodeIdToFlows = new Map()
                for(const nodeId of nodeIds) {
                    nodeIdToFlows.set(nodeId, { "in": [], "out": [], "in_values": [], "out_values": [] })
                }

                // Build inflows and outflows for node IDs
                for(let index = 0; index < trace.link.source.length; index++) {
                    const sourceNodeId = trace.link.source[index]
                    const targetNodeId = trace.link.target[index]
                    const value = trace.link.value[index]
                    nodeIdToFlows.get(sourceNodeId)["out"].push(targetNodeId)
                    nodeIdToFlows.get(sourceNodeId)["out_values"].push(value)
                    nodeIdToFlows.get(targetNodeId)["in"].push(sourceNodeId)
                    nodeIdToFlows.get(targetNodeId)["in_values"].push(value)
                }

                for(const [nodeId, flows] of nodeIdToFlows.entries()) {
                    const numInflows = flows["in"].length
                    const numOutflows = flows["out"].length
                    let totalInflows = flows["in_values"].reduce((partialSum, val) => partialSum + val, 0)
                    let totalOutflows = flows["out_values"].reduce((partialSum, val) => partialSum + val, 0)
                    let hide = false

                    if(numInflows == 0 && totalOutflows < globals.smallNodeThreshold) {
                        hide = true
                    }

                    if(totalInflows < globals.smallNodeThreshold && numOutflows == 0) {
                        hide = true
                    }

                    if(hide) {
                        // Set node color to transparent
                        trace.node.label[nodeId] = ""
                        trace.node.color[nodeId] = "rgba(0, 0, 0, 0)"
                        trace.node.customdata[nodeId].is_visible = false

                        // Set also all connected links to transparent
                        for(let index = 0; index < trace.link.source.length; index++) {
                            const sourceNodeId = trace.link.source[index]
                            const targetNodeId = trace.link.target[index]
                            if(sourceNodeId == nodeId || targetNodeId == nodeId) {
                                trace.link.color[index] = "rgba(0, 0, 0, 0)"
                                trace.link.customdata[index].is_visible = false
                            }
                        }
                    }
                }
            }

            const data = {
                nodes: globals.currentTrace.node,
                links: globals.currentTrace.link,
            }
            Plotly.restyle(globals.graph, data, {})
        }
        
        function updateShowVirtualNodes() {
            const trace = globals.currentTrace
            if(globals.showVirtualNodes) {
                const initialData = globals.initialData[globals.currentTraceIndex]            
            
                // Show all virtual processes
                for(let nodeIndex = 0; nodeIndex < trace.node.color.length; nodeIndex++) {
                    if(trace.node.customdata[nodeIndex].is_virtual) {
                        trace.node.label[nodeIndex] = initialData.node.label[nodeIndex]
                        trace.node.color[nodeIndex] = initialData.node.color[nodeIndex]
                        trace.node.customdata[nodeIndex].is_visible = true
                    }
                }

                // Show all virtual flows
                for(let linkIndex = 0; linkIndex < trace.link.source.length; linkIndex++) {
                    if(trace.link.customdata[linkIndex].is_virtual) {
                        trace.link.color[linkIndex] = initialData.link.color[linkIndex]
                        trace.link.customdata[linkIndex].is_visible = true
                    }
                }
            } else {
                // Hide all virtual processes
                for(let nodeIndex = 0; nodeIndex < trace.node.color.length; nodeIndex++) {
                    if(trace.node.customdata[nodeIndex].is_virtual) {
                        trace.node.label[nodeIndex] = ""
                        trace.node.color[nodeIndex] = "rgba(0, 0, 0, 0)"
                        trace.node.customdata[nodeIndex].is_visible = false
                    }
                }

                // Hide all virtual flows
                for(let linkIndex = 0; linkIndex < trace.link.source.length; linkIndex++) {
                    if(trace.link.customdata[linkIndex].is_virtual) {
                        trace.link.color[linkIndex] = "rgba(0, 0, 0, 0)"
                        trace.link.customdata[linkIndex].is_visible = false
                    }
                }
            }

            const data = {
                nodes: globals.currentTrace.node,
                links: globals.currentTrace.link,
            }

            Plotly.restyle(globals.graph, data, {})
        }

        globals.graph.on("plotly_sliderchange", function(eventdata) {
            // NOTE: Check that using proper slider
            //console.log(eventdata.slider.name)
            // Update visual state of the selected trace
            updateToggleSmallNodes()
        })

        globals.graph.on('plotly_hover', function(eventdata) {
            // Hovering over grouped
            if(eventdata.points[0].group) {
                return
            }
            
            const target = eventdata.points[0] 

            // Return if hovering over flow
            const isFlow = target.hasOwnProperty('flow')
            if(isFlow) {
                const flow = target
                const customdata = flow.customdata
                const isVirtualFlow = customdata.is_virtual

                let text = ""
                text += "Source: " + flow.source.label + "<br />" 
                text += "Target: " + flow.target.label + "<br />" 
                text += "Value: <b>" + flow.value.toFixed(1) + "</b><br />"
                
                if(isVirtualFlow) {
                    text += "<b>Virtual flow</b><br />"
                }

                const dataUpdate = {}
                dataUpdate["link.hovertemplate"] = text
                dataUpdate["link.hovertemplate"] += "<extra></extra>"

                Plotly.restyle(globals.graph, dataUpdate, {})
                return
            }

            // Check if showing normalized position for nodes
            const node = target
            if(!node.customdata.is_visible) {
                return
            }

            // Display different hovertemplate depending if showing normalized position or not
            const dataUpdate = {}
            let totalInflows = 0.0
            let numInflows = 0
            for(const flow of node.targetLinks) {
                totalInflows += flow.value
                numInflows += 1
            }

            let totalOutflows = 0.0
            let numOutflows = 0
            for(const flow of node.sourceLinks) {
                totalOutflows += flow.value
                numOutflows += 1
            }
            
            let text = ""
            text += "Inflows: " + numInflows + "<br />"
            text += "Outflows: " + numOutflows + "<br />"
            text += "Total inflows: <b>" + totalInflows.toFixed(1) + "</b><br />"
            text += "Total outflows: <b>" + totalOutflows.toFixed(1) + "</b><br />"

            const isVirtualNode = node.customdata.is_virtual
            if(isVirtualNode) {
                text += "<b>Virtual process</b><br />"
            }

            text += "<extra></extra>"
            dataUpdate["node.hovertemplate"] = text

            const layoutUpdate = {}
            Plotly.restyle(globals.graph, dataUpdate, layoutUpdate)
        })

        globals.graph.on("plotly_restyle", function(eventdata) {
            const source = eventdata[0]

            // Toggle showing small nodes
            if(source.hasOwnProperty('toggleSmallNodes')) {
                globals.toggleSmallNodes = JSON.parse(source.toggleSmallNodes.toLowerCase())
                updateToggleSmallNodes()
            }

            // Show node info window
            if(source.hasOwnProperty('showNodeInfo')) {
                const state = JSON.parse(source.showNodeInfo)
                if(state) {
                    // Update values if window already opened
                    globals.showNodeInfoWindow = true
                    createNodeInfoWindow()
                } else {
                    // Close the window
                    globals.showNodeInfo = false
                    removeNodeInfoWindow()
                }
            }
            
            // Toggle showing virtual nodes
            if(source.hasOwnProperty('showVirtualNodes')) {
                const state = JSON.parse(source.showVirtualNodes)
                globals.showVirtualNodes = state                
                updateShowVirtualNodes()
            }
        })

        function createNodeInfoWindow() {
            // Reset global node data cache when opening window
            globals.nodeDataCache = []

            // Get Sankey chart element and Sankey nodes
            const nodeLabelToNormalizedPos = new Map()
            const sankey = document.getElementsByClassName("sankey")[0]
            const sankeyRect = sankey.getBoundingClientRect()
            const nodeElems = document.getElementsByClassName("sankey-node")
            for(const elem of nodeElems) {
                const elemLabel = elem.textContent
                const elemRect = elem.getBoundingClientRect()
                const elemCenter = {
                    x: (elemRect.x + elemRect.width * 0.5),
                    y: (elemRect.y + elemRect.height * 0.5),
                }

                // Offset elem center from Sankey origin (=top-left corner)
                elemCenter.x -= sankeyRect.x
                elemCenter.y -= sankeyRect.y

                // Now elemCenter is in Sankey chart coordinate space and normalized position
                // inside chart can be calculated
                const elemCenterNormalized = { x: elemCenter.x / sankeyRect.width, y: elemCenter.y / sankeyRect.height }
                nodeLabelToNormalizedPos.set(elemLabel, elemCenterNormalized)
            }

            // Create style for the node position window
            const styleText = `
                .node-info {
                    position: absolute;
                    min-width: 500px;
                    padding: 8px;
                    min-height: 250px;
                    max-height: 500px;
                    overflow-y: auto;
                    background: #eee;
                    z-index: 1000;
                    top: 50px;
                    left: 50px;
                    border: solid 1px #aaa;
                    border-radius: 4px;
                    font-size: 12px;
                    font-family: "Open Sans", verdana, arial, sans-serif;
                    box-shadow: 0px 0px 4px 4px rgba(0, 0, 0, 0.10)
                }

                table, th, tr, td {
                    padding: 4px;
                    border: solid 1px #aaa;
                    border-collapse: collapse;
                    font-size: 12px;
                    font-family: "Open Sans", verdana, arial, sans-serif;
                }

                table {
                    width: 100%;
                }

                tr {
                    background: #fff;
                }
            `

            const style = document.createElement('style')
            style.type = 'text/css'
            style.innerHTML = styleText
            document.getElementsByTagName('head')[0].appendChild(style)

            const trace = globals.currentTrace

            // Create table
            const elemTable = document.createElement('table')

            // Create headers for table
            const tHead = document.createElement('thead')
            const trHeader = document.createElement('tr')

            thHeaderName = document.createElement('th')
            thHeaderName.appendChild(document.createTextNode('Name'))
            trHeader.appendChild(thHeaderName)
            thHeaderName.style = "user-select: none"


            thHeaderPosX = document.createElement('th')
            thHeaderPosX.appendChild(document.createTextNode('X'))
            trHeader.appendChild(thHeaderPosX)

            thHeaderPosY = document.createElement('th')
            thHeaderPosY.appendChild(document.createTextNode('Y'))
            trHeader.appendChild(thHeaderPosY)

            tHead.appendChild(trHeader)
            elemTable.appendChild(tHead)

            tbody = document.createElement('tbody')

            // Create rows for table and store the node position data to
            for(const nodeId of trace.meta) {
                let found = false
                let nodeIndex = -1
                let nodeData = null
                for(let i = 0; i < trace.node.label.length && !found; i++) {
                    const nodeLabel = trace.node.label[i]
                    const nodeCustomData = trace.node.customdata[i]
                    const nodePos = nodeLabelToNormalizedPos.get(nodeLabel)
                    const isVirtual = nodeCustomData.is_virtual
                    if(nodeCustomData.node_id == nodeId && !isVirtual) {
                        nodeData = { label: nodeLabel, customdata: nodeCustomData, nodePos: nodePos }
                        nodeIndex = i
                        found = true
                    }
                }

                if(nodeData) {
                    globals.nodeDataCache.push(nodeData)
                    const tr = document.createElement('tr')
                    const tdName = tr.insertCell()
                    const tdPosX = tr.insertCell()
                    const tdPosY = tr.insertCell()

                    const nodeId = nodeData.customdata.node_id
                    const nodeLabel = nodeData.label
                    let nodePos = nodeData.nodePos
                    
                    // NOTE: If processes do not have any inflows and outflows (= isolated processes) for
                    //the current year then the nodePos is also undefined.
                    if(nodePos == undefined) {
                        nodePos = { x: "", y: "" }
                    }
                    
                    tdName.appendChild(document.createTextNode(nodeLabel + " (" + nodeId + ")"))
                    tdPosX.appendChild(document.createTextNode(nodePos.x.toFixed(3)))
                    tdPosY.appendChild(document.createTextNode(nodePos.y.toFixed(3)))
                    tbody.appendChild(tr)
                }
            }

            elemTable.appendChild(tbody)


            // Delete existing div if already exists
            const prevElem = document.getElementById("node-info")
            if(prevElem) {
                prevElem.remove()
            }

            const divNodeInfo = document.createElement("div")
            divNodeInfo.className = 'node-info'
            divNodeInfo.id = "node-info"

            // Title
            const elemTitle = document.createElement('h2')
            elemTitle.innerHTML = 'Node normalized positions'

            // Copy button
            const buttonCopy = document.createElement('button')
            buttonCopy.textContent = "Copy positions to clipboard"
            buttonCopy.style = "margin-bottom: 1rem"

            let text = ""
            buttonCopy.addEventListener("click", (e) => {
                for(const elem of globals.nodeDataCache) {
                    const nodeLabel = elem.label
                    const nodePos = elem.nodePos
                    text += nodePos.x.toFixed(3) + "\\t" + nodePos.y.toFixed(3) + "\\n"
                }
                navigator.clipboard.writeText(text)
            })

            // Append to node window div
            divNodeInfo.appendChild(elemTitle)
            divNodeInfo.appendChild(buttonCopy)
            divNodeInfo.appendChild(elemTable)
            document.getElementsByTagName("body")[0].appendChild(divNodeInfo)
        }

        function removeNodeInfoWindow() {
            const elem = document.getElementById("node-info")
            if(elem) {
                elem.remove()
            }
        }
        
        """
