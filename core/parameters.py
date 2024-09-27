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


class ParameterFillMethod(str, Enum):
    """
    Valid values for parameter FillMethod
    """

    Zeros: str = "zeros"
    Previous: str = "previous"
    Next: str = "next"
    Interpolate: str = "interpolate"
