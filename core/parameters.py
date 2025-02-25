# Parameters names are defined in this file
# and DataProvider file provides the default
# values for each parameter
from enum import Enum
from typing import Dict, Any


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


# Parameters used for Process/Flows/Stocks in settings file
class StockDistributionType(str, Enum):
    """
    Stock distribution types and decay functions
    """
    Fixed: str = "Fixed"
    Normal: str = "Normal"
    LogNormal: str = "LogNormal"
    FoldedNormal: str = "FoldedNormal"
    Weibull: str = "Weibull"
    Simple: str = "Simple"
    LandfillDecayWood: str = "LandfillDecayWood"
    LandfillDecayPaper: str = "LandfillDecayPaper"


class LandfillDecayParameter(str, Enum):
    """
    Parameter names for LandFillDecay* types
    """
    Condition: str = "condition"


# *********************************
# * Stock distribution parameters *
# *********************************

class StockDistributionParameter(str, Enum):
    """
    Stock distribution parameters.
    """
    StdDev: str = "stddev"
    Shape: str = "shape"
    Scale: str = "scale"
    Condition: str = "condition"


class StockDistributionParameterValueType(object):
    """
    Storage class for stock distribution parameters.
    Emulates Dictionary behaviour allowing to get value using
    the [] notation e.g.
        StockDistributionParameterValueType[StockDistributionParameter.StdDev]
        StockDistributionParameterValueType["stddev"]
    """
    parameter_to_value_type = {
        StockDistributionParameter.StdDev: float,
        StockDistributionParameter.Shape: float,
        StockDistributionParameter.Scale: float,
        StockDistributionParameter.Condition: str,
    }

    def __class_getitem__(cls, item):
        """
        Get value type for StockDistributionParameter

        :param item: Item (str or StockDistributionParameter)
        :return:
        """
        item_enum = None
        if isinstance(item, str):
            try:
                item_enum = StockDistributionParameter(item)
            except ValueError:
                pass

        if item_enum is None:
            #raise Exception("{} is not valid StockDistributionParameter".format(item_enum))
            pass

        value_type = cls.parameter_to_value_type.get(item_enum, None)
        if value_type is None:
            #raise Exception("No value type for {}!".format(item_enum))
            pass

        return value_type


class RequiredStockDistributionParameters(object):
    """
    Storage class for required stock distribution parameters.
    Emulates Dictionary behaviour allowing to get value using
    the [] notation e.g.
        RequiredStockDistributionParameters[StockDistributionType.Fixed]
        RequiredStockDistributionParameters["Fixed"]
    """

    # NOTE: value must be dictionary
    # NOTE: Key = StockDistributionType, Value: Dictionary (str -> required type)
    stock_distribution_to_required_params = {
        StockDistributionType.Fixed: {},
        StockDistributionType.Normal: {"stddev": float},
        StockDistributionType.LogNormal: {"stddev": float},
        StockDistributionType.FoldedNormal: {"stddev": float},
        StockDistributionType.Weibull: {"shape": float, "scale": float},
        StockDistributionType.Simple: {},
        StockDistributionType.LandfillDecayWood: {"condition": str},
        StockDistributionType.LandfillDecayPaper: {"condition": str},
    }

    def __class_getitem__(cls, item) -> Dict[str, Any]:
        """
        Get required parameters for StockDistributionType.
        Parameter 'item' can be either string or StockDistributionType-instance.

        :param item: String or instance of StockDistributionType
        :return: Dictionary of required parameters (key = parameter name, value = type of required parameter e.g. float)
        """

        # Convert string to StockDistributionType Enum
        item_enum = None
        if isinstance(item, str):
            try:
                item_enum = StockDistributionType(item)
            except ValueError:
                pass

        if item_enum is None:
            # raise Exception("{} is not in RequiredStockDistributionParameters".format(item_name))
            pass

        params = cls.stock_distribution_to_required_params.get(item_enum, None)
        if params is None:
            # raise Exception("{} is not valid StockDistributionType!".format(item_enum))
            pass

        return params


class AllowedStockDistributionParameterValues(object):
    """
    Storage class for required stock distribution parameter values.
    Emulates Dictionary behaviour allowing to get value using
    the [] notation e.g.
        AllowedStockDistributionParameterValues[StockDistributionType.Fixed]
        AllowedStockDistributionParameterValues["Fixed"]
    """

    # NOTE: value must be dictionary
    # NOTE: Key = StockDistributionType, Value: Dictionary (str -> required type)
    stock_distribution_param_to_allowed_values = {
        StockDistributionParameter.Condition: {"Dry": str, "Wet": str, "Managed": str}
    }

    def __class_getitem__(cls, item) -> Dict[str, Any]:
        """
        Get allowed parameters for StockDistributionParameter.
        Parameter 'item' can be either string or StockDistributionParameter-instance.

        :param item: String or instance of StockDistributionParameter
        :return: Dictionary of allowed entries (key: StockDistributionParameter-instance, value: type)
        """

        # Convert string to StockDistributionParameter Enum
        item_enum = None
        if isinstance(item, str):
            try:
                item_enum = StockDistributionParameter(item)
            except ValueError:
                pass

        # If item_enum is not found in list of allowed values then return empty Dictionary
        params = cls.stock_distribution_param_to_allowed_values.get(item_enum, None)
        if params is None:
            params = {}

        return params