from typing import Tuple


class ObjectBase(object):
    def __init__(self):
        self._id = -1
        self._row_number = -1
        self._is_valid = False
        self._is_virtual = False

    @property
    def is_valid(self) -> bool:
        return False

    @property
    def is_valid(self) -> bool:
        return False

    @property
    def id(self) -> str:
        return self._id

    @id.setter
    def id(self, new_id) -> str:
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

        self._flow_share = 0.0
        self._flow_value = 0.0
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

        self._row_number = row_number  # Track Excel file row number, last element in list

    def __str__(self):
        s = "Flow '{}' -> '{}': Value={} Unit={}, is_evaluated={}, evaluated_share={}, evaluated_value={}, year={}".format(
            self.source_process_id, self.target_process_id, self.value, self.unit,
            self.is_evaluated, self.evaluated_share, self.evaluated_value, self.year)
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

        if not params:
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


class FlowVariation(ObjectBase):
    def __init__(self):
        super().__init__()
        print("FlowVariation.__init__()")

