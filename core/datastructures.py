from typing import Tuple, List, Union, Dict, Any
from builtins import float
import copy
import pandas as pd
from lib.odym.modules.ODYM_Classes import MFAsystem
from core.parameters import StockDistributionParameterValueType
from core.types import FunctionType, ChangeType


class ObjectBase(object):
    """
    Base class for Process, Flow and Stock.
    Keeps track of row number, validity of read row and virtual state.
    """
    def __init__(self):
        self._id: Union[str, any] = -1
        self._row_number: int = -1
        self._is_valid: bool = False
        self._is_virtual: bool = False

    @property
    def is_valid(self) -> bool:
        return False

    @property
    def id(self) -> Union[str, any]:
        return self._id

    @id.setter
    def id(self, new_id: str):
        self._id = new_id

    @property
    def row_number(self) -> int:
        return self._row_number

    @row_number.setter
    def row_number(self, value: int):
        self._row_number = value

    @property
    def is_virtual(self) -> bool:
        return self._is_virtual

    @is_virtual.setter
    def is_virtual(self, value: bool):
        self._is_virtual = value


class Indicator(object):
    def __init__(self, name: str = None, conversion_factor: float = 1.0, comment: str = None, unit: str = None):
        super().__init__()
        self._name: Union[str, None] = name
        self._conversion_factor: Union[float, None] = conversion_factor
        self._comment: Union[str, None] = comment
        self._unit: Union[str, None] = unit

    @property
    def name(self) -> str:
        """
        Get the indicator name.

        :return: Indicator name (str)
        """
        return self._name

    @name.setter
    def name(self, new_name: str):
        """
        Set the indicator name.

        :param new_name: New indicator name (str)
        """
        self._name = new_name

    @property
    def conversion_factor(self) -> float:
        """
        Get the indicator conversion factor.

        :return: Conversion factor (float)
        """
        return self._conversion_factor

    @conversion_factor.setter
    def conversion_factor(self, new_conversion_factor: float):
        """
        Set the indicator conversion factor.

        :param new_value: New conversion factor (float)
        """
        self._conversion_factor = new_conversion_factor

    @property
    def comment(self) -> str:
        """
        Get indicator comment.

        :return: Indicator comment (str)
        """
        return self._comment

    @comment.setter
    def comment(self, new_comment: str):
        """
        Set the indicator comment.

        :param new_comment: New indicator comment (str)
        """
        self._comment = new_comment

    @property
    def unit(self) -> str:
        """
        Get the indicator unit.

        :return: Indicator unit (str)
        """
        return self._unit

    @unit.setter
    def unit(self, new_unit: str):
        """
        Set the indicator unit.

        :param new_unit: New Indicator unit (str)
        """
        self._unit = new_unit


