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
    SkipNumRowsProcesses: str = "skip_num_rows_processes"
    IgnoreColumnsProcesses: str = "ignore_columns_processes"

    # Flow related
    SheetNameFlows: str = "sheet_name_flows"
    SkipNumRowsFlows: str = "skip_num_rows_flows"
    IgnoreColumnsFlows: str = "ignore_columns_flows"

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
    UseScenarios: str = "use_scenarios"
    SheetNameScenarios: str = "sheet_name_scenarios"
    SkipNumRowsScenarios: str = "skip_num_rows_scenarios"
    IgnoreColumnsScenarios: str = "ignore_columns_scenarios"

    # Sheet name for colors
    SheetNameColors: str = "sheet_name_colors"
    SkipNumRowsColors: str = "skip_num_rows_colors"
    IgnoreColumnsColors: str = "ignore_columns_colors"

    # Network graph
    CreateNetworkGraphs: str = "create_network_graphs"
    CreateSankeyCharts: str = "create_sankey_charts"

    # Output path
    OutputPath: str = "output_path"

    # Show plots
    ShowPlots: str = "show_plots"

    # Visualize inflows to process IDs
    VisualizeInflowsToProcesses: str = "visualize_inflows_to_processes"

    # Baseline unit
    # BaseLineValueName: Name of the baseline value e.g. "Solid wood equivalent"
    # BaselineUnitName: Name of the baseline unit e.g. Mm3 SWE
    BaselineValueName: str = "baseline_value_name"
    BaselineUnitName: str = "baseline_unit_name"

    # Flow prioritization
    PrioritizeTransformationStages: str = "prioritize_transformation_stages"
    PrioritizeLocations: str = "prioritize_locations"


class ParameterFillMethod(str, Enum):
    """
    Valid values for parameter FillMethod
    """

    Zeros: str = "Zeros"
    Previous: str = "Previous"
    Next: str = "Next"
    Interpolate: str = "Interpolate"


class ParameterLandfillDecayType(str, Enum):
    Wood: str = "LandfillDecayWood"
    Paper: str = "LandfillDecayPaper"


class ParameterLandfillKey(str, Enum):
    def __str__(self) -> str:
        return str(self.value)

    Condition: str = "condition"