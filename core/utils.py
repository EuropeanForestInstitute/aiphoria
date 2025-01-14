import os
import sys
import pandas as pd
import numpy as np
from IPython import get_ipython
from lib.odym.modules.ODYM_Classes import MFAsystem


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


def calculate_scenario_mass_balance(mfa_system: MFAsystem, model_years: list[int]) -> pd.DataFrame:
    """
    Get scenario mass balance summary per year.

    :param mfa_system: MFASystem-object
    :param model_years: List of years
    :return: DataFrame
    """

    #print("Mass balance difference per year")
    mb = mfa_system.MassBalance()
    #print("Mass balance result shape: {}".format(mb.shape))
    df_mass_balance = pd.DataFrame(columns=["Year", "Process 0", "Rest", "Abs difference"])
    for year_index, year in enumerate(model_years):
        # Calculate mass balance using the first element in MFA system (= base element)
        # Negative value in process 0 means that process 0 has no inflows so this mass
        # is coming from outside system boundaries
        p0 = np.sum(mb[year_index][0][0])
        rest = np.sum(mb[year_index][1:, 0])
        abs_diff = abs(p0) - abs(rest)
        df_mass_balance.loc[year_index] = np.array([year, p0, rest, abs_diff])
    df_mass_balance = df_mass_balance.astype({"Year": "int32"})
    df_mass_balance.set_index(["Year"], inplace=True)
    return df_mass_balance
