Introduction
===============================

DeviceModelingToolkit (DMT) is a python tool targeted at helping modeling engineers extract model parameters, run circuit and TCAD simulations and automate their infrastructure.

The project ist still in its infancy, though many things already work. Here is an incomplete list of already working stuff:

- HiCUML2 scalable model parameter extraction
- HiCUML0 model parameter extraction
- NGSpice, Xyce, Spectre and ADS circuit simulator interface
- DEVICE, Spring and Hdev TCAD simulator interface
- Data management with pandas
- Typical electrical engineering relevant equations such as S-to-Z parameter conversions and so on are mostly implemented
- Many examples
- Many test cases

Currently ongoing projects:

- VSource model availability
- Our partner project `VAE <https://man.sr.ht/~dspom/openvaf_doc/verilogae/>`_, a new verilog-A compiler aimed at replacing ADMS once and for all

Ongoing goals:

- Improve documentation
- Test coverage of > 80 %

DMT is applied in several industry research projects and has matured such that it may be used by
people that know how to work with large software projects that are not yet finished.
Achieving better usability for engineers that do not have the time or skills to dive into such a project is not one of our current goals.

If you have used our framework for research purposes, please cite us with:

.. code:: tex

    @misc{pymoo,
    author = {M. Krattenmacher, M. Mueller and M. Schroeter},
    title = {DMT - {Device-Modeling-Toolkit}},
    howpublished = {https://www.iee.et.tu-dresden.de/iee/eb/eb_home.html}
    }

Currently DMT is developed
at SemiMod, by:

* Dipl.-Ing. M.Krattenmacher
* Dipl.-Ing. M.Müller


Overview of Documentation
===============================

.. toctree::
    :maxdepth: 1

    examples/index
    automatic_testing/index
    technical_documentation/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
