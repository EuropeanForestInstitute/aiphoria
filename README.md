<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/_static/aiphoria-logo.png" height="50">
    <img alt="aiphoria logo" src="https://raw.githubusercontent.com/EuropeanForestInstitute/aiphoria/main/docs/_static/aiphoria-logo.png" height="160">
  </picture>
</h1>

## Python package for assessing and visualizing dynamic wood material flows

> ℹ️ _This package is under continuous development_

aiphoria is Python package that facilitates the assessment of wood materials flows, associated carbon stocks, and stock changes, as well as and their visualization over time.
**aiphoria** builds on top of [ODYM - Open Dynamic Material Systems Model](https://github.com/IndEcol/ODYM).

## Features:
**aiphoria** allows you to:
- **Solve flows** provided both in absolute and relative (%) values, for example semi-finished wood product statistics (absolute values) to end-uses (relative values)
- **Conduct dynamic MFA as well as temporary carbon storage assessment**
- **Visualize material flows** through a Sankey diagram and provided timestep.

## Use cases:

**aiphoria** is ideal for:
- **Any temporal and spatial situation where material systems want to be assessed**
- **Product sink/stock effects**


# Installation

**aiphoria** is available at Python Package Index (PyPi) and as source distribution in [Github](https://github.com/EuropeanForestInstitute/aiphoria/wiki)<br>

## Install from PyPi
```
pip install aiphoria
```

## Install from GitHub
```
pip install git+https://github.com/EuropeanForestInstitute/aiphoria.git
```

# How to use

## Showcase
**aiphoria** includes helper function to showcase example scenario with visualizations.<br>
Showcase / example scenario can be run by the following code:

```python
from aiphoria.example import run_example

run_example(remove_existing_output_dir=True)
```

Network and Sankey visualizations are opened automatically in browser and output is generated<br>
inside user home directory to directory called "aiphoria_example_scenario".<br>

## Advanced usage
For the users who are already familiar using **aiphoria** the package exposes function for running
scenarios by using the one-liner:

```python
from aiphoria.runner import run_scenarios

run_scenarios(path_to_settings_file="path/to/scenario/file.xlsx",
              path_to_output_dir="~/scenario_result",
              remove_existing_output_dir=False)
```

Using parameter **path_to_output_dir** overrides the output path defined in scenario file.<br>
This makes easier to change target from Python script itself or when running multiple scenarios in batch.<br>
Parameters:
- path_to_settings_file (string): Path to scenario settings file
- path_to_output_dir (string): Path to directory where results are saved
- remove_existing_output_dir: If True then existing output directory is deleted (defaults to False). If directory already exists then error is raised and execution is stopped

## Documentation

Online documentation can be found in [GitHub wiki](https://github.com/EuropeanForestInstitute/aiphoria/wiki).

## Support:

If you have any questions or need help, do not hesitate to contact us:
- Cleo Orfanidou [cleo.orfanidou@efi.int](mailto:cleo.orfanidou@efi.int)
- Janne Järvikylä [janne.jarvikyla@efi.int](mailto:janne.jarvikyla@efi.int)

## Special thanks
A huge thank you to the following people who made aiphoria better:
- Gustavo Ezequiel Martinez (virtual flows, system testing)
  - GitHub: [GustavoEzMartinez](https://github.com/GustavoEzMartinez)
  - Email: [gustavoezequiel.martinez@vito.be](mailto:gustavoezequiel.martinez@vito.be) 