class Process(ObjectBase):
    def __init__(self, params: pd.Series = None, row_number=-1):
        super().__init__()

        self._name = None
        self._location = None
        self._id = None
        self._transformation_stage = None
        self._stock_lifetime = None
        self._stock_lifetime_source = None
        self._stock_distribution_type = None
        self._stock_distribution_params = None
        self._wood_content = None
        self._wood_content_source = None
        self._density = None
        self._density_source = None
        self._modelling_status = None
        self._comment = None
        self._row_number = -1
        self._depth = -1
        self._position_x = None
        self._position_y = None
        self._label_in_graph = None

        # Leave instance to default state if params is not provided
        if params is None:
            return

        # Skip totally empty row
        if params.isna().all():
            return

        self._name = params.iloc[0]
        self._location = params.iloc[1]
        self._id = params.iloc[2]
        self._transformation_stage = params.iloc[3]

        # Parse stock lifetime, default to zero if None
        self._stock_lifetime = self._parse_stock_lifetime(params.iloc[4], row_number)

        self._stock_lifetime_source = params.iloc[5]
        self._stock_distribution_type = params.iloc[6]
        self._stock_distribution_params = params.iloc[7]

        # Parse stock distribution parameters
        # NOTE: Event invalid key-value -pairs are stored to _stock_distribution_params after parsin
        # and those are checked in datachecker
        self._parse_and_set_distribution_params(params.iloc[7])

        self._wood_content = params.iloc[8]
        self._wood_content_source = params.iloc[9]
        self._density = params.iloc[10]
        self._density_source = params.iloc[11]
        self._modelling_status = params.iloc[12]
        self._comment = params.iloc[13]
        self._position_x = params.iloc[14]
        self._position_y = params.iloc[15]
        self._label_in_graph = params.iloc[16]
        self._row_number = row_number

    def __str__(self) -> str:
        s = "Process '{}': Lifetime: {}".format(self.id, self.stock_lifetime)
        return s

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Process):
            return NotImplemented

        return self.id == other.id

    def is_valid(self) -> bool:
        is_valid = True
        is_valid = is_valid and self.name is not None
        is_valid = is_valid and self.location is not None
        is_valid = is_valid and self.id is not None
        return is_valid

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @name.setter
    def name(self, value) -> str:
        self._name = value

    @property
    def location(self) -> str:
        return self._location

    @location.setter
    def location(self, value: str):
        self._location = value

    @property
    def transformation_stage(self) -> str:
        return self._transformation_stage

    @transformation_stage.setter
    def transformation_stage(self, value: str):
        self._transformation_stage = value

    @property
    def stock_lifetime(self) -> int:
        return self._stock_lifetime

    @stock_lifetime.setter
    def stock_lifetime(self, value: int):
        self._stock_lifetime = value

    @property
    def stock_lifetime_source(self) -> str:
        return self._stock_lifetime_source

    @stock_lifetime_source.setter
    def stock_lifetime_source(self, value: str):
        self._stock_lifetime_source = value

    @property
    def stock_distribution_type(self) -> str:
        return self._stock_distribution_type

    @stock_distribution_type.setter
    def stock_distribution_type(self, value: str):
        self._stock_distribution_type = value

    @property
    def stock_distribution_params(self) -> str:
        return self._stock_distribution_params

    @stock_distribution_params.setter
    def stock_distribution_params(self, value: str):
        self._stock_distribution_params = value

    @property
    def wood_content(self) -> float:
        return self._wood_content

    @wood_content.setter
    def wood_content(self, value: float):
        self._wood_content = value

    @property
    def wood_content_source(self) -> str:
        return self._wood_content_source

    @wood_content_source.setter
    def wood_content_source(self, value: str):
        self._wood_content_source = value

    @property
    def density(self) -> float:
        return self._density

    @density.setter
    def density(self, value: float):
        self._density = value

    @property
    def density_source(self) -> str:
        return self._density_source

    @density_source.setter
    def density_source(self, value: str):
        self._density_source = value

    @property
    def modelling_status(self) -> str:
        return self._modelling_status

    @modelling_status.setter
    def modelling_status(self, value: str):
        self._modelling_status = value

    @property
    def comment(self) -> str:
        return self._comment

    @comment.setter
    def comment(self, value: str):
        self._comment = value

    @property
    def depth(self) -> int:
        return self._depth

    @depth.setter
    def depth(self, value: int):
        self._depth = value

    @property
    def position_x(self) -> float:
        return self._position_x

    @position_x.setter
    def position_x(self, value: float):
        self._position_x = value

    @property
    def position_y(self) -> float:
        return self._position_y

    @position_y.setter
    def position_y(self, value: float):
        self._position_y = value

    @property
    def label_in_graph(self) -> str:
        return self._label_in_graph

    @label_in_graph.setter
    def label_in_graph(self, value: str):
        self._label_in_graph = value

    def _parse_stock_lifetime(self, s: str, row_number: int = -1):
        """
        Parse stock lifetime from string.

        :param s: String
        :return: Stock lifetime (int)
        """
        lifetime = 0
        if s is None:
            return lifetime

        try:
            lifetime = int(s)
        except (ValueError, TypeError) as ex:
            raise Exception("Stock lifetime must be number (row {})".format(row_number))

        return lifetime

    def _parse_and_set_distribution_params(self, s: str):
        """
        Parse keys from string for distribution parameters.
        """

        try:
            # Check if cell contains only value
            self._stock_distribution_params = float(s)
            return
        except (ValueError, TypeError):
            if s is None:
                return

        params = {}
        has_multiple_params = s.find(',') > 0
        if not has_multiple_params:
            # Single parameter
            entry = s
            k = None
            v = None
            if entry.find("=") >= 0:
                # Has key=value
                k, v = entry.split("=")
                k = k.strip()
                v = v.strip()
            else:
                # Only key, no value
                k = entry.strip()
                v = None

            # Convert to target value type if definition exists
            value_type = StockDistributionParameterValueType[k]
            if value_type is not None:
                v = value_type(v)

            params[k] = v

        else:
            # Multiple parameters, separated by ','
            for entry in s.split(","):
                k = None
                v = None
                if entry.find("=") >= 0:
                    k, v = entry.split("=")
                    k = k.strip()
                    v = v.strip()
                else:
                    k = entry.strip()
                    v = None

                # Convert to target value type if definition exists
                value_type = StockDistributionParameterValueType[k]
                if value_type is not None:
                    v = value_type(v)

                params[k] = v

        self._stock_distribution_params = params


