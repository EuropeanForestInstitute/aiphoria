import pytest
from aiphoria.core.datavisualizer import DataVisualizer


def test_datavisualizer_defaults():
    datavisualizer = DataVisualizer()

    # Expected: Fail if no parameters are provided
    with pytest.raises(TypeError):
        datavisualizer.build_and_show()


def test_datavisualizer_defaults():
    datavisualizer = DataVisualizer()

    combine_to_one_file = True
    scenarios = []
    visualizer_params = {}
    model_params = {}

    # Expected: Fail if empty parameters are provided
    with pytest.raises(KeyError):
        datavisualizer.build_and_show(scenarios,
                                      visualizer_params,
                                      model_params,
                                      combine_to_one_file=combine_to_one_file
                                      )
