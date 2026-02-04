import os
import sys
import shutil
from importlib.resources import files
from typing import Union
from .runner import run_scenarios


def run_example(path_to_output_dir: Union[str, None] = None,
                remove_existing_output_dir: bool = False):
    """
    Run example scenario and place output to path_to_output_dir.
    If no path_to_output_dir is provided then places results
    to users home directory inside directory "aiphoria_example".
    Existing directory is not deleted and error is shown if
    directory already exists.

    Deleting existing directory can be overridden by setting
    parameter remove_existing_output_dir to True.


    Examples:
    run_example()
    run_example("C:\\results\\aiphoria_example")
    run_example("~/results/aiphoria_example")

    NOTE:
    - Path to output directory MUST BE in absolute format
    (e.g. "C:\\results\\aiphoria_example" (Windows)
    - ~ is expanded to absolute path automatically

    :param path_to_output_dir: Absolute path to output directory
    :param remove_existing_output_dir: If True then removes existing output directory (default = False)
    """
    output_dir_name = "aiphoria_example"
    example_scenario_path = "data/example_scenario.xlsx"

    if path_to_output_dir is None:
        # Place results to users home directory
        path_to_output_dir = os.path.expanduser(os.path.join("~", output_dir_name))
        path_to_output_dir = os.path.realpath(path_to_output_dir)

    if not os.path.isabs(path_to_output_dir):
        sys.stderr.write("ERROR: Path to output directory is not in absolute format\n")
        return False

    if not remove_existing_output_dir and os.path.isdir(path_to_output_dir):
        sys.stderr.write("Directory {} already exists\n".format(path_to_output_dir))
        return False

    # Target directory doesn't exist or is okay to remove
    sys.stdout.write("Using output path = {}\n".format(path_to_output_dir))
    shutil.rmtree(path_to_output_dir, ignore_errors=True)
    os.makedirs(path_to_output_dir, exist_ok=True)

    path_to_example_scenario = files("aiphoria").joinpath(example_scenario_path)
    if not os.path.isfile(path_to_example_scenario):
        sys.stderr.write("ERROR: Example scenario file {} not found, packaging issue\n")
        return False

    current_cwd = os.getcwd()
    os.chdir(path_to_output_dir)
    run_scenarios(path_to_example_scenario,
                  path_to_output_dir=path_to_output_dir,
                  remove_existing_output_dir=remove_existing_output_dir)
    os.chdir(current_cwd)
