ngspice interface
===================

The interface to the simulator `ngspice <http://ngspice.sourceforge.net/>`__ is implemented by inheritance of the  :ref:`DutCircuit<dut_circuit>` in the :ref:`DutNgspice<dut_ngspice>`.

Installing ngspice
------------------

Ngspice can be installed directly from the project homepage. The DMT CI/CD pipeline uses version 36 on linux. The installation is done using the following lines:

.. code-block:: bash

    wget -O /home/ngspice.tar.gz https://sourceforge.net/projects/ngspice/files/ng-spice-rework/36/ngspice-36.tar.gz/download
    cd /home && tar -xf ngspice.tar.gz
    cd /home/ngspice-36 && chmod a+rwx compile_linux.sh && ./compile_linux.sh --disable-debug

This installs ngspice to ``/usr/local/bin/ngspice``. Usually this is already part of the environment path. Usually no further configuration for DMT is needed to call ngspice. But in case you have a multiple ngspice installations or something like this, the correct installation can be chosen in the :ref:`config` with the key:

.. code-block:: yaml

    commands:
        NGSPICE: ngspice