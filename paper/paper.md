---
title: 'aiphoria: A Python package for dynamic wood material flow and carbon stock analysis'
tags:
  - Python
  - material flow analysis
  - dynamic stock modelling
  - wood products
  - carbon stocks
  - industrial ecology
  - bioeconomy
authors:
  - name: Timokleia Orfanidou
    orcid: 0000-0003-3126-9603
    affiliation: 1
  - name: Janne Järvikylä
    orcid: 0009-0006-8390-1905
    affiliation: 1
affiliations:
  - name: European Forest Institute (EFI), Finland
    index: 1
date: 20 June 2026
bibliography: paper.bib
---

# Summary

`aiphoria` is an open-source Python package for dynamic material flow analysis
(DMFA) of wood. It can be used to follow wood from harvest through sawmills
and other processing to final products such as buildings, furniture, and paper,
and it calculates how much carbon these products hold over time and when it is
released at end of life. Users describe the system and their scenarios in an
Excel file, so no programming is needed. The package builds on ODYM
[@Pauliuk2020] for the stock calculations and returns time series of flows,
in-use stocks, and carbon stock changes, with interactive Sankey diagrams.

`aiphoria` was built for the wood sector, but its core does not depend on
wood: wood-specific settings, such as carbon content and product lifetimes,
are input data and can be replaced for any other material.

# Statement of need

Wood is both a material and a temporary carbon store. The carbon
taken up by trees stays stored in harvested wood products for as long as they
remain in use, from a few years for paper to several decades for construction
timber and wood panels, and is released when the products are burned or decay
at end of life. Assessing the climate role of the forest-based bioeconomy
therefore means following how wood flows through the economy and how long
carbon stays in products before it is released. This question is central to
current EU forest and climate policy [@Verkerk2022].

Dynamic material flow analysis gives the basis for this [@Brunner2016]: it
tracks wood and carbon year by year and keeps each process in balance, so
harvest, products in use, and end-of-life flows are linked in one account. The
main challenge is the data. Production and trade statistics are reported as
absolute amounts (m³ or tonnes), while end uses are often available only as
shares, for example the percentage of sawnwood used in construction. Combining
the two usually requires custom preprocessing that is hard to repeat across
studies.

`aiphoria` is made for forest economists, bioeconomy analysts, and experts
preparing LULUCF greenhouse gas reports, who often work in spreadsheets rather
than code. It takes absolute and relative flows together, calculates the
unknown flows while keeping the mass balance, and follows the carbon in each
product stock, without custom scripting.

# State of the field

General dynamic MFA frameworks such as ODYM [@Pauliuk2020] and flodym
[@flodym] provide well-tested methods for stocks and flows, but the user must
build each system in code and first bring all data into one consistent format.
`aiphoria` reuses ODYM's dynamic stock model and adds what wood-sector studies need: a spreadsheet interface, a solver for
mixed absolute and relative flows, and carbon stock accounting.

Carbon in harvested wood products (HWP) is usually estimated with the approach
of the IPCC guidelines [@IPCC2019]. The default method starts from production
statistics for three product groups (sawnwood, wood-based panels, and paper and
paperboard) and assumes that each group loses carbon at a fixed rate (default
half-lives of 35, 25, and 2 years). It is simple and needs little data, but it
does not follow products to their end uses or capture recycling and
circularity. Many models go further, and the review by @BrunetNavarro2016
shows that they differ widely in product categories, lifetimes, and
end-of-life options. Studies that combine the
IPCC approach with mass-balanced MFA find that following end uses can give
larger carbon pools than the default method [@Jasinevicius2018], but these
studies were not released as reusable software. Forest carbon models such as
CBM-CFS3 [@Kurz2009] include an HWP pool, but they start from forest inventory
data, and product accounting is only a small part of a larger forest model.

Market models such as TiMBA [@TiMBA] answer a different question, namely how
wood flows respond to prices and policy; their results can serve as input to
`aiphoria`.

What has been missing is a reusable tool that starts from production and trade
statistics, follows wood to its end uses and back through recycling, and keeps
mass and carbon balanced over time. Compared with the tools above, `aiphoria`
adds:

- absolute amounts and shares solved together in one mass-balanced system;
- in-use stocks with product lifetime distributions, calculated with ODYM;
- carbon stocks and annual CO2 removals for each product stock and age cohort;
- scenarios defined in Excel, with constrained and unconstrained solver modes;
- interactive Sankey diagrams for every year and a network graph of the system.

# Software design

`aiphoria` has three layers (\autoref{fig:design}). The `DataProvider` reads
the Excel file; the `DataChecker` checks the data, fills in missing years, and
builds the baseline and alternative scenarios; and the `FlowSolver` calculates
flows and stocks year by year. Results are saved as Excel and CSV files, and
the Sankey diagrams and network graph as HTML files.

The whole model, including lifetimes, carbon contents, and scenarios, is
described in one Excel file. This limits what the
user can express compared with code, but keeps the tool open to analysts who
do not program and makes a model easy to share and review.

