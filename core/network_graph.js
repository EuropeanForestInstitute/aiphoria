const chart = echarts.init(document.getElementById("main"));

// ***************
// * Global data *
// ***************

// Global variables
const globals = {
  // Original data, this will get replaced with JSON object from Python
  originalYearToData: {year_to_data},

  // Updated year to data: contains various mappings e.g. node ID to position
  yearToData: new Map(),

  // Edge colors
  edgeColors: {
    absolute: "rgba(59, 162, 114, 1)",
    relative: "rgba(255, 50, 50, 1)",
  },

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

  // If true, hide processes that have no inflows and outflows
  hideUnconnectedProcesses: false,

  // Freeze node positions, disabled by default to allow force layout
  // to find node positions
  freezeNodePositions: false,
};


// *******************
// * Event listeners *
// *******************

// Resize chart when window size has changed
addEventListener("resize", (e) => {
  chart.resize();
});

// Listen when user changes process label type
document.getElementById("processLabelType").addEventListener("change", (event) => {
  const value = event.target.options[event.target.selectedIndex].value
  switch(value) {
    case "id":
      globals.useProcessIdAsLabel = true
      break

    case "label":
      globals.useProcessIdAsLabel = false
      break
  }

  // Toggle between node ID and node label for all years
  for(const year of globals.years) {
    const yearData = getYearData(year)
    for (const [nodeIndex, nodeData] of yearData.data.entries()) {
      if (globals.useProcessIdAsLabel) {
        nodeData.name = nodeData.id
      } else {
        if (nodeData.label) {
          nodeData.name = nodeData.label
        } else {
          nodeData.name = `Missing label (${nodeData.id})`
        }
      }
    }
  }

  chart.setOption(globals.initialOption)
})

document.getElementById("hideUnconnectedProcesses").addEventListener("change", (event) => {
  const value = event.target.options[event.target.selectedIndex].value
  switch(value) {
    case "yes":
      globals.hideUnconnectedProcesses = true
      break
    case "no":
      globals.hideUnconnectedProcesses = false
      break
  }

  globals.initialOption.options = []
  for(const year of globals.years) {
  const graphData = buildGraphDataForYear(year, {})
    const newSeries = {
      series: [{
        data: graphData.data,
        links: graphData.links,
        categories: graphData.categories,
      }]
    }
    globals.initialOption.options.push(newSeries)
  }

  const currentYearData = buildGraphDataForYear(globals.currentYear)
  globals.initialOption.baseOption.legend[0].data = currentYearData.legendData
  globals.initialOption.baseOption.timeline.data = globals.years
  chart.setOption(globals.initialOption)

  // // Same as update
  // const graphData = buildGraphDataForYear(globals.currentYear)
  // const option = buildOption(graphData, { resetView: false })
})

document.getElementById("resetView").addEventListener("click", (event) => {
  // Set default unfreezed state for nodes
  setFreezeNodePositionButtonState("Freeze", false)
  update({ resetView: true })
})

document.getElementById("freezeNodePositions").addEventListener("click", (event) => {
  const nextState = !globals.freezeNodePositions
  if(nextState) {
    setFreezeNodePositionButtonState("Unfreeze", nextState)
    freezeNodePositions()
  } else {
    setFreezeNodePositionButtonState("Freeze", nextState)
    unfreezeNodePositions()
  }
})


// **************************
// * ECharts event handlers *
// **************************

chart.on("timelinechanged", function (params) {
  const targetYear = globals.years[params.currentIndex]
  changeCurrentYear(targetYear)
});

chart.on("mousedown", { dataType: "node" }, (params) => {
  globals.selectedNodeIndex = params.dataIndex
})

chart.on("mousemove", { dataType: "node" }, (params) => {
  if(!globals.selectedNodeIndex) {
    return
  }

  const yearData = getYearData(globals.currentYear)
  const nodeId = yearData.data[globals.selectedNodeIndex].id
  const nodePosition = calculateNodePosition(nodeId)
  setNodePosition(globals.currentYear, nodeId, nodePosition)
})

