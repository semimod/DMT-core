Introduction
===============================

DeviceModelingToolkit (DMT) is a Python package targeted at helping modeling engineers extract model parameters, 
run circuit and TCAD simulations, and automate their infrastructure.

Here is an incomplete list of features:

- NGSpice and Xyce circuit simulator interface
- Hdev TCAD simulator interface
- Data management with Pandas
- Equations relevant for electrical engineering such as S-to-Z parameter conversions are implemented
- Verilog-AMS model parameter reading and handling in model cards
- Many examples
- Many test cases

We rely on our partner project 
`VAE <https://man.sr.ht/~dspom/openvaf_doc/verilogae/>`__, 
for dealing with Verilog-A code. 

DMT is applied in several industry research projects and has matured such that it may be used by
people that know how to work with large software projects. It is not a GUI tool, but a framework that 
requires you to look at examples, test-cases and software documentation in order to build 
your own scripts. 
Achieving better usability for engineers that do not have the time or skills to dive into such a project is not one of our current main goals. DMT is a very high level toolkit and has many optional dependencies. One has to invest a serious amount of time to the steep learning curve of a python, wanted interface and finally ouput (like plotting or writing reports) at the same time. This invest will pay of in the long run, as we can tell from experiance.

If you make this investment, the potential gains are

- simpler transfer between different interfaces for example different circuit simulators,
- direct access to all kind of data using the same syntax,
- faster exchange of scripts and hence workflows inside or outside of work groups and finally
- publications with sharable scripts as open data attachment.


If you have used our framework for research purposes, please cite us with:

TODO

.. code:: tex

    @misc{DMT,
    author = {M. Krattenmacher, M. Mueller and M. Schroeter},
    title = {DMT - {Device-Modeling-Toolkit}},
    howpublished = {https://www.iee.et.tu-dresden.de/iee/eb/eb_home.html}
    }

Currently DMT is developed at `SemiMod <https://semimod.de/>`__, by:

* Dipl.-Ing. Mario Krattenmacher
* Dipl.-Ing. Markus Müller
* Pascal Kuthe

Open-Source
--------------

The core package of DMT is available for everyone in a `gitlab.com repository <https://gitlab.com/dmt-development/dmt-core>`__ under GPLv3. If you find bugs, want to suggest enhancements or even join the developement team, the repository is the best point to start.

If are interested in other modules, need installation or usage support, or you want to use DMT in your own project contact: info@semimod.de

Questions, bugs and feature requests
------------------------------------

If you have any questions or issues regarding DMT, we kindly ask you to contact us. Either mail us directly or open an issue <here `https://gitlab.com/dmt-development/dmt-core/-/issues>`__. There we have prepared <several templates `https://docs.gitlab.com/ee/user/project/description_templates.html#use-the-templates>`__ for the description:

* <Questions `https://gitlab.com/dmt-development/dmt-core/-/issues/new?issuable_template=question>`__
* <Bug reports `https://gitlab.com/dmt-development/dmt-core/-/issues/new?issuable_template=bug_report>`__
* <Feature requests `https://gitlab.com/dmt-development/dmt-core/-/issues/new?issuable_template=feature_request>`__


Overview of Documentation
===============================

.. toctree::
    :maxdepth: 1

    installation/install_dmt
    introduction
    examples/index
    automatic_testing/index
    technical_documentation/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
