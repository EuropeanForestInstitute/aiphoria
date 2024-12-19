from enum import Enum


class VisualizerParameters(str, Enum):
    SmallNodeThreshold = "small_node_threshold"
    FlowAlpha = "flow_alpha"
    TransformationStageNameToColor = "transformation_stage_name_to_color"
