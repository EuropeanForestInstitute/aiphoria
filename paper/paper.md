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
 
`aiphoria` is an open-source Python package for dynamic material flow analysis (DMFA) of wood products. It helps tracking how wood moves through socioeconomic systems, from harvested timber through semi-finished products to end uses such as construction, furniture, and paper, and how carbon is stored in those products or released back to the atmosphere over time. The package builds on ODYM [@Pauliuk2020], a general-purpose dynamic material systems model, and adds the workflow that wood-sector analysis needs: mixed input formats (absolute volumes together with relative shares), temporary carbon storage accounting, and interactive Sankey diagrams of the flow system at any timestep. Scenarios are defined in an Excel file, so users without programming experience can run a full analysis. Results include time series of material flows, in-use stocks, and carbon stock changes, exported for further analysis or direct visualisation.
 
 
# Statement of need
 
The forest-wood value chain holds an important place in Europe's climate mitigation efforts [@verkerk2022]. Forests sequester carbon in biomass and soil; harvested wood products (HWP) extend that sequestration into the technosphere by storing carbon in long-lived applications such as construction timber and engineered wood panels; and wood-based materials and energy displace fossil -based alternatives. These three mechanisms, forest carbon storage, HWP carbon storage, and material and energy substitution, interact across the full life cycle of wood, and their joint optimisation is a defining challenge of sustainable bioeconomy governance. Tracking how wood flows through the economy and how long carbon remains locked in products before returning to the atmosphere is central to assessing the mitigation potential of the forest-based bioeconomy [@BrunetNavarro2016]. aiphoria is also complementary to forest-sector market models such as EFI-GTM [@Kallio2004] and TiMBA [@TiMBA2025], which project wood supply and demand at the market level. Projections from these models can be integrated with historic statistics and end-use shares inside aiphoria, linking market-level outlooks to the underlying physical material and carbon stock changes.
 
Dynamic material flow analysis provides the quantitative basis for this [@Brunner2016]: by tracking wood mass and carbon through the system over time, it links harvest, product stocks, and end-of-life pathways into a single, mass-balanced account. The main challenge is the data. Forest sector and wood use data come in different forms: production and trade are reported in absolute volumes (m³ or tonnes), while end-uses are often connected to semi-finished wood products as shares (for example, the percentage of sawnwood going to construction). Connecting these data into one consistent system has so far required custom preprocessing that is hard to reproduce across studies, which in turn limits scenario analysis at the end-use level. `aiphoria` is built for the users who run into this problem, for example, forest economists, bioeconomy analysts, and LULUCF experts working at national or regional scale, often from spreadsheet data rather than code. It takes absolute and relative flows together, converts the relative shares into absolute flows while preserving mass balance, and propagates carbon coefficients through the stocks, so a dataset that mixes the two becomes a reproducible wood-flow and carbon stock account without custom scripting or preprocessing.
 
 
# State of the field
 
General-purpose dynamic MFA frameworks such as ODYM [@Pauliuk2020] and flodym [@flodym] provide the modelling foundation for material systems, but the user has to define each system, i.e., its processes, flows, and dimensions, in code. Rather than re-implement stock dynamics, `aiphoria` reuses ODYM's `DynamicStockModel` as its computational engine and contributes the domain layer on top: the wood-sector workflow, the mixed absolute and relative flows solver, and temporary carbon storage assessment.
 
The main capabilities `aiphoria` adds are:
 
|Capability|`aiphoria`|
|-|-|
|Automated stock–flow solver (`FlowSolver`)|yes|
|Mixed absolute and percentage flows in one system|yes|
|Carbon stock tracking across age cohorts|yes|
|Interactive Sankey visualisation, per timestep|yes|
|Network graph of the full system|yes|
|Excel scenario input|yes|
|Constrained and unconstrained solver modes|yes|
|Virtual flows for accounting-only transfers|yes|
|`pip install` distribution|yes|
 
Mixed absolute and relative flow solving is the central contribution: it lets production, import, and export statistics which are typically available at the semi-finished wood product level to be linked directly to end uses, without first converting everything to a single flow type by hand. Carbon stock tracking can be integrated into the same flow model, computing temporary carbon storage in wood products across cohorts and timesteps, which is what bioeconomy and LULUCF accounting require. The same structure also supports user-defined transfer coefficients beyond carbon (e.g., employment, revenue, etc.), propagated across cohorts and timesteps in the same way.
 
 
# Software design
 
`aiphoria` is organised in three layers, a design that separates what the user provides from how the system is solved and reported.
 
The **input layer** is an Excel settings file in which the user defines processes, flows, parameters, the time range, and one or more scenarios. Using a spreadsheet as the interface trades some flexibility for accessibility: it keeps the tool usable by users who do not need to have programming knowledge.
 
The **solver layer** is the `FlowSolver`. It resolves mixed absolute and relative flows defined in the Excel file by converting percentage shares into absolute flows from upstream values, then calls ODYM's `DynamicStockModel` for each in-use stock process. Outflows are derived from product lifetime distributions and fed back into the flow network. The solver runs in two modes by design: an unconstrained mode for exploratory scenario work, and a constrained mode that applies flow modifiers strictly and reports exactly which flows the data cannot supply, which makes it a diagnostic tool for building normative scenarios. Stock accumulation can be bypassed for flows that never enter use (for example, direct exports), and *virtual flows* let the model carry transfers that are needed for accounting but do not exist as separate physical movements.
 
The **output layer** writes results to a structured directory: per-timestep Sankey diagrams and a network graph open automatically in the browser, and all numerical results are saved as Excel or CSV files.
 
A complete analysis runs without writing modelling code:
 
```python
from aiphoria.example import run_example
run_example(remove_existing_output_dir=True)
```
 
Correctness is checked with a `pytest` suite run on every push through GitHub Actions, covering absolute, relative, and mixed absolute and relative flows resolution, mass balance, both solver modes, the carbon stock calculations, and an end-to-end run of the example scenario. The package is distributed on PyPI (`pip install aiphoria`).
 
 
# Research impact statement
 
`aiphoria` has supported two peer-reviewed studies so far. It was used to map wood material flows and added-value wood product markets across the EU forest sector [@Orfanidou2026] and to reconstruct the Italian forest-wood value chain [@Khan2026]. The package was initially developed in the Horizon Europe ForestPaths project and is in active use at EFI; it is openly released under an MIT licence with documentation in the project wiki, has issued more than sixteen versioned releases, and is installable from PyPI, so it is ready for use beyond the original author group.

 
# AI usage disclosure
 
Open 4.8 was used to assist with copy-editing and structuring the text of this paper. All scientific content, design decisions, and software were produced and verified by the authors, who reviewed and edited every AI-assisted suggestion.
 
 
# Acknowledgments
 
We thank Arthur Jakobs for contributions to packaging and CI/CD setup, and Gustavo Ezequiel Martinez, Pieter Johannes Verkerk, and Giuseppe Cardellini for their support during the development and testing of `aiphoria`. This work received funding from the European Union's Horizon Europe Research and Innovation Programme under grant agreements ForestPaths (No 101056755), Monifun (No 101134991), and eco2adapt (No 101059498).
 
 
# References
