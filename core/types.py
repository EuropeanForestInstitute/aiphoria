from enum import Enum


class FunctionType(str, Enum):
    Linear: str = "linear"
    Exponential: str = "exponential"


class ChangeType(str, Enum):
    Absolute: str = "ABS"
    Relative: str = "REL"


class FlowType(str, Enum):
    Absolute: str = "ABS"
    Relative: str = "REL"
