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

  update({ resetViewPosition: false })
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

  update({ resetViewPosition: false })
})

document.getElementById("resetView").addEventListener("click", (event) => {
  update({ resetViewPosition: true })
})


// **************************
// * ECharts event handlers *
// **************************

chart.on("timelinechanged", function (params) {
  globals.currentYear = globals.years[params.currentIndex];
  update()
});

chart.on("click", { dataType: "node" }, (params) => {
  // console.log(params)
  // const dataType = params.dataType
  // const seriesIndex = params.seriesIndex
  // const dataIndex = params.dataIndex
  // console.log(dataType, seriesIndex, dataIndex)
  // selectedNodes.push({ seriesIndex: seriesIndex, dataIndex: dataIndex })
})

chart.on("mousedown", { dataType: "node" }, (params) => {
  console.log(params)
})

chart.on("mouseup", { dataType: "node" }, (params) => {
  console.log(params)
  const data = params.data
  const seriesIndex = params.seriesIndex
  const dataIndex = params.dataIndex
  const transform = params.event.target.transform

  const prevOption = chart.getOption()

  // prevOption.series[seriesIndex].data[dataIndex].x = transform[4]
  // prevOption.series[seriesIndex].data[dataIndex].y = transform[5]
  // chart.setOption(prevOption)
})

// chart.on("click", { dataType: "edge" }, (params) => {
//   console.log(params)
// })

// ********
// * Data *
// ********

// Global variables
const globals = {
  // [Absolute flow color, relative flow color]
  edgeColors: ["rgba(59, 162, 114, 1)", "rgba(255, 50, 50, 1)"],

  nodeIds: [],

  // Data from Python script, this string gets replaced by the JSON object
  yearToData: {year_to_data},
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
};

// *************
// * Functions *
// *************

function buildGraphDataForYear(year) {
  const graphData = {
    data: [],
    link: [],
    categories: [],
    legendData: [],
    processIdToDataIndex: new Map(),
  };

  // Data for current year
  const nodeData = globals.yearToData[year]["node_index_to_data"];
  const edgeData = globals.yearToData[year]["edge_index_to_data"];

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
      if(numInflows == 0 && numOutflows == 0) {
        continue
      }
    }

    // Check if process label exists
    // Replace missing process label with text "Missing label (PROCESS_ID)"
    const processLabel = node.process_label ? node.process_label : `Missing label (${processId})`
    let processName = globals.useProcessIdAsLabel ? processId : processLabel

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
    const edge = edgeData[edgeIndex];
    const flowId = edge.flow_id;
    const sourceProcessId = edge.source_process_id;
    const targetProcessId = edge.target_process_id;
    const isUnitAbsoluteValue = edge.is_unit_absolute_value;
    const value = edge.value;
    const unit = edge.unit;
    const newEdgeData = {
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
    };
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
  //graphData.legendData = nodeIds;
  graphData.legendData = visibleNodeIds;
  return graphData;
}

function buildOption(graphData, updateOptions = { resetViewPosition: true }) {
  const center = ["50%", "50%"]
  if(!updateOptions.resetViewPosition) {
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
          layout: "force",
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
  globals.years = Object.keys(globals.yearToData);
  globals.currentYear = globals.years[0];
  update()
}

function update(updateOptions = { resetViewPosition: true }) {
  const year = globals.currentYear
  const graphData = buildGraphDataForYear(year)
  const option = buildOption(graphData, updateOptions)
  chart.setOption(option)
  globals.graphData = graphData
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
