# Parameters names are defined in this file
# and DataProvider file provides the default
# values for each parameter
from enum import Enum


class ParameterName(str, Enum):
    """
    Parameter enumerations used in settings file
    """

    # ***********************
    # * Required parameters *
    # ***********************

    # Process related
    SheetNameProcesses: str = "sheet_name_processes"
    ColumnRangeProcesses: str = "column_range_processes"
    SkipNumRowsProcesses: str = "skip_num_rows_processes"

    # Flow related
    SheetNameFlows: str = "sheet_name_flows"
    ColumnRangeFlows: str = "column_range_flows"
    SkipNumRowsFlows: str = "skip_num_rows_flows"

    # Model parameters
    StartYear: str = "start_year"
    EndYear: str = "end_year"
    DetectYearRange: str = "detect_year_range"
    UseVirtualFlows: str = "use_virtual_flows"
    VirtualFlowsEpsilon: str = "virtual_flows_epsilon"

    # ***********************
    # * Optional parameters *
    # ***********************
    ConversionFactorCToCO2: str = "conversion_factor_c_to_co2"
    FillMissingAbsoluteFlows: str = "fill_missing_absolute_flows"
    FillMissingRelativeFlows: str = "fill_missing_relative_flows"
    FillMethod: str = "fill_method"

    # Scenarios related
    SheetNameScenarios: str = "sheet_name_scenarios"
    ColumnRangeScenarios: str = "column_range_scenarios"
    SkipNumRowsScenarios: str = "skip_num_rows_scenarios"

    # Network graph
    CreateNetworkGraphs: str = "create_network_graphs"
    CreateSankeyCharts: str = "create_sankey_charts"

    # Output path
    OutputPath: str = "output_path"

    # Show plots
    ShowPlots: str = "show_plots"

    # Visualize inflows to process IDs
    VisualizeInflowsToProcesses: str = "visualize_inflows_to_processes"

    # Base unit name
    BaseUnitName: str = "base_unit_name"



class ParameterFillMethod(str, Enum):
    """
    Valid values for parameter FillMethod
    """

    Zeros: str = "Zeros"
    Previous: str = "Previous"
    Next: str = "Next"
    Interpolate: str = "Interpolate"
