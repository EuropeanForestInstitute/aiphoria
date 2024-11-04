// Initialize the echarts instance based on the prepared dom
const chart = echarts.init(document.getElementById("main"));

// *******************
// * Event listeners *
// *******************

// Resize chart when window size has changed
addEventListener("resize", (e) => {
  chart.resize();
});

chart.on("timelinechanged", function (params) {
  // console.log(params)
  const year = globals.years[params.currentIndex];
  console.log("New year: ", year);

  const graphData = buildGraphDataForYear(year)
  const option = buildOption(graphData)
  chart.setOption(option)
});

// ********
// * Data *
// ********

// Global variables
const globals = {
  // [Absolute flow color, relative flow color]
  edgeColors: ["rgba(59, 162, 114, 1)", "rgba(255, 50, 50, 1)"],

  nodeIds: [],

  // Data from Python script
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

  for (const [nodeIndex, nodeId] of nodeIds.entries()) {
    const node = nodeData[nodeIndex];
    const process_id = node.process_id;
    const newNodeData = {
      name: process_id,
      id: process_id,
      category: process_id,
      value: 0,
      text: `Process ${process_id}`,
    };

    // Map process ID to data index
    graphData.processIdToDataIndex.set(process_id, nodeIndex);
    graphData.data.push(newNodeData);
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

  // Build legend data
  graphData.legendData = nodeIds;

  return graphData;
  // // Build node data
  // for(const nodeIndex of Object.keys(nodeData)) {
  //   const node = nodeData[nodeIndex]
  //   const process_id = node.process_id
  //   const newNodeData = {
  //     name: process_id,
  //     id: process_id,
  //     category: process_id,
  //     value: 0,
  //     text: `Process ${process_id}`,
  //   }
  //
  //   // Map process ID to data index
  //   globals.processIdToDataIndex.set(process_id, globals.graphData.data.length)
  //   globals.graphData.data.push(newNodeData)
  // }
}

function buildOption(graphData) {
  // graphData is year-specific data
  const option = {
    baseOption: {
      title: {
        text: "Process connections",
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
          center: [ "50%", "50%"],
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
  console.log("yearToData: ", globals.yearToData);
  console.log("Initializing...");

  // Update years
  globals.years = Object.keys(globals.yearToData);
  globals.currentYear = globals.years[0];

  // Get new graphData for year, build new option and set is as active
  globals.graphData = buildGraphDataForYear(globals.currentYear);
  const option = buildOption(globals.graphData);
  chart.setOption(option, { notMerge: true });
}

initialize();

// chart.on("highlight", (e) => {
//   // console.log("Highlighting ", e)
// })

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

// chart.on("click", { dataType: "node" }, (params) => {
//   console.log(params)
//
//   const dataType = params.dataType
//   const seriesIndex = params.seriesIndex
//   const dataIndex = params.dataIndex
//   selectedNodes.push({ seriesIndex: seriesIndex, dataIndex: dataIndex })
// })

// chart.on("click", { dataType: "edge" }, (params) => {
//   console.log(params)
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