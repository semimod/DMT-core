Running a Simulation and Plotting
=================================

In ``DMT`` simulators are interfaced using the abstract classes :ref:`DutCircuit<dut_circuit>` and :ref:`DutTcad<dut_tcad>`. These classes define the missing methods which are needed to run any simulator either installed on your pc or on a remote server available using ftp and ssh.  The interface uses always the same steps which are shown in the following image:

.. image:: /_static/running_a_simulation/DMT-interface.png
    :width: 600
    :alt: DMT interface structure

#. A simulation controller :ref:`SimCon<sim_con>` instance calls the ``make_input`` method of the dut to simulate. This will then write the input file in a simulation folder. The folder is created in the simulation directory of the :ref:`config`: ``directories[simulations]/dut_folder/sim_folder``. The dut folder name consist of the dut name appended by the unique dut hash. The sim folder consist of the sweep name and the unique sweep hash. This way, no simulation has to be run twice.
#. The simulator binary is called using a sys call with the input file as a parameter in the simulation folder.
#. The simulator reads the input file and executes the simulation accordingly. If it returns a non-zero exit value, the ``simulation_successful`` return value is set to ``False``.
#. The simulator writes the simulation results into the simulation folder. This is often done in proprietary binary formats or at least with sorting and naming unknown to DMT.
#. For this the ``read_result`` method of the simulated dut is called to read and convert the results into the DMT format. If the simulation binary returned a non-zero exit value, the result is read anyway. Yes we know... but we tested many simulators, and they just behave strange...

After these steps the simulation results are ready to be used. An example code how to make a circuit simulation is shown in the following.


The code for the simulation
---------------------------
.. literalinclude:: running_a_simulation.py

The generated files
-------------------

.. figure:: /_static/running_a_simulation/J_CV_BE.png

.. literalinclude:: /_static/running_a_simulation/J_CV_BE.tex
    :language: latex
    :linenos:
    :caption: J_CV_BE.tex


.. figure:: /_static/running_a_simulation/F_TJ_C.png

.. literalinclude:: /_static/running_a_simulation/F_TJ_C.tex
    :language: latex
    :linenos:
    :caption: F_TJ_C.tex