chart.on("mouseup", { dataType: "node" }, (params) => {
  globals.selectedNodeIndex = null
})


// *************
// * Functions *
// *************

function getYearIndex(year) {
  return parseInt(year - globals.years[0])
}

function getYearData(year) {
  const yearIndex = getYearIndex(year)
  return globals.initialOption.options[yearIndex].series[0]
}

function setFreezeNodePositionButtonState(title, state) {
  const label = document.getElementById("freezeNodePositionsButtonLabel")
  globals.freezeNodePositions = state
  label.innerHTML = title
}

function getGraphNodeFromNodeData(year, nodeIndex) {
  const yearData = globals.yearToData.get(year)
  const nodeIndexToData = yearData.get("nodeIndexToData")
  const nodeIdToPosition = yearData.get("nodeIdToPosition")
  const nodeData = nodeIndexToData.get(nodeIndex)

  const processId = nodeData.process_id
  const processLabel = nodeData.process_label
  const numInflows = parseInt(nodeData.num_inflows)
  const numOutflows = parseInt(nodeData.num_outflows)
  const newGraphNode = {
    id: processId,
    name: processId,
    label: processLabel,
    category: processId,
    numInflows: numInflows,
    numOutflows: numOutflows,
    value: 0,
    text: `Process ${processId}`,
  }

  if(nodeIdToPosition.has(processId)) {
    const nodePosition = nodeIdToPosition.get(processId)
    newGraphNode.x = nodePosition.x
    newGraphNode.y = nodePosition.y
  }

  return newGraphNode
}

