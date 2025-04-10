const chart = echarts.init(document.getElementById("main"));

// ***************
// * Global data *
// ***************

// Global variables
const globals = {
    // Scenario data, contains baseline unit name and value
    scenarioData: {scenario_data},

    // Original data, this will get replaced with JSON object from Python
    originalYearToData: {year_to_data},

    // Updated year to data: contains various mappings e.g. node ID to position
    yearToData: new Map(),

    // Data mappings
    yearToProcessIdToProcess: new Map(),
    yearToProcessIdToFlowIds: new Map(),
    yearToFlowIdToFlow: new Map(),

    // Edge colors
    edgeColors: {
        absolute: "rgba(59, 162, 114, 1)",
        relative: "rgba(255, 50, 50, 1)",
    },

    virtualNodeColor: "rgba(100, 100, 100, 0.8)",
    virtualFlowColor: "rgba(100, 100, 100, 0.8)",

    // Transformation stage name to color mapping, build in initialize()
    transformationStageNameToColor: new Map(),

    // Scenario name
    scenarioName: "Scenario",

    // List of all years
    years: [],

    // Current timeline year
    currentYear: 0,
    currentYearIndex: 0,

    // Current in-use year data
    graphData: {
        data: [],
        links: [],
        categories: [],
        legendData: [],
    },

    selectedNodeIndex: null,

    // All data for timeline years
    initialOption: {},

    // ***********************
    // * Changeable settings *
    // ***********************
    // If true, use process_id as label, otherwise use process_label
    useProcessIdAsLabel: true,

    // If true, use flow type (ABS/%) as flow label, otherwise use flow value
    // useFlowTypeAsLabel: true,
    useFlowTypeAsLabel: false,

    // If true, color processes by their transformation stage
    // If transformation stage color mapping is not found then use default color palette
    useTransformationStageColors: true,

    // If true, hide processes that have no inflows and outflows
    hideUnconnectedProcesses: false,

    // Freeze node positions, disabled by default to allow force layout
    // to find node positions
    freezeNodePositions: false,
};

// **************
// * Formatters *
// **************

function formatValue(val, options = { numDecimals: 3}) {
    // Format value to fixed number of digits (defaults to 3)
    return parseFloat(val.toFixed(options.numDecimals))
}

