<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/aiphoria-logo.png" height="50">
    <img alt="aiphoria logo" src="https://raw.githubusercontent.com/EuropeanForestInstitute/aiphoria/main/assets/aiphoria-logo.png" height="160">
  </picture>
</h1>

![GitHub Release](https://img.shields.io/github/v/release/EuropeanForestInstitute/aiphoria)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/EuropeanForestInstitute/aiphoria/publish-pypi.yaml)
![Tests](https://img.shields.io/github/actions/workflow/status/EuropeanForestInstitute/aiphoria/run-tests.yaml?label=tests)
![Coverage](assets/coverage.svg)
[![PyPI Downloads](https://img.shields.io/pypi/dm/aiphoria)](https://pypi.org/project/aiphoria/)
[![PyPI version](https://img.shields.io/pypi/v/aiphoria)](https://pypi.org/project/aiphoria/)
[![Downloads](https://static.pepy.tech/badge/aiphoria)](https://pepy.tech/project/aiphoria)
![GitHub License](https://img.shields.io/github/license/EuropeanForestInstitute/aiphoria)
[![status](https://joss.theoj.org/papers/<id>/status.svg)](https://joss.theoj.org/papers/<id>)
<br>


## Python package for dynamic wood material flow and carbon stock analysis

**aiphoria** is an open-source Python package for dynamic material flow analysis (DMFA) of wood. It follows wood
from harvest through processing to products such as buildings, furniture, and paper, and calculates how much carbon
these products store over time and when it is released. You describe your system and scenarios in an Excel file, so
no programming is needed.

**aiphoria** builds on [ODYM - Open Dynamic Material Systems Model](https://github.com/IndEcol/ODYM) for the stock
calculations. It was built for the wood sector, but its core does not depend on wood: wood-specific settings such as
carbon content and product lifetimes are input data and can be replaced for any other material.

## Features
**aiphoria** allows you to:
- **Solve flows given as absolute amounts and as shares (%) together** in one mass-balanced system, for example
  production and trade statistics (absolute) linked to end uses (shares)
- **Model in-use stocks** with product lifetime distributions, by age cohort, using ODYM
- **Track carbon and other indicators/elements** (e.g. dry mass, energy) through flows and stocks, and calculate annual CO2
  removals from carbon stocks
- **Run alternative scenarios** defined in Excel, with constrained and unconstrained modes
- **Explore results interactively** with Sankey diagrams for every year and a network graph of the system, and export
  all results to Excel and CSV

## Use cases
**aiphoria** is suited for:
- Wood flow and harvested wood product (HWP) carbon accounts at national or regional scale
- Temporary carbon storage and stock changes in wood products
- Scenario analysis at the level of end uses (e.g. more wood in construction, more recycling)
- Other material systems whose data come as a mix of absolute amounts and shares

# Installation

**aiphoria** requires Python 3.10 or newer. It is available on the Python Package Index (PyPI) and as source code
on [GitHub](https://github.com/EuropeanForestInstitute/aiphoria).

## Install from PyPI
```
pip install aiphoria
```

## Install from GitHub
```
pip install git+https://github.com/EuropeanForestInstitute/aiphoria.git
```

A step-by-step guide, including virtual environments, is in the
[wiki](https://github.com/EuropeanForestInstitute/aiphoria/wiki/Installation).

# How to use

## Run the example
**aiphoria** comes with an example scenario (a simple sawnwood chain with construction and furniture stocks):

```python
from aiphoria.example import run_example

run_example(remove_existing_output_dir=True)
```

The results are written to a folder called `aiphoria_example` in your home directory. Open
`combined_sankey.html` in a web browser to explore the flows year by timestep/ year by year. See the
[Quick start](https://github.com/EuropeanForestInstitute/aiphoria/wiki/Quick-start) for what to look at first.

## Run your own scenario
Describe your system in an Excel scenario file (start from the example or the empty template, both linked in the
[wiki](https://github.com/EuropeanForestInstitute/aiphoria/wiki)) and run:

```python
from aiphoria.runner import run_scenarios

run_scenarios(path_to_settings_file="path/to/scenario/file.xlsx",
              path_to_output_dir="~/scenario_result",
              remove_existing_output_dir=False)
```

Parameters:
- `path_to_settings_file` (str): path to the scenario file
- `path_to_output_dir` (str): folder where results are saved. Overrides the output path in the scenario file, which
  is useful when running several scenarios from a script.
- `remove_existing_output_dir` (bool): if `True`, an existing output folder is deleted first. If `False` (default)
  and the folder exists, the run stops with an error.

## Documentation

The full documentation is in the [GitHub wiki](https://github.com/EuropeanForestInstitute/aiphoria/wiki):
- **Getting started:** installation, quick start, running your own scenario
- **Concepts:** how aiphoria works, processes/flows/stocks, indicators, scenarios and scenario modes
- **Building a scenario file:** a reference for every sheet of the Excel file
- **Results:** output files and interactive visualizations
- **Help:** upgrading from older versions, troubleshooting

## Citation

If you use aiphoria, please cite it using the metadata in [`CITATION.cff`](CITATION.cff) (on GitHub: *Cite this
repository* in the right-hand panel). A paper describing aiphoria is under review at the
[Journal of Open Source Software](https://github.com/openjournals/joss-reviews/issues/11039).

## Contributing

Contributions are welcome: bug reports, questions, documentation, example scenarios, tests, and code. See
[CONTRIBUTING.md](CONTRIBUTING.md) for how to get started.

## Support

Please report bugs and ask questions in the [issue tracker](https://github.com/EuropeanForestInstitute/aiphoria/issues).
You can also contact us directly:
- Cleo Orfanidou [cleo.orfanidou@efi.int](mailto:cleo.orfanidou@efi.int)
- Janne Järvikylä [janne.jarvikyla@efi.int](mailto:janne.jarvikyla@efi.int)

## Special thanks
A huge thank you to the following people who made aiphoria better:
- Gustavo Ezequiel Martinez (virtual flows, system testing)
  - GitHub: [GustavoEzMartinez](https://github.com/GustavoEzMartinez)
  - Email: [gustavoezequiel.martinez@vito.be](mailto:gustavoezequiel.martinez@vito.be)

- Arthur Jakobs (packaging, CI/CD)
  - GitHub: [jakobsarthur](https://github.com/jakobsarthur)
  - Email: [artos.jakobs@psi.ch](mailto:artos.jakobs@psi.ch)

### JOSS review
aiphoria was reviewed for the [Journal of Open Source Software](https://joss.theoj.org)
([review thread](https://github.com/openjournals/joss-reviews/issues/11039)).
We warmly thank the reviewers [@JakobBD](https://github.com/JakobBD) and
[@paulrougieux](https://github.com/paulrougieux), and the editor
[@ethanwhite](https://github.com/ethanwhite), for their careful and constructive
feedback. Their comments helped us improve the documentation, dependencies,
package structure and code organisation of aiphoria, as well as the paper.

## Funding
aiphoria developers / European Forest Institute receive funding from the European Union's Horizon Europe Research
and Innovation Programme [`ForestPaths (ID No 101056755)`](https://forestpaths.eu/),
[`Monifun (ID No 101134991)`](https://www.monifun.eu/) and [`eco2adapt (ID No 101059498)`](https://www.eco2adapt.eu/).

## License
aiphoria is released under the [MIT License](LICENSE).