function getGraphEdgeFromEdgeData(edgeIndex, year) {
  const yearData = globals.yearToData.get(year)
  const edgeIndexToData = yearData.get("edgeIndexToData")
  const edgeData = edgeIndexToData.get(edgeIndex)

  const sourceProcessId = edgeData.source_process_id;
  const targetProcessId = edgeData.target_process_id;
  const isUnitAbsoluteValue = edgeData.is_unit_absolute_value;
  const value = edgeData.value;
  const unit = edgeData.unit;

  const newGraphEdge = {
    source: sourceProcessId,
    target: targetProcessId,
    label: {
      show: true,
      position: "middle",
      formatter: (params) => {
        return isUnitAbsoluteValue ? "ABS" : "%";
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
  }

  return newGraphEdge
}

function buildGraphDataForYear(year, updateOptions = {}) {
  const graphData = {
    data: [],
    links: [],
    categories: [],
    legendData: [],
  }

  const yearData = globals.yearToData.get(year)

  const nodeIndexToData = yearData.get("nodeIndexToData");
  for(const [nodeIndex, nodeData] of nodeIndexToData.entries()) {
    const graphNode = getGraphNodeFromNodeData(year, nodeIndex)

    if(globals.hideUnconnectedProcesses) {
      const hasNoInflows = graphNode.numInflows === 0
      const hasNoOutflows = graphNode.numOutflows === 0
      if(hasNoInflows && hasNoOutflows) {
        continue
      }
    }

    if(globals.useProcessIdAsLabel) {
      graphNode.name = graphNode.id
    } else {
      if(graphNode.label) {
        graphNode.name = graphNode.label
      } else {
        graphNode.name = `Missing label (${graphNode.id})`
      }
    }

    graphData.data.push(graphNode)
  }

  const edgeIndexToData = yearData.get("edgeIndexToData");
  for(const [edgeIndex, edgeData] of edgeIndexToData.entries()) {
    const graphEdge = getGraphEdgeFromEdgeData(edgeIndex, year)
    graphData.links.push(graphEdge)
  }

  for(const node of graphData.data) {
    const newCategory = {
      name: node.id
    }
    graphData.categories.push(newCategory)
  }

  const visibleNodeIds = []
  for(const node of graphData.data) {
    visibleNodeIds.push(node.id)
  }

  // Build legend data - ECharts uses automatically node ID with this
  graphData.legendData = visibleNodeIds;
  return graphData;
}


function buildOption(graphData, updateOptions = { resetView: false }) {
  const center = ["50%", "50%"]
  if(!updateOptions.resetView) {
    // Use previous center
    const prevOption = chart.getOption()
    const prevCenter = prevOption.series[0].center
    center[0] = prevCenter[0]
    center[1] = prevCenter[1]
  }

  let layout = globals.freezeNodePositions ? "none" : "force"
  if(updateOptions.resetView) {
    layout = "force"
  }

  // graphData is year-specific data
  const option = {
    baseOption: {
      title: {
        text: "Process connection graph",
        subtext: `Year ${globals.currentYear}`
      },
      tooltip: {
        formatter: function (params) {
          if (params.dataType == "node") {
            return;
            // let text = params.data.text
            // return `<div>${text}</div>`
          }

          if (params.dataType === "edge") {
            let text = params.data.text;
            let value = params.data.value;
            return `<div>${text}</div><div>${value}</div>`;
          }
        },
      },
      legend: [
        {
          type: "scroll",
          data: graphData.legendData,
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
        axisType: "category",
        data: globals.years,
        left: "20px",
        right: "20px",
      },
      series: [
        {
          name: "Process flows",
          type: "graph",
          layout: layout,
          data: graphData.data,
          links: graphData.links,
          categories: graphData.categories,
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

  return option;
}

// Initialize data
function initialize() {
  globals.years = Object.keys(globals.originalYearToData);
  globals.currentYear = globals.years[0];

  // Create data mapping for each year
  const yearToData = new Map()
  for(const year of globals.years) {
    const yearData = new Map()
    const nodeData = {...globals.originalYearToData[year]["node_index_to_data"]}
    const edgeData = {...globals.originalYearToData[year]["edge_index_to_data"]}

    // Map node index to node data
    const nodeIdToNodeIndex = new Map()
    const nodeIndexToData = new Map()
    for (const key of Object.keys(nodeData)) {
      const nodeIndex = parseInt(key)
      const node = nodeData[nodeIndex]
      const nodeId = node.process_id
      nodeIndexToData.set(nodeIndex, node)
      nodeIdToNodeIndex.set(nodeId, nodeIndex)
    }

    // Map edge index to edge data
    const edgeIndexToData = new Map()
    for (const key of Object.keys(edgeData)) {
      const edgeIndex = parseInt(key)
      const edge = edgeData[edgeIndex];
      edgeIndexToData.set(edgeIndex, edge)
    }

    yearData.set("nodeIndexToData", nodeIndexToData)
    yearData.set("nodeIdToIndex", nodeIdToNodeIndex)
    yearData.set("edgeIndexToData", edgeIndexToData)
    yearData.set("nodeIdToPosition", new Map([]))
    yearToData.set(year, yearData)
  }

  globals.yearToData = yearToData

  // Create option for ECharts
  const center = ["50%", "50%"]
  let layout = globals.freezeNodePositions ? "none" : "force"
  const option = {
    baseOption: {
      title: {
        text: "Process connection graph",
        subtext: `Year ${globals.currentYear}`
      },
      tooltip: {
        formatter: function (params) {
          if (params.dataType == "node") {
            return;
            // let text = params.data.text
            // return `<div>${text}</div>`
          }

          if (params.dataType === "edge") {
            let text = params.data.text;
            let value = params.data.value;
            return `<div>${text}</div><div>${value}</div>`;
          }
        },
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
  }

  // Build years and insert to options
  for(const year of globals.years) {
  const graphData = buildGraphDataForYear(year, {})
    const newSeries = {
      series: [{
        data: graphData.data,
        links: graphData.links,
        categories: graphData.categories,
      }]
    }
    option.options.push(newSeries)
  }

  const currentYearData = buildGraphDataForYear(globals.currentYear)
  option.baseOption.legend[0].data = currentYearData.legendData
  option.baseOption.timeline.data = globals.years

  // Store reference to original option
  // This is needed for changed the data of the nodes later
  globals.initialOption = option
  chart.setOption(globals.initialOption)
}

function update(updateOptions = { resetView: false }) {
  const graphData = buildGraphDataForYear(globals.currentYear)
  const option = buildOption(graphData, updateOptions)
  chart.setOption(option)
  globals.graphData = graphData
}

function freezeNodePositions() {
  // Update current year nodes' position
  const yearData = getYearData(globals.currentYear)
  for(const [nodeIndex, nodeData] of yearData.data.entries()) {
    const nodePosition = calculateNodePosition(nodeData.id)
    setNodePosition(globals.currentYear, nodeData.id, nodePosition)
  }

  globals.initialOption.baseOption.series[0].layout = "none"
  chart.setOption(globals.initialOption)
}

function unfreezeNodePositions() {
  // Update current year nodes' position
  const yearData = getYearData(globals.currentYear)
  for(const [nodeIndex, nodeData] of yearData.data.entries()) {
    const nodePosition = calculateNodePosition(nodeData.id)
    setNodePosition(globals.currentYear, nodeData.id, nodePosition)
  }

  globals.initialOption.baseOption.series[0].layout = "force"
  chart.setOption(globals.initialOption)
}

function getNodePosition(year, nodeId) {
  const yearIndex = getYearIndex(year)
  const yearData = globals.initialOption.options[yearIndex].series[0]
  for(const [nodeIndex, nodeData] of yearData.data.entries()) {
    if(nodeData.id == nodeId) {
      return { x: nodeData.x, y: nodeData.y }
    }
  }

  console.log(`No node ${nodeId} at year ${year}`)
}

function setNodePosition(year, nodeId, nodePosition) {
  const yearIndex = getYearIndex(year)
  const yearData = globals.initialOption.options[yearIndex].series[0]
  for(const [nodeIndex, nodeData] of yearData.data.entries()) {
    if(nodeData.id == nodeId) {
      nodeData.x = nodePosition.x
      nodeData.y = nodePosition.y
      return
    }
  }

  console.log(`No node ${nodeId} at year ${year}`)
}

function calculateNodePosition(nodeId) {
  const nodeIdToPosition = new Map()

  const nodes = chart.getModel().getSeriesByIndex(0).getData()
  nodes.each(function (nodeIndex) {
    const nodeData = nodes.getRawDataItem(nodeIndex)
    const nodeLayout = nodes.getItemLayout(nodeIndex)
    const nodePosition = { x: nodeLayout[0], y: nodeLayout[1] }
    nodeIdToPosition.set(nodeData.id, nodePosition)
  })

  if(!nodeIdToPosition.has(nodeId)) {
    console.error(`No node ${nodeId} found in year ${globals.currentYear}!`)
    return { x: 0.0, y: 0.0 }
  }

  const nodePosition = nodeIdToPosition.get(nodeId)
  return { x: nodePosition.x, y: nodePosition.y }
}

function changeCurrentYear(targetYear) {
  // Save current year nodes' position
  const currentYearData = getYearData(globals.currentYear)
  for(const [nodeIndex, nodeData] of currentYearData.data.entries()) {
    const nodePosition = calculateNodePosition(nodeData.id)
    setNodePosition(globals.currentYear, nodeData.id, nodePosition)
  }

  const targetYearData = getYearData(targetYear)
  for(const [nodeIndex, nodeData] of currentYearData.data.entries()) {
    const nodePosition = getNodePosition(targetYear, nodeData.id)
    setNodePosition(targetYear, nodeData.id, nodePosition)
  }

  const yearIndex = getYearIndex(targetYear)
  globals.initialOption.baseOption.timeline.currentIndex = yearIndex
  globals.initialOption.baseOption.title.subtext = `Year ${globals.currentYear}`
  chart.setOption(globals.initialOption)
  globals.currentYear = targetYear
}


console.log("Initializing...")
initialize();
console.log("Done.")

//   chart.dispatchAction({
//     type: 'highlight',
//     batch: [
//       { dataType: 'node', dataIndex: nodeDataIndex},
//       { dataType: 'edge', dataIndex: edgeDataIndex, notBlur: true},
//     ],
//   })
// })