function getTooltipFormatter(params) {
    const isLegend = params.componentType == "legend"
    const isNode = params.dataType == "node"
    const isLink = params.dataType == "edge"

    let result = ""
    result += `
        <style>
        .tooltip-wrapper {
            min-width: 300px;
            min-height: 100px;
        }

        .tooltip-title {
            font-size: 16px;
            font-weight: bold;
        }

        .tooltip-type-title {
            font-size: 12px;
        }

        .tooltip-body-wrapper {
            display: flex;
            flex-direction: row;
            margin-right: 1rem;
            column-gap: 10px;
        }

        .tooltip-col {
            font-size: 14px;
            font-weight: normal;
            /*flex-grow: 1;*/
            /*height: 100%;*/
        }

        .tooltip-table {
            --border: solid 1px #ccc;
            --font-size-header: 12px;
            --font-size-data: 12px;
            border: var(--border);
            border-collapse: collapse;
        }

        .tooltip-table-title {
            font-size: 14px;
            font-weight: bold;
        }

        /* Table headings */
        .tooltip-table > thead > tr > th {
            font-size: var(--font-size-header);
            font-weight: bold;
            text-align: left;
            border: var(--border);
            width: 100%;
            padding: 0 4px 0 4px;
            background: #eee;
        }

        /* Table rows */
        .tooltip-table > tbody > tr > td {
            font-size: var(--font-size-data);
            text-align: left;
            border: var(--border);
            padding: 0 4px 0 4px;
        }
        </style>
    `

    // TODO: Check with || isLegend and show tooltip when hovering over legend items
    if (isNode) {
        // let nodeData = null
        // let nodeId = null
        // if(isNode) {
        //     nodeData = params.data
        //     nodeId = nodeData.id
        // }
        // if(isLegend) {
        //     nodeId = params.name
        // }

        const nodeData = params.data
        const nodeId = nodeData.id;

        // Get flow IDs
        const year = globals.currentYear;
        const processId = nodeId
        const process = globals.yearToProcessIdToProcess.get(year).get(processId)
        const processIdToFlowIds =
            globals.yearToProcessIdToFlowIds.get(year);
        const flowIdToFlow = globals.yearToFlowIdToFlow.get(year)
        const inflowIds = processIdToFlowIds.get(nodeId).in;
        const outflowIds = processIdToFlowIds.get(nodeId).out;

        // Build stock info
        let stockInfoHTML = ""
        const hasStock = nodeData.isStock
        if (hasStock) {
            let paramsHTML = ""
            const stockDistributionParams = nodeData.stockDistributionParams
            let hasStockParams = !(stockDistributionParams == undefined || stockDistributionParams == null)

            // Unpack stock distribution params
            if (hasStockParams && typeof stockDistributionParams == "object") {
                const params = []
                for (const [k, v] of Object.entries(stockDistributionParams)) {
                    params.push(`${k}=${v}`)
                }
                paramsHTML = params.join(", ")
            } else {
                paramsHTML = stockDistributionParams
            }

            stockInfoHTML = `
                <table class="tooltip-table">
                    <span class="tooltip-table-title">Stock</span>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Lifetime</th>
                            ${hasStockParams ? "<th>Parameters</th>" : ""}
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>${nodeData.stockDistributionType}</td>
                            <td>${nodeData.stockLifetime}</td>
                            ${hasStockParams ? `<td>${paramsHTML}</td>` : ""}
                        </tr>
                    </tbody>
                </table>
                <br/>
            `
            }

        // Build list of inflow IDs, outflow IDs, total inflows and total outflows
        let totalInflowsBaseline = 0.0
        let totalInflowsIndicators = new Map()
        const inflows = [];
        for (const flowId of inflowIds) {
            const flow = flowIdToFlow.get(flowId)
            totalInflowsBaseline += flow.evaluated_value
            for (const [k, v] of Object.entries(flow.indicators)) {
                if (!totalInflowsIndicators.has(k)) {
                    totalInflowsIndicators.set(k, 0.0)
                }
                const prevTotal = totalInflowsIndicators.get(k)
                const newTotal = prevTotal + v
                totalInflowsIndicators.set(k, newTotal)
            }
            inflows.push(flow);
        }

        let totalOutflowsBaseline = 0.0
        let totalOutflowsIndicators = new Map()
        const outflows = [];
        for (const flowId of outflowIds) {
            const flow = flowIdToFlow.get(flowId)
            totalOutflowsBaseline += flow.evaluated_value
            for (const [k, v] of Object.entries(flow.indicators)) {
                if (!totalOutflowsIndicators.has(k)) {
                    totalOutflowsIndicators.set(k, 0.0)
                }
                const prevTotal = totalOutflowsIndicators.get(k)
                const newTotal = prevTotal + v
                totalOutflowsIndicators.set(k, newTotal)
            }
            outflows.push(flow);
        }

        // Get indicator names from either inflows or from outflows
        const indicatorNames = [];
        const hasInflows = inflows.length > 0;
        const hasOutflows = outflows.length > 0;
        if (hasInflows && !indicatorNames.length) {
            for (const key of Object.keys(inflows[0].indicators)) {
                indicatorNames.push(key);
            }
        }
        if (hasOutflows && !indicatorNames.length) {
            for (const key of Object.keys(outflows[0].indicators)) {
                indicatorNames.push(key);
            }
        }

        // Make headers for inflows and outflows columns
        const baseline = globals.scenarioData.baseline_value_name
        const inflowHeaders = ["Source", baseline, ...indicatorNames.map(elem => elem)]
        const outflowHeaders = ["Target", baseline, ...indicatorNames.map(elem => elem)]

        // Build inflow headers and inflow items
        let inflowHeadersHTML = ""
        inflowHeadersHTML += "<tr>"
        for (const elem of inflowHeaders) {
            inflowHeadersHTML += `<th>${elem}</th>`
        }
        inflowHeadersHTML += "</tr>"

        // Build inflow items as HTML
        let inflowItemsHTML = ""
        for (const flow of inflows) {
            inflowItemsHTML += "<tr>"
            inflowItemsHTML += `<td>${flow.source_process_id}</td>`
            inflowItemsHTML += `<td>${formatValue(flow.evaluated_value)}</td>`
            for (const name of indicatorNames) {
                inflowItemsHTML += `<td>${formatValue(flow.indicators[name])}</td>`
            }
            inflowItemsHTML += "</tr>"
        }
        if (hasInflows) {
            // Add total row
            inflowItemsHTML += "<tr>"
            inflowItemsHTML += "<td><span style='font-weight: bold'>Total</span></td>"
            inflowItemsHTML += `<td><span style='font-weight: bold'>${formatValue(totalInflowsBaseline)}</span></td>`
            for (const [k, v] of totalInflowsIndicators.entries()) {
                inflowItemsHTML += `<td><span style='font-weight: bold'>${formatValue(v)}</span></td>`
            }
            inflowItemsHTML += "</tr>"
        } else {
            inflowHeadersHTML = "<tr>No inflows</tr>"
        }

        // Build outflow headers and inflow items
        let outflowHeadersHTML = ""
        outflowHeadersHTML += "<tr>"
        for (const elem of outflowHeaders) {
            outflowHeadersHTML += `<th>${elem}</th>`
        }
        outflowHeadersHTML += "</tr>"

        // Build inflow items as HTML
        let outflowItemsHTML = ""
        for (const flow of outflows) {
            outflowItemsHTML += "<tr>"
            outflowItemsHTML += `<td>${flow.target_process_id}</td>`
            outflowItemsHTML += `<td>${formatValue(flow.evaluated_value)}</td>`
            for (const name of indicatorNames) {
                outflowItemsHTML += `<td>${formatValue(flow.indicators[name])}</td>`
            }
            outflowItemsHTML += "</tr>"
        }
        if (hasOutflows) {
            // Add total row
            outflowItemsHTML += "<tr>"
            outflowItemsHTML += "<td><span style='font-weight: bold'>Total</span></td>"
            outflowItemsHTML += `<td><span style='font-weight: bold'>${formatValue(totalOutflowsBaseline)}</span></td>`
            for (const [k, v] of totalOutflowsIndicators.entries()) {
                outflowItemsHTML += `<td><span style='font-weight: bold'>${formatValue(v)}</span></td>`
            }
            outflowItemsHTML += "</tr>"
        } else {
            outflowHeadersHTML = "<tr>No outflows</tr>"
        }

        // Determine type for process
        let nodeType = "Process"
        if (hasStock) {
            nodeType = "Stock"
        }
        if (nodeData.isVirtual) {
            nodeType = "Virtual process"
        }

        // Node tooltip result
        result += `
            <div class="tooltip-wrapper">
                <div class="tooltip-title">${nodeData.name}</div>
                <span class="tooltip-type-title">Type: ${nodeType}</span><br/>
                <span class="tooltip-type-title">ID: ${nodeId}</span><br/>
                <br/>
                <div class="tooltip-body-wrapper">
                    <div class="tooltip-col">
                        ${hasStock ? stockInfoHTML : ""}
                    </div>
                </div>
                <div class="tooltip-body-wrapper">
                    <div class="tooltip-col">
                        <table class="tooltip-table">
                            <span class="tooltip-table-title">Inflows</span><br/>
                            <thead>
                                ${inflowHeadersHTML}
                            </thead>
                            <tbody>
                                ${inflowItemsHTML}
                            </tbody>
                        </table>
                    </div>
                    <br/>
                    <div class="tooltip-col">
                        <span class="tooltip-table-title">Outflows</span><br/>
                        <table class="tooltip-table">
                            <thead>
                                ${outflowHeadersHTML}
                            </thead>
                            <tbody>
                                ${outflowItemsHTML}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        return result;
    }

    if (isLink) {
        // console.log(params)
        const linkData = params.data
        const linkId = params.data.id
        const year = globals.currentYear;
        const flow = globals.yearToFlowIdToFlow.get(year).get(linkId)

        // Flow indicators
        const indicatorNameToValue = new Map()
        for(const [k, v] of Object.entries(flow.indicators)) {
            indicatorNameToValue.set(k, v)
        }

        const baseline = globals.scenarioData.baseline_value_name
        const headers = ["Source", "Target", baseline, ...indicatorNameToValue.keys().map(elem => elem)]

        // Build headers
        let headersHTML = ""
        headersHTML += "<tr>"
        for(const entry of headers) {
            headersHTML += `<th>${entry}</th>`
        }
        headersHTML += "</tr>"

        // Build data rows
        let bodyHTML = ""
        bodyHTML += `<td>${flow.source_process_id}</td>`
        bodyHTML += `<td>${flow.target_process_id}</td>`
        bodyHTML += `<td>${formatValue(flow.evaluated_value)}</td>`
        for(const [k, v] of indicatorNameToValue.entries()) {
            bodyHTML += `<td>${formatValue(v)}</td>`
        }

        // Determine the type of the link
        let linkType = "Flow"
        if (linkData.isVirtual) {
            linkType = "Virtual flow"
        }

        // Flow tooltip result
        result += `
        <div class="tooltip-wrapper">
            <div class="tooltip-title">${linkData.name}</div>
            <span class="tooltip-type-title">Type: ${linkType}</span><br/>
            <span class="tooltip-type-title">ID: ${linkId}</span><br/>
            <br/>
            <div class="tooltip-body-wrapper">
                <div class="tooltip-col">
                    <table class="tooltip-table">
                        <span class="tooltip-table-title">Flow</span><br/>
                        <thead>
                            ${headersHTML}
                        </thead>
                        <tbody>
                            ${bodyHTML}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
        return result
    }
}

// *******************
// * Event listeners *
// *******************

// Resize chart when window size has changed
addEventListener("resize", (e) => {
    chart.resize();
});

// Listen when user changes process label type
document
    .getElementById("processLabelType")
    .addEventListener("change", (event) => {
        const value = event.target.options[event.target.selectedIndex].value;
        switch (value) {
            case "id":
                globals.useProcessIdAsLabel = true;
                break;

            case "label":
                globals.useProcessIdAsLabel = false;
                break;
        }

        // Toggle between node ID and node label for all years
        for (const year of globals.years) {
            const yearData = getYearData(year);
            for (const [nodeIndex, nodeData] of yearData.data.entries()) {
                if (globals.useProcessIdAsLabel) {
                    nodeData.name = nodeData.id
                } else {
                    if (nodeData.label) {
                        nodeData.name = nodeData.label
                    } else {
                        nodeData.name = `Missing label (${nodeData.id})`;
                    }
                }
            }
        }

        chart.setOption(globals.initialOption);
    });

document
    .getElementById("flowLabelType")
    .addEventListener("change", (event) => {
        const value = event.target.options[event.target.selectedIndex].value;
        switch (value) {
            case "type":
                globals.useFlowTypeAsLabel = true
                break;

            case "value":
                globals.useFlowTypeAsLabel = false
                break;
        }

        chart.setOption(globals.initialOption);
    });

document
    .getElementById("useTransformationStageColors")
    .addEventListener("change", (event) => {
        const value = event.target.options[event.target.selectedIndex].value;
        switch (value) {
            case "yes":
                globals.useTransformationStageColors = true
                break;

            case "no":
                globals.useTransformationStageColors = false
                break;
        }

        update({resetView: false})
    });

document
    .getElementById("hideUnconnectedProcesses")
    .addEventListener("change", (event) => {
        const value = event.target.options[event.target.selectedIndex].value;
        switch (value) {
            case "yes":
                globals.hideUnconnectedProcesses = true;
                break;
            case "no":
                globals.hideUnconnectedProcesses = false;
                break;
        }

        globals.initialOption.options = [];
        for (const year of globals.years) {
            const graphData = buildGraphDataForYear(year, {});
            const newSeries = {
                series: [
                    {
                        data: graphData.data,
                        links: graphData.links,
                        categories: graphData.categories,
                    },
                ],
            };
            globals.initialOption.options.push(newSeries);
        }

        const currentYearData = buildGraphDataForYear(globals.currentYear);
        globals.initialOption.baseOption.legend[0].data =
            currentYearData.legendData;
        globals.initialOption.baseOption.timeline.data = globals.years;
        chart.setOption(globals.initialOption);

        // // Same as update
        // const graphData = buildGraphDataForYear(globals.currentYear)
        // const option = buildOption(graphData, { resetView: false })
    });

document.getElementById("resetView").addEventListener("click", (event) => {
    // Set default unfreezed state for nodes
    setFreezeNodePositionButtonState("Freeze", false);
    update({resetView: true});
});

document
    .getElementById("freezeNodePositions")
    .addEventListener("click", (event) => {
        const nextState = !globals.freezeNodePositions;
        if (nextState) {
            setFreezeNodePositionButtonState("Unfreeze", nextState);
            freezeNodePositions();
        } else {
            setFreezeNodePositionButtonState("Freeze", nextState);
            unfreezeNodePositions();
        }
    });

// **************************
// * ECharts event handlers *
// **************************

chart.on("timelinechanged", function (params) {
    const targetYear = globals.years[params.currentIndex];
    changeCurrentYear(targetYear);
});

chart.on("mousedown", {dataType: "node"}, (params) => {
    globals.selectedNodeIndex = params.dataIndex;
});

chart.on("mousemove", {dataType: "node"}, (params) => {
    if (!globals.selectedNodeIndex) {
        return;
    }

    const yearData = getYearData(globals.currentYear);
    const nodeId = yearData.data[globals.selectedNodeIndex].id;
    const nodePosition = calculateNodePosition(nodeId);
    setNodePosition(globals.currentYear, nodeId, nodePosition);
});

chart.on("mouseup", {dataType: "node"}, (params) => {
    globals.selectedNodeIndex = null;
});

// *************
// * Functions *
// *************

function getYearIndex(year) {
    return parseInt(year - globals.years[0]);
}

function getYearData(year) {
    const yearIndex = getYearIndex(year);
    return globals.initialOption.options[yearIndex].series[0];
}

function setFreezeNodePositionButtonState(title, state) {
    const label = document.getElementById("freezeNodePositionsButtonLabel");
    globals.freezeNodePositions = state;
    label.innerHTML = title;
}

function getGraphNodeFromNodeData(year, nodeIndex) {
    // Unpack Process data as Node data
    const yearData = globals.yearToData.get(year);
    const nodeIndexToData = yearData.get("nodeIndexToData");
    const nodeIdToPosition = yearData.get("nodeIdToPosition");
    const nodeData = nodeIndexToData.get(nodeIndex);
    const processId = nodeData.process_id;
    const newGraphNode = {
        id: processId,
        name: processId,
        label: nodeData.process_label,
        category: processId,
        numInflows: parseInt(nodeData.num_inflows),
        numOutflows: parseInt(nodeData.num_outflows),
        value: 0,
        text: `Process ${processId}`,

        transformationStage: nodeData.transformation_stage,
        isStock: nodeData.is_stock,
        stockLifetime: nodeData.stock_lifetime,
        stockDistributionType: nodeData.stock_distribution_type,
        stockDistributionParams: nodeData.stock_distribution_params,

        // Colors, injected at initialize
        colorNormal: nodeData.color_normal,
        colorTransformationStage: nodeData.color_transformation_stage,

        // Default color, created at startup
        isVirtual: nodeData.is_virtual,

        // ECharts related
        itemStyle: {}
    };

    // Make virtual nodes dark grey
    if (newGraphNode.isVirtual) {
        newGraphNode.itemStyle = {
            color: globals.virtualNodeColor,
        };
    }

    // Make border for nodes that has stock
    if (newGraphNode.isStock) {
        newGraphNode.itemStyle.borderColor = "#333"
        newGraphNode.itemStyle.borderWidth = 3
    }

    if (nodeIdToPosition.has(processId)) {
        const nodePosition = nodeIdToPosition.get(processId);
        newGraphNode.x = nodePosition.x;
        newGraphNode.y = nodePosition.y;
    }

    const hasColorNormal = newGraphNode.colorNormal !== undefined
    const hasColorTransformationStage = newGraphNode.colorTransformationStage !== undefined
    if(!newGraphNode.isVirtual) {
        if(globals.useTransformationStageColors) {
            if(hasColorTransformationStage) {
                newGraphNode.itemStyle.color = newGraphNode.colorTransformationStage
            }
        } else {
            if(hasColorNormal) {
                newGraphNode.itemStyle.color = newGraphNode.colorNormal
            }
        }
    }

    return newGraphNode;
}

