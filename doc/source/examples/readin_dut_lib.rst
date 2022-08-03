Reading the Skywater130 raw data
=================================

Google released `raw experimental data<https://github.com/google/skywater-pdk-sky130-raw-data>`__`` for the SKY130 open source process technology.  This data is stored in the MDM format which is ideal to show the application of DMTs data acquisition tools. A simple direct read of a single measurement to a :ref:`DataFrame<data_frame>` is shown in the test case `test_read_skywater_mdm<https://gitlab.com/dmt-development/dmt-core/-/blob/main/test/test_core_no_interfaces/test_read_mdm.py>`

In this example, we will show how to read all devices in the measurement data into a :ref:`DMT.DutLib<dut_lib>`. Also, it is shown how to access the data inside the library and finally how to document the measurement in LaTeX.

The code
--------

.. literalinclude:: readin_dut_lib.py


The generated files
-------------------

.. figure:: /_static/readin_dut_lib/IDVG.png

.. literalinclude:: /_static/readin_dut_lib/IDVG.tex
    :language: latex
    :linenos:
    :caption: IDVG.tex with legend in 3 columns (manually)