class Flow(ObjectBase):
    def __init__(self, params: pd.Series = None, row_number=-1):
        super().__init__()

        self._source_process = None
        self._source_process_transformation_stage = None
        self._source_process_location = None
        self._target_process = None
        self._target_process_transformation_stage = None
        self._target_process_location = None
        self._source_process_id = None
        self._target_process_id = None
        self._value = None
        self._unit = None
        self._year = None
        self._data_source = None
        self._data_source_comment = None
        self._comment = None

        # Evaluated per timestep
        self._is_evaluated = False
        self._evaluated_share = 0.0
        self._evaluated_value = 0.0

        # Indicator name to Indicator
        self._indicator_name_to_indicator = {}
        self._indicator_name_to_evaluated_value = {}

        # Flow prioritization
        self._is_prioritized = False

        if params is None:
            return

        # Skip totally empty row
        if params.isna().all():
            return

        self._source_process = params.iloc[0]
        self._source_process_transformation_stage = params.iloc[1]
        self._source_process_location = params.iloc[2]
        self._target_process = params.iloc[3]
        self._target_process_transformation_stage = params.iloc[4]
        self._target_process_location = params.iloc[5]
        self._source_process_id = params.iloc[6]
        self._target_process_id = params.iloc[7]
        self._value = params.iloc[8]
        self._unit = params.iloc[9]
        self._year = int(params.iloc[10])
        self._data_source = params.iloc[11]
        self._data_source_comment = params.iloc[12]

        # Rest of the elements except last element are indicators
        # There should be even number of indicators because each indicator has value and comment
        first_indicator_index = 13
        indicators = params[first_indicator_index:]
        if len(indicators) % 2:
            s = "Not even number of indicator columns in settings file.\n"
            s += "Each indicator needs two columns (value and comment) in this order."
            raise Exception(s)

        # Build indicator name to Indicator mappings
        for i in range(0, len(indicators), 2):
            indicator_name = indicators.index[i]
            conversion_factor = indicators.iloc[i]
            comment = indicators.iloc[i+1]

            # Strip substring inside characters '(' and  ')'
            # and use that as a unit
            indicator_unit = ""
            start_index = indicator_name.find("(")
            end_index = indicator_name.find(")")
            if start_index >= 0 and end_index >= 0:
                unit_name = indicator_name[start_index:end_index + 1]
                indicator_name = indicator_name.replace(unit_name, '').strip()
                indicator_unit = unit_name[1:-1].strip()

            new_indicator = Indicator(indicator_name, conversion_factor, comment, indicator_unit)
            self._indicator_name_to_indicator[indicator_name] = new_indicator
            self._indicator_name_to_evaluated_value[indicator_name] = 0.0

        self._row_number = row_number  # Track Excel file row number

    def __str__(self):
        s = "Flow '{}' -> '{}': Value={}, Unit={}, " \
            "is_evaluated={}, evaluated_share={}, evaluated_value={}, " \
            "year={}, is_virtual={}".format(
                self.source_process_id, self.target_process_id, self.value, self.unit,
                self.is_evaluated, self.evaluated_share, self.evaluated_value, self.year,
                self.is_virtual)
        return s

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Flow):
            return NotImplemented

        return self.id == other.id

    @staticmethod
    def make_flow_id(source_process_id: str, target_process_id: str) -> str:
        """
        Make Flow ID from source Process ID and target Process ID.

        :param source_process_id: Source Process ID (string)
        :param target_process_id: Target Process ID (string)
        :return: Flow ID (string)
        """
        return "{} {}".format(source_process_id, target_process_id)

    @property
    def id(self) -> str:
        """
        Returns Flow ID.

        :return: Flow ID (string)
        """
        return Flow.make_flow_id(self.source_process_id, self.target_process_id)

    def is_valid(self):
        is_valid = True
        is_valid = is_valid and self.value is not None
        is_valid = is_valid and (self.source_process is not None)
        is_valid = is_valid and (self.target_process is not None)
        is_valid = is_valid and (self.source_process_id is not None)
        is_valid = is_valid and (self.target_process_id is not None)
        return is_valid

    @property
    def is_unit_absolute_value(self):
        # Default to absolute value if unit is missing
        unit_str = self.unit
        if unit_str is None:
            return True

        unit_str = unit_str.strip()
        if unit_str == "%":
            return False

        return True

    @property
    def source_process(self) -> str:
        """
        Get source Process name.

        :return: Source Process name (str)
        """
        return self._source_process

    @property
    def source_process_transformation_stage(self) -> str:
        return self._source_process_transformation_stage

    @property
    def source_process_location(self) -> str:
        return self._source_process_location

    @property
    def target_process(self) -> str:
        """
        Get target Process name.
        :return: Target Process name (str)
        """
        return self._target_process

    @property
    def target_process_transformation_stage(self) -> str:
        return self._target_process_transformation_stage

    @property
    def target_process_location(self) -> str:
        return self._target_process_location

    @property
    def source_process_id(self) -> str:
        """
        Get source Process ID.
        :return: Source Process ID (str)
        """
        return self._source_process_id

    @source_process_id.setter
    def source_process_id(self, source_process_id: str):
        """
        Set source Process ID.

        :param source_process_id: Source Process ID (str)
        """
        self._source_process_id = source_process_id

    @property
    def target_process_id(self) -> str:
        """
        Get target Process ID.

        :return: Target Process ID (str)
        """
        return self._target_process_id

    @target_process_id.setter
    def target_process_id(self, target_process_id: str):
        """
        Set target Process ID.

        :param target_process_id: New target Process ID
        """
        self._target_process_id = target_process_id

    # Original value from Excel row
    @property
    def value(self) -> float:
        """
        Get original baseline value.

        :return: Original baseline value (float)
        """
        return self._value

    @value.setter
    def value(self, value: float):
        """
        Set original base value.

        :param value: New original base value (float)
        """
        self._value = value

    @property
    def unit(self) -> str:
        return self._unit

    @unit.setter
    def unit(self, unit: str):
        self._unit = unit

    @property
    def year(self) -> int:
        return self._year

    @year.setter
    def year(self, value: int):
        self._year = value

    @property
    def data_source(self) -> str:
        return self._data_source

    @property
    def data_source_comment(self) -> str:
        return self._data_source_comment

    @property
    def comment(self) -> str:
        return self._comment

    @property
    def is_evaluated(self) -> bool:
        """
        Get flow evaluated state.

        :return: True if Flow is evaluated, False otherwise.
        """
        return self._is_evaluated

    @is_evaluated.setter
    def is_evaluated(self, value: bool):
        """
        Set flow evaluated state.

        :param value: New evaluated state (bool)
        """
        self._is_evaluated = value

    @property
    def evaluated_value(self) -> float:
        """
        Get evaluated base value.

        :return: Evaluated base value (float)
        """
        return self._evaluated_value

    @evaluated_value.setter
    def evaluated_value(self, value: float):
        """
        Set evaluated base value.

        :param value: New evaluated base value (float)
        """
        self._evaluated_value = value

    @property
    def evaluated_share(self) -> float:
        return self._evaluated_share

    @evaluated_share.setter
    def evaluated_share(self, value: float):
        self._evaluated_share = value

    @property
    def is_prioritized(self) -> bool:
        return self._is_prioritized

    @is_prioritized.setter
    def is_prioritized(self, is_prioritized: bool):
        self._is_prioritized = is_prioritized

    @property
    def indicator_name_to_indicator(self) -> Dict[str, Indicator]:
        return self._indicator_name_to_indicator

    @property
    def indicator_name_to_evaluated_value(self) -> Dict[str, float]:
        return self._indicator_name_to_evaluated_value

    def get_indicator_names(self) -> List[str]:
        """
        Get list of Indicator names (including baseline indicator name).

        :return: List of Indicator names
        """
        return list(self._indicator_name_to_indicator.keys())

    def get_indicator_conversion_factor(self, indicator_name: str) -> float:
        """

        :param indicator_name:
        :return:
        """
        return self._indicator_name_to_indicator[indicator_name].conversion_factor

    def get_evaluated_value_for_indicator(self, indicator_name: str) -> float:
        """
        Get evaluated value for Indicator.

        :param indicator_name: Target Indicator name (str)
        :return: Evaluated value for Indicator (float)
        """
        return self._indicator_name_to_evaluated_value[indicator_name]

    def set_evaluated_value_for_indicator(self, indicator_name: str, value: float):
        """
        Set evaluated value for Indicator.

        :param indicator_name: Target Indicator name (str)
        :param value: New evaluated value for Indicator (float)
        """
        self._indicator_name_to_evaluated_value[indicator_name] = value

    def evaluate_indicator_values_from_baseline_value(self):
        """
        Evaluated indicator evaluated value from baseline value.
        """
        for indicator_name, indicator in self._indicator_name_to_indicator.items():
            evaluated_value = self.evaluated_value * indicator.conversion_factor
            self.set_evaluated_value_for_indicator(indicator_name, evaluated_value)

    def get_all_evaluated_values(self) -> List[float]:
        """
        Get list of all evaluated values.
        First index is always the evaluated baseline value.
        Other indices are evaluated indicator values

        :return: List of evaluated values (list of float)
        """

        return [self.evaluated_value] + [value for name, value in self.indicator_name_to_evaluated_value.items()]


# Stock is created for each process that has lifetime
class Stock(ObjectBase):
    def __init__(self, params: Process = None, row_number=-1):
        super().__init__()
        self._process = None
        self._id = -1

        if params is None:
            return

        self._process = params
        self._id = params.id
        self._row_number = row_number

    def __str__(self):
        if not self.is_valid():
            return "Stock: no process"

        s = "Stock: Process='{}', lifetime={}".format(self.id, self.stock_lifetime)
        return s

    def is_valid(self):
        if not self._process:
            return False

        return True

    def __hash__(self):
        return hash(self._process.id)

    def __eq__(self, other):
        return self.id == other.id

    @property
    def name(self):
        return self._process.name

    @property
    def stock_lifetime(self):
        return self._process.stock_lifetime

    @property
    def stock_distribution_type(self):
        return self._process.stock_distribution_type

    @property
    def stock_distribution_params(self):
        return self._process.stock_distribution_params


class FlowModifier(ObjectBase):
    def __init__(self, params: pd.Series = None):
        super().__init__()

        self._scenario_name: str = ""
        self._source_process_id: str = ""
        self._target_process_id: str = ""
        self._change_in_value: Union[float, None] = None
        self._target_value: Union[float, None] = None
        self._change_type: str = ""
        self._start_year: int = 0
        self._end_year: int = 0
        self._function_type: str = ""
        self._opposite_target_process_ids = []

        if params is None:
            # Invalid: no parameters
            return

        if all(not elem for elem in params):
            # Invalid: all parameters None
            return

        # Alias parameters to more readable form
        param_scenario_name = params.iloc[0]
        param_source_process_id = params.iloc[1]
        param_target_process_id = params.iloc[2]
        param_change_in_value = params.iloc[3]
        param_target_value = params.iloc[4]
        param_change_type = params.iloc[5]
        param_start_year = params.iloc[6]
        param_end_year = params.iloc[7]
        param_function_type = params.iloc[8]

        self._scenario_name = self._parse_as(param_scenario_name, str)[0]
        self._source_process_id = self._parse_as(param_source_process_id, str)[0]
        self._target_process_id = self._parse_as(param_target_process_id, str)[0]

        # This is the delta change of the value and means that it's error
        # if target flow has ABS type and the 'change in value' is REL
        # NOTE: Either of self._change_in_value of self._target_value must be defined
        if param_change_in_value is not None:
            self._change_in_value = self._parse_as(param_change_in_value, float)[0]

        if param_target_value is not None:
            self._target_value = self._parse_as(param_target_value, float)[0]

        # Change type
        # NOTE: Convert change type to valid ChangeType enum if found. Otherwise use the value from parameter.
        self._change_type = param_change_type
        for change_type in ChangeType:
            if self._parse_as(self._change_type, str)[0].lower() == change_type.lower():
                self._change_type = change_type

        self._start_year = self._parse_as(param_start_year, int)[0]
        self._end_year = self._parse_as(param_end_year, int)[0]

        # Function type
        # NOTE: Convert function type to valid FunctionType enum if found. Otherwise use the value from parameter.
        self._function_type = param_function_type
        for function_type in FunctionType:
            if self._parse_as(self._function_type, str)[0].lower() == function_type:
                self._function_type = function_type

        # Check how many target nodes with opposite effect there is
        for process_id in list(params[9:]):
            if process_id is not None:
                self._opposite_target_process_ids.append(process_id)

    def __str__(self):
        s = "Flow modifier: scenario_name='{}', source_process_id='{}', target_process_id='{}', change_in_value='{}', " \
            "target_value='{}', change_type='{}', start_year='{}', end_year='{}', function_type='{}'".format(
            self.scenario_name,
            self.source_process_id,
            self.target_process_id,
            self.change_in_value,
            self.target_value,
            self.change_type,
            self.start_year,
            self.end_year,
            self.function_type,
        )
        return s

    def is_valid(self) -> bool:
        return True

    @property
    def use_change_in_value(self) -> bool:
        return self.change_in_value is not None

    @property
    def use_target_value(self) -> bool:
        return self.target_value is not None

    @property
    def is_change_type_value(self) -> bool:
        """
        Check if change type is value type (= absolute change in flow value or in flow share)
        :return: True if change type is value type, False otherwise.
        """
        return self.change_type == ChangeType.Value

    @property
    def is_change_type_proportional(self) -> bool:
        """
        Is change type proportional (= relative change in flow value or in flow share)
        :return: True if change type is proportional, False otherwise.
        """
        return self.change_type == ChangeType.Proportional

    @property
    def has_target(self) -> bool:
        """
        Does flow modifier target any flow?
        :return: Bool
        """
        return self.target_process_id != ""

    @property
    def has_opposite_targets(self) -> bool:
        """
        Does flow modifier have opposite targets?
        :return: Bool
        """
        return len(self.opposite_target_process_ids) > 0


    @staticmethod
    def _parse_as(val: any, target_type: any) -> (bool, any):
        """
        Parse variable as type.
        Returns tuple (bool, value).
        If parsing fails then value is the original val.

        :param val: Variable
        :param type: Target type
        :return: Tuple (bool, value)
        """
        ok = True
        result = val
        try:
            result = target_type(val)
        except ValueError as ex:
            ok = False

        return result, ok

    @property
    def scenario_name(self) -> str:
        return self._scenario_name

    @property
    def source_process_id(self) -> str:
        return self._source_process_id

    @property
    def target_process_id(self) -> str:
        return self._target_process_id

    @property
    def target_flow_id(self) -> str:
        return "{} {}".format(self.source_process_id, self.target_process_id)

    @property
    def change_in_value(self) -> float:
        return self._change_in_value

    @property
    def target_value(self) -> float:
        return self._target_value

    @property
    def change_type(self) -> str:
        return self._change_type

    @property
    def start_year(self) -> int:
        return self._start_year

    @property
    def end_year(self) -> int:
        return self._end_year

    @property
    def function_type(self) -> Union[FunctionType, str]:
        return self._function_type

    @property
    def opposite_target_process_ids(self) -> List[str]:
        return self._opposite_target_process_ids

    def get_year_range(self) -> List[int]:
        """
        Get list of years FlowModifier is used.

        :return: List of years (integers)
        """
        return [year for year in range(self.start_year, self.end_year + 1)]


class ScenarioData(object):
    """
    Data class for holding Scenario data.

    DataChecker builds ScenarioData-object that can be used for FlowSolver.
    """

    def __init__(self,
                 years: List[int] = None,
                 year_to_process_id_to_process: Dict[int, Dict[str, Process]] = None,
                 year_to_process_id_to_flow_ids: Dict[int, Dict[str, Dict[str, List[str]]]] = None,
                 year_to_flow_id_to_flow: Dict[int, Dict[str, Flow]] = None,
                 stocks: List[Stock] = None,
                 process_id_to_stock: Dict[str, Stock] = None,
                 unique_process_id_to_process: Dict[str, Process] = None,
                 unique_flow_id_to_flow: Dict[str, Flow] = None,
                 use_virtual_flows: bool = True,
                 virtual_flows_epsilon: float = 0.1,
                 baseline_value_name: str = "Baseline",
                 baseline_unit_name: str = "Baseline unit",
                 indicator_name_to_indicator: Dict[str, Indicator] = None
                 ):

        if years is None:
            years = []

        if year_to_process_id_to_process is None:
            year_to_process_id_to_process = {}

        if year_to_process_id_to_flow_ids is None:
            year_to_process_id_to_flow_ids = {}

        if year_to_flow_id_to_flow is None:
            year_to_flow_id_to_flow = {}

        if stocks is None:
            stocks = []

        if process_id_to_stock is None:
            process_id_to_stock = {}

        if unique_process_id_to_process is None:
            unique_process_id_to_process = {}

        if unique_flow_id_to_flow is None:
            unique_flow_id_to_flow = {}

        if indicator_name_to_indicator is None:
            indicator_name_to_indicator = {}

        self._year_to_flow_id_to_flow = year_to_flow_id_to_flow
        self._year_to_process_id_to_process = year_to_process_id_to_process
        self._year_to_process_id_to_flow_ids = year_to_process_id_to_flow_ids

        self._years = years
        self._year_start = 0
        self._year_end = 0

        if self._years:
            self._year_start = min(self._years)
            self._year_end = max(self._years)

        self._process_id_to_stock = process_id_to_stock
        self._stocks = stocks
        self._unique_process_id_to_process = unique_process_id_to_process
        self._unique_flow_id_to_flow = unique_flow_id_to_flow
        self._use_virtual_flows = use_virtual_flows
        self._virtual_flows_epsilon = virtual_flows_epsilon
        self._baseline_value_name = baseline_value_name
        self._baseline_unit_name = baseline_unit_name
        self._indicator_name_to_indicator = indicator_name_to_indicator

    @property
    def years(self) -> List[int]:
        """
        Get list of years
        :return: List of years
        """
        return self._years

    @property
    def year_to_process_id_to_process(self) -> Dict[int, Dict[str, Process]]:
        """
        Get year to Process ID to Process mappings.

        :return: Dictionary (Year -> Process ID -> Process)
        """
        return self._year_to_process_id_to_process

    @property
    def year_to_process_id_to_flow_ids(self) -> Dict[int, Dict[str, Dict[str, List[str]]]]:
        """
        Get year to Process ID to In/Out to -> List of Flow ID mappings.

        :return: Dictionary (Year -> Process ID -> Dictionary(keys "in", "out") -> List of Flow IDS)
        """

        return self._year_to_process_id_to_flow_ids

    @property
    def year_to_flow_id_to_flow(self) -> Dict[int, Dict[str, Flow]]:
        """
        Get year to Flow ID to Flow mappings.

        :return: Dictionary (Year -> Flow ID -> Flow)
        """
        return self._year_to_flow_id_to_flow

    @property
    def stocks(self) -> List[Stock]:
        """
        Get list of Stocks
        :return: List of Stocks
        """
        return self._stocks

    @property
    def process_id_to_stock(self) -> Dict[str, Stock]:
        """
        Get mapping of Process ID to Stock
        :return: Dictionary
        """
        return self._process_id_to_stock

    @property
    def unique_process_id_to_process(self) -> Dict[str, Process]:
        """
        Get mapping of unique Process ID to Process
        :return: Dictionary
        """
        return self._unique_process_id_to_process

    @property
    def unique_flow_id_to_flow(self) -> Dict[str, Flow]:
        """
        Get mapping of unique Flow ID to Flows
        :return: Dictionary
        """
        return self._unique_flow_id_to_flow

    @property
    def use_virtual_flows(self) -> bool:
        """
        Get boolean flag if using virtual flows
        :return: bool
        """
        return self._use_virtual_flows

    @property
    def virtual_flows_epsilon(self) -> float:
        """
        Get maximum allowed difference between input and output flows before creating virtual flows.
        This is only used if using the virtual flows.
        :return: Float
        """
        return self._virtual_flows_epsilon

    @property
    def start_year(self) -> int:
        """
        Get starting year
        :return: Starting year (int)
        """
        return self._year_start

    @property
    def end_year(self) -> int:
        """
        Get ending year
        Ending year is included in simulation.

        :return: Ending year (int)
        """
        return self._year_end

    @property
    def baseline_value_name(self) -> str:
        """
        Get baseline value name (e.g. "Solid wood equivalent")

        :return: Baseline value name (str)
        """
        return self._baseline_value_name

    @baseline_value_name.setter
    def baseline_value_name(self, new_name: str):
        """
        Set new baseline value name.

        :param new_name: New baseline value name (str)
        """
        self._baseline_value_name = new_name

    @property
    def baseline_unit_name(self) -> str:
        """
        Get baseline unit name (e.g. "Mm3")

        :return: Baseline unit name (str)
        """
        return self._baseline_unit_name

    @baseline_unit_name.setter
    def baseline_unit_name(self, new_name: str):
        """
        Set new baseline unt name.

        :param new_name: New baseline name (str)
        """
        self._baseline_unit_name = new_name

    @property
    def indicator_name_to_indicator(self) -> Dict[str, Indicator]:
        """
        Get dictionary of Indicator name to Indicator.

        :return: Dictionary (indicator name (str), Indicator)
        """
        return self._indicator_name_to_indicator

    @indicator_name_to_indicator.setter
    def indicator_name_to_indicator(self, new_indicator_name_to_indicator: Dict[str, Indicator]):
        """
        Set new Indicator name to Indicator mapping.

        :param new_indicator_name_to_indicator: New Indicator name to Indicator dictionary
        """
        self._indicator_name_to_indicator = new_indicator_name_to_indicator


class ScenarioDefinition(object):
    """
    ScenarioDefinition is wrapper object that contains scenario name and all flow modifiers that are applied
    for the Scenario.

    Actual building of Scenarios happens inside DataChecker.build_scenarios()
    """
    def __init__(self, name: str = None, flow_modifiers: List[FlowModifier] = None):
        if name is None:
            name = "Baseline scenario"

        if flow_modifiers is None:
            flow_modifiers = []

        self._name = name
        self._flow_modifiers = flow_modifiers

    @property
    def name(self) -> str:
        """
        Get scenario name.

        :return: Scenario name
        """
        return self._name

    @property
    def flow_modifiers(self) -> List[FlowModifier]:
        """
        Get list of FlowModifiers.
        These are the rules that are applied to Scenario.

        :return: List of FlowModify-objects
        """
        return self._flow_modifiers


class Scenario(object):
    """
    Scenario is wrapper object that contains scenario name and all flow modifiers that are
    happening in the scenario
    """

    def __init__(self, definition: ScenarioDefinition = None, data: ScenarioData = None, model_params=None):
        if definition is None:
            definition = ScenarioDefinition()

        if data is None:
            data = ScenarioData()

        if model_params is None:
            model_params = {}

        self._scenario_definition = definition
        self._scenario_data = data
        self._flow_solver = None
        self._odym_data = None
        self._model_params = model_params
        self._mfa_system = None

    @property
    def name(self) -> str:
        return self._scenario_definition.name

    @property
    def scenario_definition(self) -> ScenarioDefinition:
        return self._scenario_definition

    @property
    def scenario_data(self) -> ScenarioData:
        return self._scenario_data

    # Flow solver
    @property
    def flow_solver(self):
        """
        Get FlowSolver that is assigned to Scenario.
        :return: FlowSolver (FlowSolver)
        """
        return self._flow_solver

    @flow_solver.setter
    def flow_solver(self, flow_solver):
        self._flow_solver = flow_solver

    @property
    def model_params(self) -> Dict[str, Any]:
        return self._model_params

    @property
    def mfa_system(self) -> MFAsystem:
        """
        Get stored ODYM MFA system.
        :return: MFAsystem-object
        """
        return self._mfa_system

    @mfa_system.setter
    def mfa_system(self, mfa_system) -> None:
        """
        Set new MFAsystem
        :param mfa_system: Target MFAsystem-object
        """
        self._mfa_system = mfa_system

    def copy_from_baseline_scenario_data(self, scenario_data: ScenarioData):
        """
        Copy ScenarioData from baseline Scenario.
        Data is deep copied and is not referencing to original data anymore.

        :param scenario_data: ScenarioData from baseline FlowSolver.
        """
        self._scenario_data = copy.deepcopy(scenario_data)


