
.. _dut_view:

DutView
================

A Device Unter Test (DUT) can be single devices or full circuits and range from atomic TCAD simulations to full circuit simulations and also measurements. This range of different DUTs is represented in DMT as a view on a DUT. The name view is chosen, because sometimes the same device is measured and simulated in different simulators. So this "view-axis" can change, always the same are the DUT properties and also the data handling.

Submodules of DutView
-------------------------------

.. toctree::
    :maxdepth: 1

    duts_meas/dut_type
    duts_meas/dut_meas
    duts_tcad/dut_tcad
    duts_circuit/dut_circuit


Relation of the Submodules
-------------------------------

.. graphviz:: ../diagrams/classes_dut.dot


DutView class
------------------------------

.. automodule:: DMT.core.dut_view
    :members:
    :undoc-members:
    :show-inheritance:
