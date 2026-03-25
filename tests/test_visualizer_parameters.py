from aiphoria.core.visualizer_parameters import VisualizerParameters


def test_visualizer_parameters():
    """
    Test that all the required visualizer parameters are found
    """
    # Following properties must be found from VisualizerParameters
    required_property_names = [
        "SmallNodeThreshold",
        "FlowAlpha",
        "TransformationStageNameToColor",
    ]

    for name in required_property_names:
        try:
            entry = VisualizerParameters[name]
        except KeyError as ex:
            raise ValueError("Required property name {} not defined in VisualizerParameters".format(name))