function getGraphEdgeFromEdgeData(edgeIndex, year) {
    const yearData = globals.yearToData.get(year);
    const edgeIndexToData = yearData.get("edgeIndexToData");
    const edgeData = edgeIndexToData.get(edgeIndex);

    const flowId = edgeData.flow_id;
    const sourceProcessId = edgeData.source_process_id;
    const targetProcessId = edgeData.target_process_id;
    const isUnitAbsoluteValue = edgeData.is_unit_absolute_value;
    const value = edgeData.value;
    const unit = edgeData.unit;

    const newGraphEdge = {
        id: flowId,
        name: flowId,
        source: sourceProcessId,
        target: targetProcessId,
        label: {
            id: edgeData.flow_id,
            show: true,
            position: "middle",
            formatter: (params) => {
                // Format text for links
                if (globals.useFlowTypeAsLabel) {
                    return isUnitAbsoluteValue ? "ABS" : "%";
                } else {
                    return formatValue(edgeData.evaluated_value)
                }
            },
        },
        lineStyle: {
            color: isUnitAbsoluteValue
                ? globals.edgeColors.absolute
                : globals.edgeColors.relative,
            // width can be used to change line width
        },

        // Custom data
        text: isUnitAbsoluteValue ? "Absolute flow" : "Relative flow",
        value: `${value} ${unit}`,

        isVirtual: edgeData.is_virtual,
    };

    if (newGraphEdge.isVirtual) {
        newGraphEdge.lineStyle.color = globals.virtualFlowColor;
    }

    return newGraphEdge;
}

function buildGraphDataForYear(year, updateOptions = {}) {
    const graphData = {
        data: [],
        links: [],
        categories: [],
        legendData: [],
    };

    const yearData = globals.yearToData.get(year);

    const nodeIndexToData = yearData.get("nodeIndexToData");
    for (const [nodeIndex, nodeData] of nodeIndexToData.entries()) {
        const graphNode = getGraphNodeFromNodeData(year, nodeIndex);
        if (globals.hideUnconnectedProcesses) {
            const hasNoInflows = graphNode.numInflows === 0;
            const hasNoOutflows = graphNode.numOutflows === 0;
            if (hasNoInflows && hasNoOutflows) {
                continue;
            }
        }

        if (globals.useProcessIdAsLabel) {
            graphNode.name = graphNode.id;
        } else {
            if (graphNode.label) {
                graphNode.name = graphNode.label;
            } else {
                graphNode.name = `Missing label (${graphNode.id})`;
            }
        }

        graphData.data.push(graphNode);
    }

    // Sort graphs in alphabetical order so legend is also in alphabetical order
    graphData.data.sort((a, b) => a.name > b.name ? 1 : -1);

    const edgeIndexToData = yearData.get("edgeIndexToData");
    for (const [edgeIndex, edgeData] of edgeIndexToData.entries()) {
        const graphEdge = getGraphEdgeFromEdgeData(edgeIndex, year);
        graphData.links.push(graphEdge);
    }

    // Color nodes by categories
    for (const node of graphData.data) {
        const newCategory = {
            name: node.id,
            itemStyle: {}
        };

        const hasColorNormal = node.colorNormal !== undefined
        const hasColorTransformationStage = node.colorTransformationStage !== undefined
        if(!node.isVirtual) {
            if(globals.useTransformationStageColors) {
                if(hasColorTransformationStage) {
                    newCategory.itemStyle.color = node.colorTransformationStage
                }
            } else {
                if(hasColorNormal) {
                    newCategory.itemStyle.color = node.colorNormal
                }
            }
        }

        graphData.categories.push(newCategory);
    }

    // Create legend from all visible nodes
    const legendData = []
    for (const node of graphData.data) {
        const newEntry = {
            name: node.id,
            itemStyle: node.itemStyle,
            tooltip: {
                show: true,
                formatter: getTooltipFormatter,
            }
        }
        legendData.push(newEntry)
    }

    // Build legend data - ECharts uses automatically node ID with this
    graphData.legendData = legendData;
    return graphData;
}

function buildOption(graphData, updateOptions = {resetView: false}) {
    const center = ["50%", "50%"];
    if (!updateOptions.resetView) {
        // Use previous center
        const prevOption = chart.getOption();
        const prevCenter = prevOption.series[0].center;
        center[0] = prevCenter[0];
        center[1] = prevCenter[1];
    }

    let layout = globals.freezeNodePositions ? "none" : "force";
    if (updateOptions.resetView) {
        layout = "force";
    }
    const option = {
        options: [{
            series: [{
                name: "Process flows test",
                //                 type: "graph",
                //                 layout: layout,
                data: graphData.data,
                links: graphData.links,
                categories: graphData.categories,
                //                 center: center,
                //                 zoom: zoom: 2,
                //                 draggable: true,
                //                 symbolSize: 40,
                //                 symbol: "circle", // 'rect'
                //                 label: {
                //                     show: true, // node name to be shown in circle
                //                 },
                //                 edgeSymbol: ["circle", "arrow"], // for arrow from one to another
                //                 edgeSymbolSize: [0, 15],
                //                 emphasis: {
                //                     focus: "adjacency",
                //                     label: {
                //                         show: true,
                //                     },
                //                     // disabled: true,
                //                 },
                //                 roam: true,
                //                 force: {
                //                     repulsion: [500, 1000, 2000],
                //                     edgeLength: 50,
                //                 },
                //             },
            }]
        }]
    }

    // // graphData is year-specific data
    // const option = {
    //     baseOption: {
    //         title: {
    //             text: "Process connection graph",
    //             subtext: `Year ${globals.currentYear}`,
    //         },
    //         tooltip: {
    //             formatter: getTooltipFormatter,
    //         },
    //         legend: [
    //             {
    //                 type: "scroll",
    //                 data: graphData.legendData,
    //                 position: "left",
    //                 orient: "vertical",
    //                 right: 10,
    //                 top: 50,
    //                 height: "88%",
    //             },
    //         ],
    //         timeline: {
    //             show: true,
    //             type: "slider",
    //             axisType: "category",
    //             data: globals.years,
    //             left: "20px",
    //             right: "20px",
    //         },
    //         series: [
    //             {
    //                 name: "Process flows",
    //                 type: "graph",
    //                 layout: layout,
    //                 data: graphData.data,
    //                 links: graphData.links,
    //                 categories: graphData.categories,
    //                 center: center,
    //                 zoom: 2,
    //                 draggable: true,
    //                 symbolSize: 40,
    //                 symbol: "circle", // 'rect'
    //                 label: {
    //                     show: true, // node name to be shown in circle
    //                 },
    //                 edgeSymbol: ["circle", "arrow"], // for arrow from one to another
    //                 edgeSymbolSize: [0, 15],
    //                 emphasis: {
    //                     focus: "adjacency",
    //                     label: {
    //                         show: true,
    //                     },
    //                     // disabled: true,
    //                 },
    //                 roam: true,
    //                 force: {
    //                     repulsion: [500, 1000, 2000],
    //                     edgeLength: 50,
    //                 },
    //             },
    //         ],
    //     },
    //     options: [],
    // };

    return option;
}

// Initialize data
function initialize() {
    globals.years = Object.keys(globals.originalYearToData);
    globals.currentYear = globals.years[0];
    globals.currentYearIndex = 0

    const yearToProcessIdToProcess = new Map();
    const yearToProcessIdToFlowIds = new Map();
    const yearToFlowIdToFlow = new Map();

    // Create data mapping for each year
    const yearToData = new Map();
    for (const year of globals.years) {
        const yearData = new Map();
        const nodeData = {
            ...globals.originalYearToData[year]["node_index_to_data"],
        };
        const edgeData = {
            ...globals.originalYearToData[year]["edge_index_to_data"],
        };

        // Year -> Process Id and Flow ID -> Process/Flow
        yearToProcessIdToProcess.set(year, new Map());
        yearToFlowIdToFlow.set(year, new Map());
        yearToProcessIdToFlowIds.set(year, new Map());

        // Map node index to node data
        const nodeIdToNodeIndex = new Map();
        const nodeIndexToData = new Map();
        for (const key of Object.keys(nodeData)) {
            const nodeIndex = parseInt(key);
            const node = nodeData[nodeIndex];
            const nodeId = node.process_id;
            nodeIndexToData.set(nodeIndex, node);
            nodeIdToNodeIndex.set(nodeId, nodeIndex);

            // Year -> Process ID -> Process
            const processIdToProcess = yearToProcessIdToProcess.get(year);
            processIdToProcess.set(nodeId, node);

            // Year -> Process ID -> Flow IDs
            const processIdToFlowIds = yearToProcessIdToFlowIds.get(year);
            processIdToFlowIds.set(nodeId, {in: [], out: []});
        }

        // Map edge index to edge data
        const edgeIndexToData = new Map();
        const edgeIdToData = new Map();
        for (const key of Object.keys(edgeData)) {
            const edgeIndex = parseInt(key);
            const edge = edgeData[edgeIndex];
            const edgeId = edge.flow_id;
            edgeIndexToData.set(edgeIndex, edge);
            edgeIdToData.set(edgeId, edge);

            // Year -> Flow ID -> Flow
            const flowIdToFlow = yearToFlowIdToFlow.get(year);
            flowIdToFlow.set(edgeId, edge);
        }

        // Year -> Process ID -> Flow IDs
        for (const [flowId, flow] of yearToFlowIdToFlow.get(year).entries()) {
            const sourceProcessId = flow.source_process_id;
            const sourceProcessEntry = yearToProcessIdToFlowIds
                .get(year)
                .get(sourceProcessId);
            sourceProcessEntry.out.push(flowId);

            const targetProcessId = flow.target_process_id;
            const targetProcessEntry = yearToProcessIdToFlowIds
                .get(year)
                .get(targetProcessId);
            targetProcessEntry.in.push(flowId);
        }

        yearData.set("nodeIndexToData", nodeIndexToData);
        yearData.set("nodeIdToIndex", nodeIdToNodeIndex);
        yearData.set("edgeIndexToData", edgeIndexToData);
        yearData.set("edgeIdToData", edgeIdToData);
        yearData.set("nodeIdToPosition", new Map([]));
        yearToData.set(year, yearData);
    }

    // Build transformation stage name to color mapping
    for(const [k, v] of Object.entries(globals.scenarioData.transformation_stage_name_to_color)) {
        globals.transformationStageNameToColor.set(k, v)
    }

    // Update scenario name
    globals.scenarioName = globals.scenarioData.scenario_name

    globals.yearToData = yearToData;
    globals.yearToProcessIdToProcess = yearToProcessIdToProcess;
    globals.yearToFlowIdToFlow = yearToFlowIdToFlow;
    globals.yearToProcessIdToFlowIds = yearToProcessIdToFlowIds;

    // Create option for ECharts
    const center = ["50%", "50%"];
    let layout = globals.freezeNodePositions ? "none" : "force";
    const option = {
        baseOption: {
            title: {
                text: `${globals.scenarioName}`,
                subtext: `Year ${globals.currentYear}`,
                textStyle: {
                    color: "#000",
                    fontSize: 20,
                    fontWeight: 'bold',
                },
                subtextStyle: {
                    color: "#000",
                    fontSize: 16,
                    fontWeight: 'bold',
                }
            },
            tooltip: {
                formatter: getTooltipFormatter,
            },
            legend: [
                {
                    type: "scroll",
                    data: [],
                    position: "left",
                    orient: "vertical",
                    right: 10,
                    top: 50,
                    height: "88%",
                },
            ],
            timeline: {
                show: true,
                type: "slider",
                currentIndex: 0,
                axisType: "category",
                data: [],
                left: "20px",
                right: "20px",
            },
            series: [
                {
                    name: "Process flows",
                    type: "graph",
                    layout: "force",
                    data: [],
                    links: [],
                    categories: [],
                    center: center,
                    zoom: 2,
                    draggable: true,
                    symbolSize: 40,
                    symbol: "circle", // 'rect'
                    label: {
                        show: true, // node name to be shown in circle
                    },
                    edgeSymbol: ["circle", "arrow"], // for arrow from one to another
                    edgeSymbolSize: [0, 15],
                    emphasis: {
                        focus: "adjacency",
                        label: {
                            show: true,
                        },
                        // disabled: true,
                    },
                    roam: true,
                    force: {
                        repulsion: [500, 1000, 2000],
                        edgeLength: 50,
                    },
                },
            ],
        },
        options: [],
    };

    // Build years and insert to options
    for (const year of globals.years) {
        const graphData = buildGraphDataForYear(year, {});
        const newSeries = {
            series: [
                {
                    data: graphData.data,
                    links: graphData.links,
                    categories: graphData.categories,
                },
            ],
        };
        option.options.push(newSeries);
    }

    // Get first year data and activate it
    const currentYearData = buildGraphDataForYear(globals.currentYear);
    option.baseOption.timeline.currentIndex = 0
    option.baseOption.legend[0].data = currentYearData.legendData;
    option.baseOption.timeline.data = globals.years;

    // Store reference to original option
    // This is needed when changed years
    globals.initialOption = option;
    chart.setOption(globals.initialOption);

    // Build node colors by reading back the default node colors after rendering
    // first time and retrieve node colors
    const nodeInfos = []
    const model = chart.getModel()
    const series = model.getSeriesByIndex(0)
    const data = series.getData()
    data.each((index) => {
        const name = data.getName(index)
        const color = data.getItemVisual(index, "style").fill
        nodeInfos.push({ id: name, color: color })
    })

    // Set colors for every year
    for(const year of globals.years) {
        const yearData = globals.yearToData.get(year);
        const nodeIdToIndex = yearData.get("nodeIdToIndex")
        const nodeIndexToData = yearData.get("nodeIndexToData")
        for(const entry of nodeInfos) {
            const nodeId = entry.id
            const nodeColor = entry.color
            const nodeIndex = nodeIdToIndex.get(nodeId)
            const nodeData = nodeIndexToData.get(nodeIndex)

            // TODO: In year 1963 there is "Dissolving_pulp:Export" but that is not defined
            // in the original data?
            // Inject properties "color_normal" and "color_transformation_stage" to original node data
            if(nodeData == undefined) {
                console.log(nodeId)
                console.log(nodeIdToIndex.keys())
                console.log(year)
            }

            const transformationStageName = nodeData.transformation_stage
            nodeData["color_normal"] = nodeColor
            nodeData["color_transformation_stage"] = globals.transformationStageNameToColor.get(transformationStageName)
        }
    }

    if(globals.useTransformationStageColors) {
        update({ resetView: false })
    }
}

