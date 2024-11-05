const chart = echarts.init(document.getElementById("main"));

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

  // Toggle node label type (process ID or label)
  const option = {...chart.getOption()}
  for(const [nodeIndex, node] of option.series[0].data.entries()) {
    if(globals.useProcessIdAsLabel) {
      node.name = node.id
    } else {
      if(node.label) {
        node.name = node.label
      } else {
        node.name = `Missing label (${node.id})`
      }
    }
  }

  chart.setOption(option)
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

  // Rebuild nodes for this year but do not include any nodes that have no inflows AND no outflows
  // 1) Store node ID to position for all nodes
  const nodeIndexToPosition = new Map()
  for(const [nodeIndex, entry] of getNodePositions().entries()) {
    nodeIndexToPosition.set(nodeIndex, entry)
  }

  // Apply current position to all nodes
  // TODO: Not working perfectly yet
  const option = {...chart.getOption()}
  for(const [nodeIndex, node] of option.series[0].data.entries()) {
    const nodePosition = nodeIndexToPosition.get(nodeIndex)
    node.x = nodePosition.x
    node.y = nodePosition.y
  }
  chart.setOption(option)

  updateNew({ resetView: false })
})

document.getElementById("resetView").addEventListener("click", (event) => {
  updateNew({ resetView: true })
})

document.getElementById("freezeNodePositions").addEventListener("click", (event) => {
  const label = document.getElementById("freezeNodePositionsButtonLabel")
  globals.freezeNodePositions = !globals.freezeNodePositions
  if(globals.freezeNodePositions) {
    freezeNodePositions()
    label.innerHTML = "Unfreeze"
  } else {
    unfreezeNodePositions()
    label.innerHTML = "Freeze"
  }
})


// **************************
// * ECharts event handlers *
// **************************

chart.on("timelinechanged", function (params) {
  globals.currentYear = globals.years[params.currentIndex];

  // Reset freeze button
  globals.freezeNodePositions = false
  document.getElementById("freezeNodePositionsButtonLabel").innerHTML = "Freeze"
  updateNew({ resetView: true})
});

chart.on("click", { dataType: "node" }, (params) => {
  // console.log(params)
  // const dataType = params.dataType
  // const seriesIndex = params.seriesIndex
  // const dataIndex = params.dataIndex
  // console.log(dataType, seriesIndex, dataIndex)
  // selectedNodes.push({ seriesIndex: seriesIndex, dataIndex: dataIndex })
})

// chart.on("click", { dataType: "edge" }, (params) => {
//   console.log(params)
// })

let selectedNode = null
chart.on("mousedown", { dataType: "node" }, (params) => {
  selectedNode = {
    seriesIndex: params.seriesIndex,
    dataIndex: params.dataIndex,
  }
})

chart.on("mousemove", { dataType: "node" }, (params) => {
  if(!selectedNode) {
    return
  }

  updateNodePosition(globals.currentYear, selectedNode.seriesIndex, selectedNode.dataIndex)
})

chart.on("mouseup", { dataType: "node" }, (params) => {
  selectedNode = null
})


// ********
// * Data *
// ********

// Global variables
const globals = {
  // Original data, this will get replaced with JSON object from Python
  originalYearToData: {year_to_data},

  // [Absolute flow color, relative flow color]
  edgeColors: ["rgba(59, 162, 114, 1)", "rgba(255, 50, 50, 1)"],

  nodeIds: [],

  yearToData: new Map(),
  years: [],
  currentYear: 0,

  // Current in-use year data
  graphData: {
    data: [],
    link: [],
    categories: [],
    legendData: [],
    processIdToDataIndex: new Map(),
  },

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

// *************
// * Functions *
// *************

function getGraphNodeFromNodeData(nodeIndex, year) {
  const yearData = globals.yearToData.get(year)
  const nodeIndexToData = yearData.get("nodeIndexToData")
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
        ? globals.edgeColors[0]
        : globals.edgeColors[1],
      // width can be used to change line width
    },

    // Custom data
    text: isUnitAbsoluteValue ? "Absolute flow" : "Relative flow",
    value: `${value} ${unit}`,
  }

  return newGraphEdge
}

function buildGraphDataForYear(year) {
  const graphData = {
    data: [],
    link: [],
    categories: [],
    legendData: [],
    processIdToDataIndex: new Map(),
  };

  // Data for current year
  const nodeData = globals.originalYearToData[year]["node_index_to_data"];
  const edgeData = globals.originalYearToData[year]["edge_index_to_data"];

  // Build node data
  const nodeIds = [];
  for (const nodeIndex of Object.keys(nodeData)) {
    const node = nodeData[nodeIndex];
    nodeIds.push(node.process_id);
  }

  const visibleNodeIds = []
  for (const [nodeIndex, nodeId] of nodeIds.entries()) {
    const node = nodeData[nodeIndex];
    const processId = node.process_id;
    const numInflows = node.num_inflows
    const numOutflows = node.num_outflows

    // If not showing unconnected processes then skip to next iteration
    if(globals.hideUnconnectedProcesses) {
      if((numInflows == 0) && (numOutflows == 0)) {
        continue
      }
    }

    // Check if process label exists
    // Replace missing process label with text "Missing label (PROCESS_ID)"
    const processLabel = node.process_label ? node.process_label : `Missing label (${processId})`
    let processName = globals.useProcessIdAsLabel ? processId : processLabel

    // Node information for ECharts
    const newNodeData = {
      id: processId,
      name: processName,
      label: processLabel,
      category: processId,
      numInflows: numInflows,
      numOutflows: numOutflows,
      value: 0,
      text: `Process ${processId}`,
    }

    // Map process ID to data index
    graphData.processIdToDataIndex.set(processId, nodeIndex);
    graphData.data.push(newNodeData);
    visibleNodeIds.push(processId)
  }

  // Build edge data
  for (const edgeIndex of Object.keys(edgeData)) {
    graphData.link.push(newEdgeData);
  }

  // Build categories
  for (const node of graphData.data) {
    const newCategoryData = {
      name: node.id,
    };
    graphData.categories.push(newCategoryData);
  }

  // Build legend data - ECharts uses automatically node ID with this
  graphData.legendData = visibleNodeIds;
  return graphData;
}

function buildGraphDataForYearNew(year, updateOptions = {}) {
  const graphData = {
    data: [],
    link: [],
    categories: [],
    legendData: [],
    processIdToDataIndex: new Map(),
  };

  // Data for current year
  const nodeIndexToData = globals.yearToData.get(year).get("nodeIndexToData");
  for(const [nodeIndex, nodeData] of nodeIndexToData.entries()) {
    const graphNode = getGraphNodeFromNodeData(nodeIndex, year)

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

  const edgeIndexToData = globals.yearToData.get(year).get("edgeIndexToData");
  for(const [edgeIndex, edgeData] of edgeIndexToData.entries()) {
    const graphEdge = getGraphEdgeFromEdgeData(edgeIndex, year)
    graphData.link.push(graphEdge)
  }

  for(const node of graphData.data) {
    const newCategory = {
      name: node.id
    }
    graphData.categories.push(newCategory)
  }

  visibleNodeIds = []
  for(const node of graphData.data) {
    visibleNodeIds.push(node.id)
  }

  // Build legend data - ECharts uses automatically node ID with this
  graphData.legendData = visibleNodeIds;
  return graphData;
}


function buildOptionNew(graphData, updateOptions = { resetView: false }) {
  const center = ["50%", "50%"]
  if(!updateOptions.resetView) {
    // Use previous center
    const prevOption = chart.getOption()
    const prevCenter = prevOption.series[0].center
    center[0] = prevCenter[0]
    center[1] = prevCenter[1]
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
          layout: globals.freezeNodePositions ? "none" : "force",
          data: graphData.data,
          links: graphData.link,
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
    for (const nodeIndex of Object.keys(nodeData)) {
      const node = nodeData[nodeIndex]
      const nodeId = node.process_id
      nodeIndexToData.set(nodeIndex, node)
      nodeIdToNodeIndex.set(nodeId, nodeIndex)
    }

    // Map edge index to edge data
    const edgeIndexToData = new Map()
    for (const edgeIndex of Object.keys(edgeData)) {
      const edge = edgeData[edgeIndex];
      edgeIndexToData.set(edgeIndex, edge)
    }

    yearData.set("nodeIndexToData", nodeIndexToData)
    yearData.set("nodeIdToIndex", nodeIdToNodeIndex)
    yearData.set("edgeIndexToData", edgeIndexToData)
    yearToData.set(year, yearData)
  }

  globals.yearToData = yearToData
  updateNew({ resetView: true })
}

function updateNew(updateOptions = { resetView: false }) {
  const graphData = buildGraphDataForYearNew(globals.currentYear)
  const option = buildOptionNew(graphData, updateOptions)
  chart.setOption(option)
  globals.graphData = graphData
}

function freezeNodePositions() {
  const option = {...chart.getOption()}
  const nodeIdToPosition = new Map()
  const nodeIdToNodeIndex = new Map()

  for(const [nodeIndex, nodePosition] of getNodePositions().entries()) {
    const nodeId = option.series[0].data[nodeIndex].id
    nodeIdToPosition.set(nodeId, nodePosition)
    nodeIdToNodeIndex.set(nodeId, nodeIndex)
  }

  const nodeIndexToData = globals.yearToData.get(globals.currentYear).get("nodeIndexToData")
  for(const [nodeId, nodePosition] of nodeIdToPosition.entries()) {
    const nodeIndex = nodeIdToNodeIndex.get(nodeId)

    // Update visual position data
    const visualNodeData = option.series[0].data[nodeIndex]
    visualNodeData.x = nodePosition.x
    visualNodeData.y = nodePosition.y

    // TODO: Implement storing current position!
    // Update actual position data
    //let actualNodeData = nodeIndexToData.get(nodeIndex)
    // actualNodeData.x = nodePosition.x
    // actualNodeData.y = nodePosition.y
  }

  option.series[0].layout = "none"
  chart.setOption(option)
}

function unfreezeNodePositions() {
  // Update all nodes position when unfreezing
  const option = chart.getOption()
  for(const [nodeIndex, nodePosition] of getNodePositions().entries()) {
    option.series[0].data[nodeIndex].x = nodePosition.x
    option.series[0].data[nodeIndex].y = nodePosition.y
  }
  option.series[0].layout = "force"
  chart.setOption(option)

  // TODO: Implement
  // // Update yearToData with updated positions
  // for(const [nodeIndex, nodePosition] of nodePositions.entries()) {
  //   globals.originalYearToData[globals.currentYear]["node_index_to_data"][nodeIndex].x = nodePosition.x
  //   globals.originalYearToData[globals.currentYear]["node_index_to_data"][nodeIndex].y = nodePosition.y
  // }

  // // Update option with updated positions
  // const option = {...chart.getOption()}
  // for(const [index, node] of option.series[0].data.entries()) {
  //   node.x = nodePositions[index].x
  //   node.y = nodePositions[index].y
  // }
}

function updateNodePosition(year, seriesIndex, dataIndex) {
  const nodes = chart.getModel().getSeriesByIndex(seriesIndex).getData()
  const layout = nodes.getItemLayout(dataIndex)
  const x = layout[0]
  const y = layout[1]

  globals.originalYearToData[year]["node_index_to_data"][dataIndex].x = x
  globals.originalYearToData[year]["node_index_to_data"][dataIndex].y = y

  // const nodeData = globals.originalYearToData[globals.currentYear]["node_index_to_data"]
  // for(const nodeIndex of Object.keys(nodeData)) {
  //   nodeData[nodeIndex].x = option.series[0].data[nodeIndex].x
  //   nodeData[nodeIndex].y = option.series[0].data[nodeIndex].y
  // }
}

function getNodePositions() {
  // Get list of all node positions and return them as array
  const nodePositions = []
  const nodes = chart.getModel().getSeriesByIndex(0).getData()
  nodes.each(function (index) {
    const layout = nodes.getItemLayout(index)
    const x = layout[0]
    const y = layout[1]
    nodePositions.push({ x, y })
  })

  return nodePositions
}

console.log("Initializing...")
initialize();
console.log("Done.")

// let selectedNodes = []
// chart.on("select", (e) => {
//   // console.log("Select: ", e)
//   const dataType = e.dataType // "node" or "edge"?
//   const seriesIndex = e.seriesIndex
//   const dataIndexInside = e.dataIndexInside
//
//   // Update options
//   const option = chart.getOption()
//   const series = option.series[seriesIndex]
//   const newOption = {
//       series: [
//         {
//           type: "graph",
//           emphasis: {
//             disabled: false,
//           }
//         }]
//   }
//
//   chart.setOption(newOption)
// })

// chart.on("mouseover", (params) => {
//   // console.log(params)
//   console.log("Mouse entering")
//
//   const nodeDataIndex = []
//   const edgeDataIndex = []
//   for(const entry of selectedNodes) {
//     nodeDataIndex.push(entry.dataIndex)
//   }
//
//   const option = chart.getOption()
//   for(const entry of selectedNodes) {
//     const node = option.series[entry.seriesIndex].data[entry.dataIndex]
//     const links = option.series[entry.seriesIndex].links
//     console.log(node)
//
//     console.log(entry.dataIndex, processIdToDataIndex.get(node.id))
//
//     // Select all adjacent edges to node
//     for(const [edgeIndex, edge] of links.entries()) {
//       // console.log(edgeIndex, edge)
//
//       // Inflows to node
//       if(edge.target == node.id) {
//         edgeDataIndex.push(edgeIndex)
//
//         // Select source node also
//         const sourceDataIndex = processIdToDataIndex.get(edge.source)
//         nodeDataIndex.push(sourceDataIndex)
//       }
//
//       // Outflow from node
//       if(edge.source == node.id) {
//         edgeDataIndex.push(edgeIndex)
//
//         // Select target node also
//         const targetDataIndex = processIdToDataIndex.get(edge.target)
//         nodeDataIndex.push(targetDataIndex)
//       }
//
//     }
//   }
//
//   chart.dispatchAction({
//     type: 'highlight',
//     batch: [
//       { dataType: 'node', dataIndex: nodeDataIndex},
//       { dataType: 'edge', dataIndex: edgeDataIndex, notBlur: true},
//     ],
//   })
// })

