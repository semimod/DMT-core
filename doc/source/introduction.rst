.. _intro:

Introduction
=============

This page ist a short introduction in the basic workflow and classes using ``DMT``. This guide here wil focus on the ``core`` (:ref:`DMT.core <dmt_core>`). module of DMT as this is the only public available module at the moment.

The usual workflow is to import the modules and classes of DMT you need for the current use case. But for the sake of this intro lets import the full core module first and also define the place where our data is located:

.. code-block:: python

    from pathlib import Path
    from DMT import core
    path_data = Path(__file__).resolve().parent / "_static" / "intro"

The final goal of this intro will be to compare measurement data to a Spice-Gummel-Poon model with a suitable model card. This is an every day task and ``DMT`` is perfectly suited for that.

This is split up into multiple sections which itself can be used independently.

The pure source code of the code is available in the gitlab repository `here <https://gitlab.com/dmt-development/dmt-core/-/tree/main/doc/source/examples/introduction.py>`__

Read measurement data
---------------------

In the first step lets consider a ``.csv``-File which contains measurement data from a arbitrary measurement device. The file looks like this:

.. csv-table:: Measurement data at 300 K
    :file: _static/intro/meas_data_300K.csv
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
    dut_meas.add_data(path_data / "meas_data_300K.csv", key="300K/iv")

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

* a circuit simulator,
* a model (either build-in or as Verilog-AMS code),
* model parameter,
* a circuit,
* and finally operation conditions (temperature, applied voltages and frequencies).

For this introduction we start at the model defined using a Verilog-AMS source file:

.. code-block:: python

    modelcard = core.MCard(
        ["c", "b", "e", "s"],
        "QSGP1",
        core.circuit.SGP_BJT,
        1.0,
        va_file=path_data / "sgp_v1p0.va",
    )

The ``MCard`` is now created with some information about the model. Most important is the subcircuit name and the Verilog-AMS code. Using `verilogae <https://man.sr.ht/~dspom/openvaf_doc/verilogae/>`__ the source file is read and the parameters with their default values are collected. The subcircuit name is used as device name in the circuit later.

Let's assume we have a model library in which we store the parameters for this technology and now we want to load the parameter values into our modelcard. ``MCard`` offers the method

.. code-block:: python

    modelcard.load_model_parameters(path_data / "bjt.lib")

to do exactly this.

This way we already crossed off two points of our to-list to arrive at our simulation. The next is a little tricky, we want a circuit in which a device with our model and modelcard is used. We have two options, either directly make this circuit for the use case here or overwrite the  abstract ``MCard.get_circuit`` method and pass the modelcard directly into our simulator interface. We will use the second option and also, since the method is abstract you may notice that MCard is intended to be subclassed for the models you use most often.

In this introduction we will go the non-intuitive way of overwritting the method just for this single instance (method binding). So lets create a circuit:

.. code-block:: python

    def get_circuit(self):
        """Returns a circuit which uses the modelcard to which the method is attached.

        Returns
        -------
        circuit : :class:`~DMT.core.circuit.Circuit`

        """
        circuit_elements = []
        # model instance
        circuit_elements.append(
            core.circuit.CircuitElement(
                self.default_module_name,
                self.default_subckt_name,
                [f"n_{node.upper()}" for node in self.nodes_list],
                # ["n_C", "n_B", "n_E"],
                parameters=self,
            )
        )

        # BASE NODE CONNECTION #############
        # shorts for current measurement
        circuit_elements.append(
            core.circuit.CircuitElement(core.circuit.SHORT, "I_B", ["n_B_FORCED", "n_B"])
        )
        # COLLECTOR NODE CONNECTION #############
        circuit_elements.append(
            core.circuit.CircuitElement(core.circuit.SHORT, "I_C", ["n_C_FORCED", "n_C"])
        )
        # EMITTER NODE CONNECTION #############
        circuit_elements.append(
            core.circuit.CircuitElement(core.circuit.SHORT, "I_E", ["n_E_FORCED", "n_E"])
        )
        # add sources
        circuit_elements.append(
            core.circuit.CircuitElement(
                core.circuit.VOLTAGE,
                "V_B",
                ["n_B_FORCED", "0"],
                parameters=[("Vdc", "V_B"), ("Vac", "V_B_ac")],
            )
        )
        circuit_elements.append(
            core.circuit.CircuitElement(
                core.circuit.VOLTAGE,
                "V_C",
                ["n_C_FORCED", "0"],
                parameters=[("Vdc", "V_C"), ("Vac", "V_C_ac")],
            )
        )
        circuit_elements.append(
            core.circuit.CircuitElement(
                core.circuit.VOLTAGE,
                "V_E",
                ["n_E_FORCED", "0"],
                parameters=[("Vdc", "V_E"), ("Vac", "V_E_ac")],
            )
        )

        # metal resistance between contact emitter potential and substrate contact
        circuit_elements.append(
            core.circuit.CircuitElement(
                core.circuit.RESISTANCE, "R_S", ["n_S", "n_E_FORCED"], parameters=[("R", str(0.5))]
            )
        )

        # some variables used in this circuit
        circuit_elements += [
            "V_B=0",
            "V_C=0",
            "V_E=0",
            "ac_switch=0",
            "V_B_ac=1-ac_switch",
            "V_C_ac=ac_switch",
            "V_E_ac=0",
        ]

        return core.circuit.Circuit(circuit_elements)

This is just straight forward the device with sources on all nodes except the substrate. The sources are connected using shorts to measure the current, because not all simulators allow current measuring at sources.

To bind the method to our modelcard, we have to import the ``types`` module:


.. code-block:: python

    import types

    modelcard.get_circuit = types.MethodType(get_circuit, modelcard)

Finally we can pass this model card to a circuit simulator interface which can handle Verilog-AMS files. In the core, this is possible using the simulator Xyce:

.. code-block:: python

    from DMT.xyce import DutXyce
    dut_sim = DutXyce(
        None,
        core.DutType.npn,
        modelcard,
        nodes="C,B,E",
        reference_node="E",
    )

The dut uses the get_circuit method of the modelcard to obtain a valid circuit. So we now have ticked of the circuit from our to-do-list. Only the sweep definition is missing now.

For this our toolkit allows to extract the sweep definition from a suited ``DataFrame`` instance, like the one we have here. So we just call

.. code-block:: python

    sweep = core.df_to_sweep(dut_meas.data[key_saved], temperature=300, from_forced=False)

In some cases this will not work, since data ordering and its corresponding measurements can be quite different, so if your ``DataFrame`` instance can not be converted by this approach, do not hesitate to create an `issue on github <https://gitlab.com/dmt-development/dmt-core/-/issues>`__ and supply us with an example of your measurement data. More test data is always welcome.

The simulation is the easiest part now:

.. code-block:: python

    sim_con = core.SimCon()
    sim_con.append_simulation(dut=dut_sim, sweep=sweep)
    sim_con.run_and_read()

Accessing the data and plotting
-------------------------------

Now the data is simulated and ready to use for us. In this short introduction we will show how to access and add more data to the ``DataFrame``, before finally plotting them in a suitable way for documentations or papers.

To access the data we have to differentiate between the measurement data and the simulation data:

.. code-block:: python

    data_meas = dut_meas.data[key_saved]
    data_sim = dut_sim.get_data(sweep=sweep)

For the measurement data, we named the key ourselves. For simulations, ``DMT`` converts a sweep into a valid key string in which the simulation data is read, this can be used to access the data. This valid key string is an MD5-Hash created from the sweep and is also used as folder name to save the simulation. So no simulation has to be run twice. Sometimes one has to delete the simulation folder manually to get rid of old simulations as your drive will be flooded with simulations at some point.

Now we want to access the different columns inside the ``DataFrame`` instances and now the ``SpecifierStr`` class really shows its advantages. We create some column names we will use first:

.. code-block:: python

    col_vbe = core.specifiers.VOLTAGE + ["B", "E"]
    col_vbc = core.specifiers.VOLTAGE + ["B", "C"]
    col_ic = core.specifiers.CURRENT + "C"
    col_freq = core.specifiers.FREQUENCY
    col_ft = core.specifiers.TRANSIT_FREQUENCY
    col_y21_real = core.specifiers.SS_PARA_Y + ["C", "B"] + core.sub_specifiers.REAL

    for dut, data in zip([dut_meas, dut_sim], [data_meas, data_sim]):
        data.ensure_specifier_column(col_vbe)
        data.ensure_specifier_column(col_vbc)
        data.ensure_specifier_column(col_ft, ports=dut.ac_ports)
        data.ensure_specifier_column(col_y21_real, ports=dut.ac_ports)

These new column names are instantly used to add the voltages, the transit frequency and the real part of y_21 to the frames. independently which frame it is, the handling is the same and it even goes further, but before we need to define the plots:

.. code-block:: python

    plt_ic = core.Plot(
        plot_name="I_C(V_BE)",
        x_specifier=col_vbe,
        y_specifier=col_ic,
        y_scale=1e3,
        y_log=True,
        legend_location="lower right",
    )
    plt_y21 = core.Plot(
        plot_name="Y_21(I_C)",
        x_specifier=col_ic,
        x_scale=1e3,
        x_log=True,
        y_specifier=col_y21_real,
        y_scale=1e3,
        y_log=True,
        legend_location="lower right",
    )
    plt_ft = core.Plot(
        plot_name="F_T(I_C)",
        x_specifier=col_ic,
        x_scale=1e3,
        x_log=True,
        y_specifier=col_ft,
        legend_location="upper left",
    )

Again the specifiers are used, this time to make formatting and displaying nicer. This shows how they are also nice for good looking documentations. Fist lets add data to the plots:

.. code-block:: python

    import numpy as np

    for source, data in zip(["meas", "sim"], [data_meas, data_sim]):
        for i_vbc, vbc, data_vbc in data.iter_unique_col(col_vbc, decimals=3):
            data_freq = data_vbc[np.isclose(data_vbc[col_freq], 1e7)]
            plt_ic.add_data_set(
                data_freq[col_vbe],
                data_freq[col_ic],
                label=source + " " + col_vbc.to_legend_with_value(vbc),
            )
            plt_y21.add_data_set(
                data_freq[col_ic],
                data_freq[col_y21_real],
                label=source + " " + col_vbc.to_legend_with_value(vbc),
            )
            plt_ft.add_data_set(
                data_freq[col_ic],
                data_freq[col_ft],
                label=source + " " + col_vbc.to_legend_with_value(vbc),
            )

This also heavily leans on the specifiers and the easy data handling ``DMT`` offers. But here are multiple things to unpack:

#. the ``zip`` is used again to handle the both frames the same way.
#. ``DataFrame.iter_unique_col`` allows to easily iterate through uniqued data. Here it is an overkill, since we only have V_BC = 0, but in case this changes the script is already prepared.
#. In the next line, the pandas indexing is used together with a numpy filter. This way one can easily select the wanted rows.
#. The correct columns are added to the plots using the specifiers from above.
#. ``SpecifierStr`` instances offer many methods for pretty printing. The shown variant here, includes all of them at once, The variable is pretty printed together with an value with a possibly scaled unit.

To have a look at the plots we can use different back-ends. ``pyqtgraph`` is the fastest:

.. code-block:: python

    plt_ic.plot_pyqtgraph(show=False)
    plt_y21.plot_pyqtgraph(show=False)
    plt_ft.plot_pyqtgraph(show=True)

Additionally it is quite easy to export the plots to be ready for documentations or scientific papers:

.. code-block:: python

    plt_ic.save_tikz(path_data, standalone=True, build=True, clean=True, width="3in")
    plt_y21.save_tikz(path_data, standalone=True, build=True, clean=True, width="3in")
    plt_ft.save_tikz(path_data, standalone=True, build=True, clean=True, width="3in")

The plots look like this:
