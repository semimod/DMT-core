hdev interface
===================

The interface to the simulator `Hdev <https://gitlab.com/metroid120/hdev_simulator>`__ is implemented by inheritance of the  :ref:`DutTcad<dut_tcad>` in the :ref:`DutXyce<dut_hdev>`.

Installing hdev
------------------

The hdev installation for the DMT CI/CD is placed inside the test suite itself, since we expect more changes for the simulator but as the simulator uses DMT for its own test suite, the interface is ensured to be working properly. The installation has two steps, first the python interface of Hdev, ``HdevPy``, is installed in editor mode and second the executable is downloaded from the artifacts of the latest CI run from hdev:

.. code-block:: bash

    # Hdev:
    git clone https://gitlab.com/metroid120/hdev_simulator.git
    cd hdev_simulator/HdevPy #HdevPy depends on DMT_core and therefore is installed here
    pip install -e .
    cd ..
    # download the executable and put it into path
    wget "https://gitlab.com/metroid120/hdev_simulator/-/jobs/artifacts/master/raw/builddir_docker/hdev?job=build:linux" -O hdev
    chmod +x hdev
    export PATH=$PATH:$(pwd)

Usually no further configuration for DMT is needed to use Hdev. But in case you have multiple hdev installations or something like this, the correct installation can be chosen in the :ref:`config` with the key:

.. code-block:: yaml

    commands:
        Hdev: hdev