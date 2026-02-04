from enum import Enum


# Flow modifier parameters
class FunctionType(str, Enum):
    Constant: str = "constant"
    Linear: str = "linear"
    Exponential: str = "exponential"
    Sigmoid: str = "sigmoid"


class ChangeType(str, Enum):
    Value: str = "Value"
    Proportional: str = "%"


class FlowType(str, Enum):
    Absolute: str = "ABS"
    Relative: str = "REL"

