---
title: 'DMT-core: A Python Toolkit for Semiconductor Device Engineers'
tags:
  - circuit simulation
  - compact modeling
  - electrical engineering
  - measurement data
  - open source
  - Python
  - TCAD simulation
authors:
  - name: Mario Krattenmacher^[co-first author] # note this makes a footnote saying 'co-first author'
    orcid: 0000-0003-1274-3429
    affiliation: "1, 2"
  - name: Markus Müller^[co-first author]
    orcid: 0000-0003-1058-1649
    affiliation: "1, 2"
  - name: Pascal Kuthe
    affiliation: "1, 2"
  - name: Michael Schröter
    affiliation: "1, 2"
affiliations:
 - name: CEDIC, TU Dresden, 01062 Dresden, Germany;
   index: 1
 - name: SemiMod GmbH, 01159 Dresden, Germany
   index: 2
date: 20 February 2022
bibliography: paper.bib
---

# Statement of need

Semiconductor device engineers are faced by a number of non-trivial tasks that can be solved efficiently using software.
These tasks include, amongst others, data analysis, visualization and processing, as well as interfacing various circuit and Technology-Computer-Aided-Design (TCAD) simulators.
In practice, custom 'home-made' scripts of varying quality are employed to solve these tasks.
It is often found that fundamental software engineering concepts, such as Test-Driven-Development [@Shull2010], or the use of state-of-the-art
version control tools (e.g. Git) and practices (e.g. continuous integration, CI), are not utilised by these scripts.
This causes severe inefficiencies with respect to the users cost and time.

The issues inflicted by this practice can be summarized as follows:

* The analysis/visualization/generation of data becomes difficult to reproduce.
* Device engineers work far from their maximum work-efficiency, as they are hindered, instead of empowered, by the employed software infrastructure.
* Knowledge built-up, possibly over decades, may fade away when developers leave a company or institution.

The Device Modeling Toolkit (`DMT`) presented here aims to solve these issues. `DMT` provides a Python library that offers:

* classes and methods relevant for day-to-day device engineering tasks
* several abstract base classes for implementing new interfaces to various types of simulators 
* concrete implementations of the abstract base classes for open-source simulators such as Ngspice [@Vogt2022], Xyce [@Keiter2021] or Hdev [@Hdev].

`DMT`-based simulations allow data generation, workflow implementation and visualization to be be implemented in a single file, allowing for cooperate more effectively and more reproducible research [@Stodden2016]. In addition, basic principles of software engineering, such as unit testing, version control, and documentation are adhered to,
so that others can also use and contribute to the software.

# Summary

`DMT` is implemented as a toolkit that heavily leverages principles of object-oriented software design.
Its Git repository contains documentation, and CI jobs that execute unit and integration tests, and create ready to install wheel files.
This enables a large community of engineers (with sufficient Python knowledge) to install, use and contribute to the software.

In `DMT` data is stored using `DataFrame` objects.
The `DataFrame` class is a subclass of `pandas.DataFrame` [@McKinney2010], ideally suited for processing and analyzing large amounts of data.
`DMT` extends this class with several data-processing methods that are particularly useful for electrical quantities such as currents, voltages and charges.
Some of these methods are based on routines in `scikit-rf` [@Arsenovic2022].

Electrical data comes from diverse sources such as experimental measurements or circuit simulations.
A central problem with such data is the naming of variables, which should be consistent throughout the code in order to process data in a unified way.
For example, some people might abbreviate the collector current of a bipolar transistor as $\textbf{I\_C}$,
while others might write $\textbf{IC}$ instead.
This can lead to major confusion when exchanging data and code with others.
`DMT` implements a bullet-proof grammar for naming electrical quantities for solving this problem.
During data import all data columns are translated to this grammar.
This solves a big issue when transferring data between engineers or even for a single engineer between different work stations and (proprietary) software.

`DMT` offers classes and methods which can be used either directly or need to be subclassed, i.e. for creating interfaces to circuit simulators.
The base class offered by `DMT` for representing electrical devices is called `DutView` (Device-Under-Test).
This abstract class provides common attributes and methods that represent measurements, circuit simulations or TCAD simulations.
There are several subclasses that add logic:

* `DutMeas` adds logic for DUT instances that contain measured data.
* `DutCircuit` is an abstract class that adds logic for DUT instances that represent circuit simulations. The interface is implemented in the DMT-core module for
  * Xyce [@Keiter2021] in `DutXyce` and
  * Ngspice [@Vogt2022] in `DutNgspice`.
* `DutTCAD` ads logic for DUT instances that represents devices based on TCAD simulations. The interface is implemented for
  * Hdev [@Hdev] in `DutHdev`.

Interfaces to other simulators, i.e. proprietary ones, are straight forward to implement.
All simulators can be used as drop-in replacements for each other.
There are only two necessary steps that need to be implemented for each simulator.
First, a routine for generating the simulator input file must be implemented. Second, an import routine that returns a `DataFrame` from the simulator output must be provided.
This is illustrated in \autoref{fig:interface}.

![DMT interfacing a circuit simulator and corresponding data flow.\label{fig:interface}](DMT-interface.pdf){width=80%}

Often one needs to handle many different devices, e.g. transistors with different geometries.
For this purpose the `DutLib` class offers a "container" for `DutView` objects,
e.g. for storing the measurement data of one wafer.
A typical use case is loading measurement data generated for a given technology, including specific test structures and transistors.

Circuit and TCAD simulations are started and controlled by the `SimCon` class.
This class enables the user to run many simulations in parallel and utilizes the high core count of modern computers.
Each simulation requires one `DutView` object that defines either a circuit or TCAD simulation,
as well as the definition of a sweep for changing the operating point.
The definition of sweeps, i.e. the sweep of voltages or currents, is controlled by objects of the `Sweep` class.
`SimCon` generates a hash for every simulation so that simulations need not be run when the software is called multiple times,
provided the simulation definition (and therefore the hash) have not changed.

Another important class is `MCard`,
useful for storing the model parameters of compact models that are defined within Verilog-A files.
It implements a container that may store all model parameters,
including information on parameter boundaries that is directly obtained from Verilog-A source files.
This feature leverages the VerilogAE tool [@Kuthe2020a].
`MCard` can interpret Verilog-A model codes, save and load lists of model parameters and can also be used to define elements in the `Circuit` class used for defining circuit simulations.

Finally, `DMT` implements the `Plot` class for displaying electrical data using different back-ends:

* `matplotlib` for interactive plots
* `pyqtgraph` for plots to be used in GUI applications
* `LaTeX:pgfplots` for TeX based technical documentation or scientific publications

An example plot of a simulated transistor is shown in \autoref{fig:results_1}.

![Transit frequency $f_{\mathrm{T}}$ of a Bipolar transistor.\label{fig:results_1}](F_TJ_C.pdf){width=45%}

# Related Publications

`DMT` is used internally by CEDIC staff in research and by SemiMod for commercial purposes. It has also been used by cooperating institutions and companies.
The project has been used in the following contexts:

* for circuit simulations [@Weimer2021],
* for TCAD simulations and plotting [@Muller2021],
* for circuit and TCAD simulations [@Muller2021a],
* for model parameter extraction [@Muller2020c] and
* for model parameter extraction and TCAD simulation [@Phillips2021].

In addition, `DMT` has been cited in [@Grabinski2019;@Kuthe2020a;@Muller2019a;@Muller2021b].

# Related Projects

`DMT` directly uses the [VerilogAE](https://man.sr.ht/~dspom/openvaf_doc/verilogae/) [@Kuthe2020a] for accessing all information in Verilog-AMS files.
The TCAD simulator [Hdev](https://gitlab.com/metroid120/hdev_simulator) [@Hdev] uses the class `DutHdev` as its Python interface.

# Acknowledgements

This project would not have been possible without our colleagues Dipl.-Ing. Christoph Weimer and Dr.-Ing. Yves Zimmermann.
We particularly acknowledge Wladek Grabinski for his efforts to promote the use of open source software in the semiconductor community.

# References
