.. _intro:

Introduction
=============

This page ist a short introduction in the basic workflow and classes using ``DMT``. This guide here wil focus on the ``core`` (:ref:`DMT.core <dmt_core>`). module of DMT as this is the only public available module at the moment.

The usual workflow is to import the modules and classes of DMT you need for the current use case. But for the sake of this intro lets import the full core module first:

.. code-block:: python

    from DMT import core

The final goal of this intro will be to compare measurement data to a Spice-Gummel-Poon model with a suitable model card. This is an every day task and ``DMT`` is perfectly suited for that.

This is split up into multiple sections which itself can be used independently.

Read measurement data
---------------------

In the first step lets consider a ``.csv``-File which contains measurement data from a arbitrary measurement device. The file looks like this:

.. csv-table:: Measurement data at 300 K
    :file: _static/meas_data_300K.csv
    :header-rows: 1

This is a typical measurement of an bipolar transistor. It is measured at 300 K in a common-emitter configuration with constant base-collector voltage. Additionally at each DC operation point a AC-Measurement with two frequencies is run. Also notice the inconsistent naming of the columns. This example here is artificially strange, but keeping the naming consistent is often an issue and DMT can handle this as will be shown in the next step.

As most data needs some context, most data inside ``DMT`` is handled in context with a device. Hence a measurement device under test (DUT) is created and used to import this data with the following lines:

.. code-block:: python

    dut_meas = core.DutMeas(
        database_dir=None, # Use dir from config
        dut_type=core.DutType.npn, # it is a BJT-npn
        width=float(1e-6),
        length=float(2e-6),
        name="dut_meas_npn", # name and width/length for documentation
        reference_node="E", # defines configuration
    )
    dut_meas.add_data(path_file.parent.parent / "_static/meas_data_300K.csv", key="300K/iv")

This method tries different approaches in order to read the supplied data into a ``DataFrame`` (:ref:`DMT.core.DataFrame <data_frame>`). As it is a  ``.csv``-File, the pandas csv-reader is used and then the result is casted into a DMT-DataFrame. The ``DataFrame`` object can then be accessed via its key.

To make the result compliant with DMT and clean the messed up column headers, the resulting frame is cleaned next:

.. code-block:: python

    dut_meas.clean_data(fallback={"E_": "E"})

``DMT`` automatically capitalizes everything and respects the fallback dictionary first. This way the column ``I_E_`` is read as  ``I_E``. In then all the column names are converted into ``SpecifierStr`` (:ref:`DMT.core.naming <naming>`) objects. These specify exactly what data is in each column and now the data can be accessed in the full ``DMT`` package and all associated scripts the same way. By ensuring this naming scheme also data can be easily compared.

Also note:

.. code-block:: python

    dut_meas.data["300K/iv"].columns
    > Index(
        ['V_C', 'V_E', 'V_B', 'I_E', 'I_C', 'I_B', 'FREQ', 'Y_CB', 'Y_BB', 'Y_CC', 'Y_BC'],
        dtype='object'
     )

The  ``SpecifierStr`` objects are displayed and can be used exactly like regular strings but have some useful attributes and methods. Also the Y-parameters are translated to "standardized" Y-parameters, this is useful for circuit simulations with more than two AC-sources, for example you can do "Y_BE" (input at emitter and measured at base).
We will show you how to generate ``SpecifierStr`` objects later.

Preparing a simulation
----------------------

In order to run a simulation of an BJT different things are needed:

* a circuit simulator
* A model (either build-in or as Verilog-AMS code)
* model parameter





In order to run a simulation and for especially to read one the ``SpecifierStr`` class really shows its advantages.