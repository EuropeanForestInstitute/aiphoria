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
    def __init__(self, params=None):
        super().__init__()

        self._name = None
        self._location = None
        self._id = None
        self._transformation_stage = None
        self._lifetime = None
        self._lifetime_source = None
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
        if not params:
            return

        self._name = params[0].value
        self._location = params[1].value
        self._id = params[2].value
        self._transformation_stage = params[3].value
        self._lifetime = params[4].value
        self._lifetime_source = params[5].value
        self._stock_distribution_type = params[6].value
        self._stock_distribution_params = params[7].value
        self._wood_content = params[8].value
        self._wood_content_source = params[9].value
        self._density = params[10].value
        self._density_source = params[11].value
        self._modelling_status = params[12].value
        self._comment = params[13].value
        self._position_x = params[14].value
        self._position_y = params[15].value
        self._label_in_graph = params[16].value
        self._row_number = params[-1]  # Track Excel file row number, last element in list

    def __str__(self) -> str:
        s = "Process '{}': Lifetime: {}".format(self.id, self.lifetime)
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
    def lifetime(self) -> int:
        return self._lifetime

    @lifetime.setter
    def lifetime(self, value: int):
        self._lifetime = value

    @property
    def lifetime_source(self) -> str:
        return self._lifetime_source

    @lifetime_source.setter
    def lifetime_source(self, value: str):
        self._lifetime_source = value

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


class Flow(ObjectBase):
    def __init__(self, params=None):
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
        self._data_type = None
        self._comment = None

        # Evaluated per timestep
        self._is_evaluated = False
        self._evaluated_share = 0.0
        self._evaluated_value = 0.0

        self._flow_share = 0.0
        self._flow_value = 0.0

        if not params:
            return

        self._source_process = params[0].value
        self._source_process_transformation_stage = params[1].value
        self._source_process_location = params[2].value
        self._target_process = params[3].value
        self._target_process_transformation_stage = params[4].value
        self._target_process_location = params[5].value
        self._source_process_id = params[6].value
        self._target_process_id = params[7].value
        self._value = params[8].value
        self._unit = params[9].value
        self._year = params[10].value
        self._data_source = params[11].value
        self._data_type = params[12].value
        self._comment = params[13].value
        self._conversion_factor_used = params[14].value
        self._carbon_content_factor = params[15].value
        self._carbon_content_source = params[16].value

        self._row_number = params[-1]  # Track Excel file row number, last element in list

        # # Export is indicated by negative value
        # # Switch source and target process IDs so because data is defined as "to -> from" and with the negative value
        # if self._value and self._value < 0.0:
        #     self._source_process_id, self._target_process_id = self._target_process_id, self._source_process_id
        #     self._value = abs(self._value)

    def __str__(self):
        s = "Flow '{}' -> '{}': Value={} Unit={}, is_evaluated={}, evaluated_share={}, evaluated_value={}".format(
            self.source_process_id, self.target_process_id, self.value, self.unit,
            self.is_evaluated, self.evaluated_share, self.evaluated_value)
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
    def data_type(self) -> str:
        return self._data_type

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


# Stock is created for each process that has lifetime
class Stock(ObjectBase):
    def __init__(self, params=None):
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

        s = "Stock: Process='{}', lifetime={}".format(self.id, self.lifetime)
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
    def lifetime(self):
        return self._process.lifetime

    @property
    def distribution_type(self):
        return self._process.stock_distribution_type

    @property
    def distribution_params(self):
        return self._process.stock_distribution_params