Each flow is given either as an absolute amount or as a share of the remaining
outflow of its source process. For every year, the solver starts from the
known absolute flows and calculates the rest so that the inputs and outputs of
each process balance. Flows into in-use stocks are passed to ODYM's dynamic stock model, which uses a lifetime
distribution to calculate the stock and its outflow by age cohort. These
outflows enter the flow network again in the next year, for example as
recycled wood or as wood for energy. Reusing ODYM means the stock calculations
rely on a tested method.

Scenarios change selected flows over time, for example decreasing a flow share
by 50% over five years. In the constrained mode, the default, a change that the
data cannot supply stops the run, and the model reports the largest possible
change. In the unconstrained mode the change is always applied and virtual
flows fill the gap, which suits exploratory work. Virtual flows also close
unreported imbalances in the input data.

`aiphoria` models flows and stocks along one dimension only: time. Location,
processing stage, and carbon content are attributes of processes and flows,
not separate dimensions as in ODYM and flodym. This keeps the input simple and
is enough for national and regional wood-flow studies, but it limits analyses
that need to split results by, for example, region and product type at once.

![The three layers of an `aiphoria` run, from the Excel input to the results.
\label{fig:design}](figures/software_design.pdf){ width=100% }

A `pytest` suite runs on every push through GitHub Actions and covers mixed
flows, mass balance, both solver modes, carbon calculations, and a full run of
the example. The package is on PyPI (`pip install aiphoria`).

# Illustrative example

`aiphoria` comes with an example scenario that runs with two lines of code:

```python
from aiphoria.example import run_example
run_example(remove_existing_output_dir=True)
```

The example uses illustrative values for a sawnwood chain in one country from
2021 to 2030 (\autoref{tab:input}). Sawmilling turns roundwood into sawnwood
and residues. Sawnwood is imported, exported, and used in construction (mean
lifetime 10 years) and furniture (5 years). At end of life, 40% of the construction wood returns to sawmilling
as recycled wood, and the rest, together with all furniture, goes to
incineration. An alternative scenario reduces sawmilling residues by 50%
between 2025 and 2030.

: Flows of the example scenario as entered in the Excel input (year 2021).
Values are illustrative. \label{tab:input}

| Source | Target | Value | Unit |
|---|---|---:|---|
| Industrial roundwood | Sawmilling | 60 | Mm³ |
| Sawmilling | Residues | 10 | Mm³ |
| Sawmilling | Sawnwood | 100 | % |
| Sawnwood (import) | Sawnwood | 10 | Mm³ |
| Sawnwood | Sawnwood (export) | 20 | Mm³ |
| Sawnwood | Construction | 60 | % |
| Sawnwood | Furniture | 40 | % |
| Construction | Sawmilling | 40 | % |
| Construction | Incineration | 60 | % |
| Furniture | Incineration | 100 | % |

\autoref{fig:example} shows the resulting flows. In 2021 (a), almost all wood
entering construction and furniture stays in use. By 2030 (b), the first
furniture and construction cohorts have reached end of life, so flows to
incineration and a recycling loop from construction back to sawmilling appear.

![Sankey diagram of the example scenario in (a) 2021 and (b) 2030, selected
with the year slider.
\label{fig:example}](figures/sankey_example.png){ width=100% }

The carbon stocks are also saved to Excel (\autoref{tab:example}). Furniture
has a short lifetime (5 years), so its stock stops growing at about 20 Mt C once
as much carbon leaves as enters. Construction has a longer lifetime (10 years),
so its stock keeps growing until 2030.

: Carbon stock in the in-use product stocks of the example scenario
(baseline), in million tonnes of carbon (Mt C), from the `Total_stock` sheet of
the output workbook. \label{tab:example}

| Stock | 2021 | 2024 | 2027 | 2030 |
|---|---:|---:|---:|---:|
| Construction | 5.4 | 21.6 | 37.8 | 53.2 |
| Furniture | 3.6 | 14.3 | 19.7 | 20.0 |

# Research impact statement

`aiphoria` has supported two peer-reviewed studies. It was used to map wood
material flows across the EU forest sector [@Orfanidou2026] and to reconstruct
the Italian forest-wood value chain [@Khan2026]. The package was developed in
the Horizon Europe ForestPaths project, is in active use at EFI, and has had
more than sixteen releases under an MIT licence, with documentation in the
project wiki.

# AI usage disclosure

The authors used Anthropic's Claude models (Claude Sonnet 5 and Claude Opus
5.5) while preparing this paper. All scientific content, design decisions, and
the software itself were produced by the authors, who reviewed, edited, and
verified every AI-assisted change.

# Acknowledgements

`aiphoria` was developed by the European Forest Institute (EFI) and the
Flemish Institute for Technological Research (VITO) in the ForestPaths
project. We thank Gustavo Ezequiel Martinez, Pieter Johannes Verkerk, and
Giuseppe Cardellini for their support during the development and use of
`aiphoria`, and Arthur Jakobs for contributions to packaging and CI/CD setup.

This work received funding from the European Union's Horizon Europe Research
and Innovation Programme under grant agreements ForestPaths (No 101056755),
Monifun (No 101134991), and eco2adapt (No 101059498).

# References
