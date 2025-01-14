import os
import sys
from IPython import get_ipython


def setup_current_working_directory():
    """
    Setup current working directory.
    """
    if get_ipython() is None:
        # Running in terminal
        os.chdir(os.path.dirname(sys.argv[0]))
    else:
        # Running Notebook, cwd is already set
        pass


def setup_odym_directories():
    """
    Setup ODYM directories. Appends to path to ODYM files to sys.path.
    """
    sys.path.insert(0, os.path.join(os.getcwd(), '.', 'lib', 'odym', 'modules'))
