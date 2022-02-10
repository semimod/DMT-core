Running Test Cases
==========================

The test cases are a great starting point to learn more about the inner working of DMT.

To run them, first your system has to be set up accordingly.
DMT is mainly developed on Ubuntu Linux and using Python 3.6.8, but also tested on Windows.
For installation help go to :ref:`install_dmt`.

After you have installed DMT,
place a copy of "DMT_default_config.yaml" in your home directory.
This may be used to provide DMT with local settings.

To run test cases, a  "logs" folder is needed in the DMT/ installation directory.
After these two steps are set up, one can try to run all test cases using::

    pytest test/test_*

This will run all test cases. If errors are encountered at this stage, get in touch with the DMT devs.
If the tests run, you are ready to go!


Here is a small overview of relevant test cases, which may help to make starting with DMT easier.

sweep tests
^^^^^^^^^^^^

To get an idea how bias and temperature sweeps are defined in DMT::

    test_sweep


TCAD tests
^^^^^^^^^^^^

Learn how to use DMT's data management and TCAD interface for the DEVICE TCAD simulator::

    test_elpa
    test_device
    test_dmt_device_interaction
    test_read_DEVICE_internal


Modelcard handling
^^^^^^^^^^^^^^^^^^^^

Learn how to use model cards inside of DMT to manage model parameters::

    test_mcard_class


Circuit Simulator Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the model card class to build a circuit and simulate it using ADS::

    test_dut_ads
    test_dut_ads_many_sweeps


Measurement data handling
^^^^^^^^^^^^^^^^^^^^^^^^^^

Read and preprocess data from measurements::

    test_data_processor
    test_manager_processor_and_plotter


Extraction steps
^^^^^^^^^^^^^^^^

Finally we can start extraction, the test uses Cjei as an example::

    test_xtraction


Extraction GUI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finally we arrive at the GUI for the extraction, this can be seen in::

    test_xtraction_gui
    test_xtract_cjc_temp