class Color(ObjectBase):
    def __init__(self, params: Union[List, pd.Series] = None, row_number=-1):
        super().__init__()
        self._name: str = ""
        self._value: str = ""
        self.row_number = row_number

        if params is None:
            return

        # Handle processing list and pd.Series differently
        name_val = ""
        value_val = ""
        if isinstance(params, list):
            name_val = str(params[0])
            value_val = str(params[1])

        if isinstance(params, pd.Series):
            name_val = str(params.iloc[0])
            value_val = str(params.iloc[1])

        self.name = name_val
        self.value = value_val

    def __str__(self) -> str:
        """
        Returns the string presentation of the Color in format:
        #rrggbb
        where
            rr = red component
            gg = green component
            bb = blue component

        :return: Color as hexadecimal string, prefixed with character '#'
        """
        return self.value.lower()

    def is_valid(self) -> bool:
        return not self.name and self.value

    @property
    def name(self) -> str:
        """
        Get color name.

        :return: Color name (str)
        """
        return self._name

    @name.setter
    def name(self, new_name: str):
        """
        Set color name.

        :param new_name: New color name
        """
        self._name = new_name

    @property
    def value(self) -> str:
        """
        Color value (hexadecimal, e.g. #AABBCC) prefixed with the character '#'
        """
        return self._value

    @value.setter
    def value(self, new_value: str):
        """
        Set new color value (hexadecimal).
        New color must be prefixed with the character '#'.

        :param new_value: New color value (hexadecimal)
        """
        self._value = new_value

    def get_red_as_float(self) -> float:
        """
        Get red component value in range [0, 1]
        :return: Red value (float)
        """
        return self._hex_to_normalized_float(self.value[1:][0:2])

    def get_green_as_float(self) -> float:
        """
        Get green component value in range [0, 1]
        :return: Green value (float)
        """
        return self._hex_to_normalized_float(self.value[1:][2:4])

    def get_blue_as_float(self) -> float:
        """
        Get blue component value in range [0, 1]
        :return: Blue value (float)
        """
        return self._hex_to_normalized_float(self.value[1:][4:6])

    def _hex_to_normalized_float(self, hex_value: str) -> float:
        return int(hex_value, 16) / 255.0


class ProcessEntry(object):
    """
    Internal storage class for Process entry (process, inflows, and outflows).
    Used when storing Process data in DataFrames.
    """

    KEY_IN: str = "in"
    KEY_OUT: str = "out"

    def __init__(self, process: Process = None):
        """
        Initialize ProcessEntry.
        Makes deep copy of target Process.

        :param process: Target Process
        """
        self._process = process
        self._flows = {self.KEY_IN: {}, self.KEY_OUT: {}}

    @property
    def process(self) -> Process:
        return self._process

    @property
    def flows(self) -> Dict[str, Dict[str, Flow]]:
        return self._flows

    @flows.setter
    def flows(self, flows: Dict[str, Dict[str, Flow]]):
        self._flows = flows

    @property
    def inflows(self) -> List[Flow]:
        return list(self._flows[self.KEY_IN].values())

    @inflows.setter
    def inflows(self, flows: List[Flow]):
        self._flows[self.KEY_IN] = {flow.id: flow for flow in flows}

    @property
    def inflows_as_dict(self) -> Dict[str, Flow]:
        return self._flows[self.KEY_IN]

    @property
    def outflows(self) -> List[Flow]:
        return list(self._flows[self.KEY_OUT].values())

    @outflows.setter
    def outflows(self, flows: List[Flow]):
        self._flows[self.KEY_OUT] = {flow.id: flow for flow in flows}

    def outflows_as_dict(self) -> Dict[str, Flow]:
        return self._flows[self.KEY_OUT]

    def add_inflow(self, flow: Flow):
        self._flows[self.KEY_IN][flow.id] = flow

    def add_outflow(self, flow: Flow):
        self._flows[self.KEY_OUT][flow.id] = flow

    def remove_inflow(self, flow_id: str):
        """
        Remove inflow by Flow ID.
        Raises Exception if Flow ID is not found in inflows.

        :param flow_id: Target Flow ID
        :raises Exception If Flow ID is not found
        """
        removed_flow_id = self._flows[self.KEY_IN].pop(flow_id, None)
        if not removed_flow_id:
            raise Exception("No flow_id {} in inflows".format(flow_id))

    def remove_outflow(self, flow_id: str):
        """
        Remove outflow by Flow ID.
        Raises Exception if Flow ID is not found in outflows.

        :param flow_id: Target Flow ID
        :raises Exception If Flow ID is not found
        """
        removed_flow_id = self._flows[self.KEY_OUT].pop(flow_id, None)
        if not removed_flow_id:
            raise Exception("No flow_id {} in outflows".format(flow_id))