function update(updateOptions = {resetView: false}) {
    // // TODO: This is called from reset resetView and formatter for
    // const graphData = buildGraphDataForYear(globals.currentYear);
    // const option = buildOption(graphData, updateOptions);
    // chart.setOption(option);
    // // chart.setOption(option, { notMerge: true });
    // // chart.setOption(option, { replaceMerge: ["options"] });
    // globals.graphData = graphData;

    // Update current year data used in globals.initialOption
    const graphData = buildGraphDataForYear(globals.currentYear);
    const option = globals.initialOption.options[globals.currentYearIndex]
    option.series[0].data = graphData.data
    option.series[0].links = graphData.links
    option.series[0].categories = graphData.categories
    chart.setOption(globals.initialOption)
    globals.graphData = graphData;
}

function freezeNodePositions() {
    // Update current year nodes' position
    const yearData = getYearData(globals.currentYear);
    for (const [nodeIndex, nodeData] of yearData.data.entries()) {
        const nodePosition = calculateNodePosition(nodeData.id);
        setNodePosition(globals.currentYear, nodeData.id, nodePosition);
    }

    const model = chart.getModel()
    const series = model.getSeriesByIndex(0)
    const coordSys = series.coordinateSystem
    const zoom = coordSys.getZoom()
    const center = coordSys.getCenter()
    globals.initialOption.baseOption.series[0].layout = "none";
    globals.initialOption.baseOption.series[0].zoom = zoom
    globals.initialOption.baseOption.series[0].center = center
    chart.setOption(globals.initialOption);
}

function unfreezeNodePositions() {
    // Update current year nodes' position
    const yearData = getYearData(globals.currentYear);
    for (const [nodeIndex, nodeData] of yearData.data.entries()) {
        const nodePosition = calculateNodePosition(nodeData.id);
        setNodePosition(globals.currentYear, nodeData.id, nodePosition);
    }

    const model = chart.getModel()
    const series = model.getSeriesByIndex(0)
    const coordSys = series.coordinateSystem
    const zoom = coordSys.getZoom()
    const center = coordSys.getCenter()
    globals.initialOption.baseOption.series[0].layout = "force";
    globals.initialOption.baseOption.series[0].zoom = zoom
    globals.initialOption.baseOption.series[0].center = center
    chart.setOption(globals.initialOption);
}

function getNodePosition(year, nodeId) {
    const yearIndex = getYearIndex(year);
    const yearData = globals.initialOption.options[yearIndex].series[0];
    for (const [nodeIndex, nodeData] of yearData.data.entries()) {
        if (nodeData.id == nodeId) {
            return {x: nodeData.x, y: nodeData.y};
        }
    }

    console.log(`No node ${nodeId} at year ${year}`);
}

function setNodePosition(year, nodeId, nodePosition) {
    const yearIndex = getYearIndex(year);
    const yearData = globals.initialOption.options[yearIndex].series[0];
    for (const [nodeIndex, nodeData] of yearData.data.entries()) {
        if (nodeData.id == nodeId) {
            nodeData.x = nodePosition.x;
            nodeData.y = nodePosition.y;
            return;
        }
    }

    // NOTE: Virtual flows might not be found for every year so no error here
    //   console.log(`No node ${nodeId} at year ${year}`);
}

function calculateNodePosition(nodeId) {
    const nodeIdToPosition = new Map();

    const nodes = chart.getModel().getSeriesByIndex(0).getData();
    nodes.each(function (nodeIndex) {
        const nodeData = nodes.getRawDataItem(nodeIndex);
        const nodeLayout = nodes.getItemLayout(nodeIndex);
        const nodePosition = {x: nodeLayout[0], y: nodeLayout[1]};
        nodeIdToPosition.set(nodeData.id, nodePosition);
    });

    if (!nodeIdToPosition.has(nodeId)) {
        // NOTE: Virtual flows might not be found for every year so
        // console.error(`No node ${nodeId} found in year ${globals.currentYear}!`);
        return {x: 0.0, y: 0.0};
    }

    const nodePosition = nodeIdToPosition.get(nodeId);
    return {x: nodePosition.x, y: nodePosition.y};
}

function changeCurrentYear(targetYear) {
    // Save current year nodes' position
    const currentYearData = getYearData(globals.currentYear);
    for (const [nodeIndex, nodeData] of currentYearData.data.entries()) {
        const nodePosition = calculateNodePosition(nodeData.id);
        setNodePosition(globals.currentYear, nodeData.id, nodePosition);
    }

    const targetYearData = getYearData(targetYear);
    for (const [nodeIndex, nodeData] of currentYearData.data.entries()) {
        const nodePosition = getNodePosition(targetYear, nodeData.id);
        setNodePosition(targetYear, nodeData.id, nodePosition);
    }

    // Update year and chart
    const yearIndex = getYearIndex(targetYear);
    globals.currentYear = targetYear;
    globals.currentYearIndex = yearIndex
    globals.initialOption.baseOption.timeline.currentIndex = yearIndex;
    globals.initialOption.baseOption.title.subtext = `Year ${globals.currentYear}`;
    update({ resetView: false})
}

console.log("Initializing...");
initialize();
console.log("Done.");

//   chart.dispatchAction({
//     type: 'highlight',
//     batch: [
//       { dataType: 'node', dataIndex: nodeDataIndex},
//       { dataType: 'edge', dataIndex: edgeDataIndex, notBlur: true},
//     ],
//   })
// })
