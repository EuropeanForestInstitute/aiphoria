from builtins import float
from typing import Tuple, List, Union, Dict
import copy
from core.types import FunctionType, ChangeType


class ObjectBase(object):
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


class Process(ObjectBase):
    def __init__(self, params=None, row_number=-1):
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
        self._stock_lifetime = params.iloc[4]
        self._stock_lifetime_source = params.iloc[5]
        self._stock_distribution_type = params.iloc[6]
        self._stock_distribution_params = params.iloc[7]

        success, messages = self._parse_and_set_distribution_params(s=params.iloc[7], row_number=row_number)
        if not success:
            for msg in messages:
                print("{}".format(msg))

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

    def _parse_and_set_distribution_params(self, s: str, row_number: int = -1) -> Tuple[bool, list[str]]:
        """
        Parse keys from string for distribution parameters.
        Valid keys for distribution parameters are:
        - stddev
        - shape
        - scale

        :param s: String containing distribution parameters
        :return: Tuple (was parsing successful success, error messages)
        """
        # Try converting s to float. If successful, set the value and return success
        success = True
        messages = []
        try:
            # Check if cell contains only value
            self._stock_distribution_params = float(s)
            return success, messages
        except ValueError:
            pass

        # Try parsing keys from the string, format: key=value, key1=value1, etc.
        params = {}
        for entry in s.split(","):
            key, value = entry.strip().split("=")
            try:
                param_name = key.lower()
                param_value = float(value)
                params[param_name] = param_value
            except ValueError as ex:
                success = False
                messages.append("No value defined for distribution parameter key '{}' for Process {} in row {}!".format(
                    key, id, row_number))

        # Parsing keys was not successful
        if not success:
            return success, messages

        # Update the stock distribution params to instance
        self._stock_distribution_params = params
        return success, messages


class Flow(ObjectBase):
    def __init__(self, params=None, row_number=-1):
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
        self._carbon_content_factor = 1.0
        self._carbon_content_source = None

        # Evaluated per timestep
        self._is_evaluated = False
        self._evaluated_share = 0.0
        self._evaluated_value = 0.0

        self._indicators = {}

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
        self._conversion_factor_used = params.iloc[13]
        
        # Carbon content
        self._carbon_content_factor = 1.0 if params.iloc[14] is None else params.iloc[14]
        self._carbon_content_source = params.iloc[15]

        # Rest of the elements except last element are indicators
        # There should be even number of indicators because each indicator has value and comment
        first_indicator_index = 16
        indicators = params[first_indicator_index:]
        if len(indicators) % 2:
            print("Not even number of indicator columns in data file.")
            print("Each indicator needs two columns (value and comment) in this order.")
            raise SystemExit(-1)

        # Go through indicators with step size of 2
        # column at index i   = indicator value
        # column at index i+1 = indicator comment
        for i in range(0, len(indicators), 2):
            indicator_name = str(indicators.index[i])
            indicator_value = indicators.iloc[i]
            indicator_comment = indicators.iloc[i+1]

            # Default to 1 as indicator value if no value is provided
            indicator_value = 1 if indicator_value is None else indicator_value
            self._indicators[indicator_name] = indicator_value

        self._row_number = row_number  # Track Excel file row number

    def __str__(self):
        s = "Flow '{}' -> '{}': Value={} Unit={}," \
            "is_evaluated={}, evaluated_share={}, evaluated_value={}," \
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

    @property
    def id(self) -> str:
        return self.source_process_id + " " + self.target_process_id

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
    def source_process(self) -> Process:
        return self._source_process

    @property
    def source_process_transformation_stage(self) -> str:
        return self._source_process_transformation_stage

    @property
    def source_process_location(self) -> str:
        return self._source_process_location

    @property
    def target_process(self) -> Process:
        return self._target_process

    @property
    def target_process_transformation_stage(self) -> str:
        return self._target_process_transformation_stage

    @property
    def target_process_location(self) -> str:
        return self._target_process_location

    @property
    def source_process_id(self) -> str:
        return self._source_process_id

    @source_process_id.setter
    def source_process_id(self, source_process_id: str):
        self._source_process_id = source_process_id

    @property
    def target_process_id(self) -> str:
        return self._target_process_id

    @target_process_id.setter
    def target_process_id(self, target_process_id: str):
        self._target_process_id = target_process_id

    # Original value from Excel row
    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, value: float):
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
    def carbon_content_factor(self) -> float:
        return self._carbon_content_factor

    @carbon_content_factor.setter
    def carbon_content_factor(self, value: float):
        self._carbon_content_factor = value

    @property
    def carbon_content_source(self) -> str:
        return self._carbon_content_source

    @carbon_content_source.setter
    def carbon_content_source(self, value: str):
        self._carbon_content_source = value

    @property
    def indicators(self) -> dict[str, float]:
        return self._indicators

    @indicators.setter
    def indicators(self, val):
        self._indicators = val

    @property
    def is_evaluated(self) -> bool:
        return self._is_evaluated

    @is_evaluated.setter
    def is_evaluated(self, value: bool):
        self._is_evaluated = value

    @property
    def evaluated_value(self) -> float:
        return self._evaluated_value

    @evaluated_value.setter
    def evaluated_value(self, value: float):
        self._evaluated_value = value

    @property
    def evaluated_share(self) -> float:
        return self._evaluated_share

    @evaluated_share.setter
    def evaluated_share(self, value: float):
        self._evaluated_share = value

    @property
    def evaluated_value_carbon(self) -> float:
        return self.evaluated_value * self.carbon_content_factor


# Stock is created for each process that has lifetime
class Stock(ObjectBase):
    def __init__(self, params=None, row_number=-1):
        super().__init__()
        self._process: Process = None
        self._id = -1

        if params is None:
            return

        self._process = params
        self._id = params.id

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
    def __init__(self, params: List[any] = None):
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
        param_scenario_name = params[0]
        param_source_process_id = params[1]
        param_target_process_id = params[2]
        param_change_in_value = params[3]
        param_target_value = params[4]
        param_change_type = params[5]
        param_start_year = params[6]
        param_end_year = params[7]
        param_function_type = params[8]

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
                 virtual_flows_epsilon: float = 0.1
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

    @property
    def years(self) -> List[int]:
        """
        Get list of years
        :return: List of years
        """
        return self._years

    @property
    def year_to_process_id_to_process(self) -> Dict[int, Dict[str, Process]]:
        # TODO: Fill doctext
        return self._year_to_process_id_to_process

    @property
    def year_to_process_id_to_flow_ids(self) -> Dict[int, Dict[str, Dict[str, List[str]]]]:
        # TODO: Fill doctext
        return self._year_to_process_id_to_flow_ids

    @property
    def year_to_flow_id_to_flow(self) -> Dict[int, Dict[str, Flow]]:
        # TODO: Fill doctext
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
        :return: Starting year
        """
        return self._year_start

    @property
    def end_year(self) -> int:
        """
        Get ending year
        Ending year is included in simulation.
        :return:
        """
        return self._year_end


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

    def __init__(self, definition: ScenarioDefinition = None, data: ScenarioData = None):
        if definition is None:
            definition = ScenarioDefinition()

        if data is None:
            data = ScenarioData()

        self._scenario_definition = definition
        self._scenario_data = data
        self._flow_solver = None
        self._odym_data = None

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
        return self._flow_solver

    @flow_solver.setter
    def flow_solver(self, flow_solver):
        self._flow_solver = flow_solver

    def copy_from_baseline_scenario_data(self, scenario_data: ScenarioData):
        """
        Copy ScenarioData from baseline Scenario.
        Data is deep copied and is not referencing to original data anymore.

        :param scenario_data: ScenarioData from baseline FlowSolver.
        """
        self._scenario_data = copy.deepcopy(scenario_data)


class Color(ObjectBase):
    def __init__(self, params=None, row_number=-1):
        super().__init__()
        self._name: str = ""
        self._value: str = ""
        self.row_number = row_number

        if params is None:
            return

        self.name = str(params[0])
        self.value = str(params[1])

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
