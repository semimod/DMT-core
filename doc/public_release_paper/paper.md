---
title: 'DMT: A Python toolkit for electrical engineers'
tags:
  - Python
  - electrical engineering
  - modeling
  - measurement data
  - circuit simulation
  - TCAD simulation
authors:
  - name: Mario Krattenmacher^[co-first author] # note this makes a footnote saying 'co-first author'
    orcid: 0000-0003-1274-3429
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
  - name: Markus Müller^[co-first author] # note this makes a footnote saying 'co-first author'
    orcid: 0000-0003-1058-1649
    affiliation: "1, 2"
  - name: Pascal Kuthe^[corresponding author]
    affiliation: "1, 2"
affiliations:
 - name: CEDIC, TU Dresden, 01062 Dresden, Germany
   index: 1
 - name: SemiMod UG (h.b.), 01159 Dresden, Germany
   index: 2
date: 20 February 2022
bibliography: paper.bib
---

# Statement of need

Currently most electrical device modeling is done using proprietary software which results in non reproducible procedures and parameters. Device Modeling Toolkit (`DMT`) aims to fill this gap by offering a standard library of tools to obtain simulation and measurement data to be prepared for standardized and reproducible parameter extraction procedures.

NOTE: mhm we should also make the extraction module public (but maybe later ??)

# Summary

`DMT` offers a set of basic classes which are either used directly or intended to be subclassed.

Data inside `DMT` is stored in  `DataFrame` objects. This class is derived from `pandas.DataFrame` [@pandas] to utilize its speed and existing indexing logic. `DMT` enhances this class by routines from `scikit-rf` [@scikit-rf] and own routines to calculate electrical charateristics. Correct naming of the frame columns is enabled by a `DMT` specfic naming scheme using standardized specifiers. This allows to easily and transferable handle data independent from the source.

This data can be obtained from simulation or measurement of either single devices or full electrical circuits. For this `DMT` offers different `DutView` (Device Unter Test) subclasses. In `DutView` common properties of devices are stored and a database access is offered to safely store and load data on the hard drive. The subclasses enhance these possibilities by:

* `DutMeas` allows reading, storing and accessing of measurement data
* `DutCircuit` is an abstract interface for circuit simulators. The interface is implemented for
  * Xyce [@xyce] in `DutXyce` and
  * [ngspice](http://ngspice.sourceforge.net) in `DutNgspice`
* `DutTCAD` is an abstract interface for TCAD device simulators. The interface is implemented for
  * Hdev [@hdev] in `DutHdev`

More simulators are easy to implement and can later be used as drop in replacements for the given simulators. This is possible because `DMT` interfaces the simulators by calling them with a generated input file and reading the results into a `DataFrame`. This way only these two steps have to be implemented to allow to use a different simulator (see \autoref{fig:interface}).

![TODO!! DMT interfacing a circuit simulator.\label{fig:interface}](DMT-interface.png){width=50%}

![Alternative: DMT interfacing a circuit simulator.\label{fig:interface2}](simulation_interface.png){width=50%}

Mutliple `DutView` objects can be collected in a `DutLib` to be handled collectivly. This is usefull for technology charateriziations and model extractions, since in there processes many different devices are measured and then processes in parallel and dependent on each other.

The simulations of circuit and TCAD simulators are managed together in the `SimCon` class. This allows to call many simulations in parallel and utilize the high core count of many modern computers, although the simulators are often still single threaded. Also the simulations can be easily compared, because both circuit and TCAD simulations consists of two parts, one is the device, which is described by a `DutView`, and secondly the operation condition. The operation condition consists of for example ambient temperature and applied voltages to the dut contacts. These conditions are swept inside of a simulation and hence `DMT` offers the class `Sweep` to describe the conditions in python.

To make the electrical circuit description in `DMT` transferable from one `DutCircuit` to another, the `Circuit` class offers a strongly type tested way. The type testing is done there to ease the implementation of the interfaces. This reduces the number of possibilities of circuit topologies, but since `DMT` focuses on single devices or small circuits this trade off was chosen.

This leads to the final feature `DMT` offers. As many device models have a defined set of model parameters each with special valid ranges `MCard` allows the easy handling of the model parameters. It can read model codes, carry, save and load a list of parameters and finally be used as `Circuit` elements in circuit simulations. The parameters inside a `MCard` are always valid and can be limited to be in the valid range. These parameters can be used later in parameter extraction procedures which often are badly conditioned numerical optimizations.

Finally, for an everyday use of model engineers, `DMT` implements `Plot` to easily display device characteristics using different back-ends. The Back-ends range from `matplotlib` or `pyqtgraph` for direct to `LaTeX:pgfplots` for saving and using the plots in technical documentations or scientific publications.

# Mentioned

The DMT project is already used internally by CEDIC in research and SemiMod in production. Furthermore DMT has been used by selected partners for their work.

The project is mentioned in the following papers

* [@weimer]
* There was a conference paper from Wladek (or someone else) where he said: If they release others can shut down ??
* others?

# Related projects

DMT uses two other open source projects in order to handle Verilog-AMS files for models

* DMT uses [verilogae](https://man.sr.ht/~dspom/openvaf_doc/verilogae/) [@verilogae] to access data in Verilog-AMS files. Verilog-AMS is a standardized programming language for device models. verilogae is used so the implemented model can be used simulataniously in DMT and also in circuit simulation. The circuit simulation is possible for example using the [Xyce](https://xyce.sandia.gov/) [@xyce] interface DutXyce.
* DMT is used as a front end for the open-source TCAD device simulator [Hdev](https://gitlab.com/metroid120/hdev_simulator) [@hdev]. DutHdev implements the input generation, simulation call and result reading. The results then can be used in further calculations and plotted using the DMT plot tools.

# Acknowledgements (TODO)

We acknowledge contributions from Christoph Weimer and Prof. Schröter

# References
