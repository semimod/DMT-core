

.. _install_DMT:

Installation
=============

To use DMT there are two main ways: Docker or install to virtual environment. In this short intro, we will touch both. The two ways have their own advantages and drawbacks:

+------------------------------------------+--------------------------+
| Docker                                   | Virtual environment      |
+==========================================+==========================+
| Easy install                             | Complex install          |
+------------------------------------------+--------------------------+
| Fixed interfaces only                    | Own interfaces           |
+------------------------------------------+--------------------------+
| Exchange of data between host and guest  | No data exchange needed  |
+------------------------------------------+--------------------------+
| No debugging                             | Direct debugging         |
+------------------------------------------+--------------------------+



Of course, for each drawback there is a workaround, but the basic difference stays.

So the recommendation is, if you want to test DMT and see if it suits you, choose docker. But if you want to change the code of DMT or develop more interfaces/modules, then we recommend installing the code in editor mode from your own fork. Somewhere in the middle between these, is the option to install the official pypi release.

Use the docker container
~~~~~~~~~~~~~~~~~~~~~~~~

This is quite straight forward:

.. code:: bash

    docker login registry.gitlab.com

Then the example bash script in `docker/dmt` can be used to execute Python scripts which call DMT. 

Installing container dependencies
---------------------------------

If you want to install more programs or Python packages into this container, we recommend creating your own container. The Dockerfile would start like this:

.. code:: Dockerfile

    FROM registry.gitlab.com/dmt-development/dmt-core:full

    ...

Build and tag this file with your own name. Then change the `docker/dmt` bash script to use the new container accordingly.

Exchange data
-------------

Per default, the bash script mounts the local folder into the container under `/pwd` and hence all data inside the current working path is available there. If you only use local paths (also for the simulation data and reports), the borders between host and guest are transparent. Be aware, that inside the container the user `dmt_user` (id: 1000, group: 1000) is used. So if you have a different id, change the script accordingly. It may look like this (untested):

.. code:: bash

    chmod a+rw -r . # either here
    docker run --rm -ti \
        --env="DISPLAY" \
        --user 1000:1000 \
        --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
        --volume "${PWD}":/pwd \
        --workdir=/pwd \
        registry.gitlab.com/dmt-development/dmt-core:full "python3 $@; chmod a+rw -r ." # or here

Either before or after the run, everyone gets read/write access to the data inside the folder. Depending on your use case, you may restrict the exchange to one direction or special folders. 

If you tested and verified/improved the script, please report this to us!


Install the python package
~~~~~~~~~~~~~~~~~~~~~~~~~~

In this short document, we will explain how to install DMT and many of its dependencies, including how to connect them to DMT.

This tutorial is written for Unix-users. Most of the command-line commands given herein have very similar windows equivalents, and we hope that this tutorial is helpful for both Windows and Unix users. DMT can be run both on Windows and Unix (probably also Mac, but we have not tried that, yet). DMT is implemented and tested using Ubuntu. So if you are free to choose your OS and are looking for an easy start, we can recommend using this.

Before you get started with DMT, please note that DMT is a high-level project (in terms of programming level abstraction), meaning that it has many dependencies. At the end of this page, you may find some installation help for the dependency you want to use. 

Additionally, DMT is still in development and if you use DMT be careful when updating to new versions. We try to keep everything backwards compatible as much as possible and also breaking changes will be denoted by a new master version, but this major version increase may happen earlier than you like.

So before we get started, please:

- Make sure you have Python >= 3.8 installed.
- If run circuit or TCAD simulations, make sure you have one installed on your system which is interfaced by DMT. The Core package offers interfaces to `Hdev <https://gitlab.com/metroid120/hdev_simulator>`__, `Xyce <https://xyce.sandia.gov/>`__ and `ngspice <http://ngspice.sourceforge.net/>`__. If you need a different simulator, either you have to implement it yourself or contact the DMT team for it.
- After every update, ensure that your use cases still run as expected. If you have a special use, which is not covered by our current test-environment feel free to suggest your use case to us via an issue. As we are eager to improve the Code, more test cases are always welcome.


Virtual Environment
-------------------------------

We strongly recommend to run DMT in a virtual python environment.
To install a virtual environment, first go into the DMT project folder

.. code:: bash

    cd $DMT_DIR #replace $DMT_DIR with the DMT project path on your machine

Then, to install a virtual environment:

.. code:: bash

    pip install virtualenv
    virtualenv venv -p python3.10
    source venv/bin/activate

We recommend Python 3.10 since this is what most devs are using at the moment.
You are nearly done! Now you should have activated your new virtual environment.

Install DMT
-----------

To install DMT-core just run in:

.. code:: bash

    python3.10 -m pip install DMT-core[full]

As you can see `DMT-core` offers some installation variants with different dependencies (indicated by the closed brackets). The variants and their additional dependencies are:


+------------+------------------------------+
| Variant    | Extra required packages      |
+============+==============================+
| HDF5       | tables                       |
+------------+------------------------------+
| pyqtgraph  | pyqtgraph                    |
+------------+------------------------------+
| matplotlib | matplotlib                   |
+------------+------------------------------+
| pyside2    | PySide2                      |
+------------+------------------------------+
| pyqt5      | PyQt5                        |
+------------+------------------------------+
| smithplot  | matplotlib, pysmithplot-3.10 |
+------------+------------------------------+
| develop    | pylint, black                |
+------------+------------------------------+
| latex      | pylatex, pylatexenc          |
+------------+------------------------------+
| remote     | paramiko, scp                |
+------------+------------------------------+
| full       | All of above except PyQt5    |
+------------+------------------------------+

It is possible to choose multiple variants at once. We recommend either the full install or at least:

.. code:: bash

    python3.10 -m pip install DMT-core[develop,HDF5,pyqtgraph,pyside2]


If a newer version is needed, the release candidates can be installed from gitlab directly:

.. code:: bash

    python3.10 -m pip install DMT-core==1.5.0rc3 --extra-index-url https://gitlab.com/api/v4/groups/5568716/-/packages/pypi/simple

As DMT is a toolkit which you sometimes want to adjust to your needs, you may want to install it using editor mode. For this, your either have to fork the main project or make a branch in the main repo (after contacting the team). Afterwards run (for example)

.. code:: bash

    git clone git@gitlab.com:dmt-development/dmt-core.git
    git checkout -b your_branch origin/your_branch
    pip install -e .

This enables you to change the DMT source code.

Short test
-----------

To test the installation, open a terminal and enter:

.. code:: bash

    python

Then type:

.. code:: python

    from DMT.core import specifiers
    voltage = specifiers.VOLTAGE + 'B' + 'E'

If this works, you have successfully installed DMT. For more tests visit the test cases in the `repository <https://gitlab.com/dmt-development/dmt-core/-/tree/main/test>`__ and :ref:`the examples <examples>`.


If you want to generate high-quality Tikz plots with DMT, you should also make sure that a Tex compiler such as latexmk and corresponding packages (texlive-full on Unix) are available.
These are not installed when installing DMT.

.. _config:

Configuration
--------------

DMT is a modular, high-level project, that relies heavily on other python packages. Furthermore some DMT modules interface to other (possibly proprietary) software such as ADS.
If you want to use such interfaces, you need:

* the corresponding DMT module
* the other software

Using other software may require DMT to be configured for your user and also for your current working directory. DMT has 3 different configuration file locations: 

* the local config the working directory ``$PWD/DMT_config.yaml``,
* the user config in 
  * ``%LOCALAPPDATA%\DMT\DMT_config.yaml`` on Windows or 
  * ``$XDG_CONFIG_HOME/DMT/DMT_config.yaml`` on Linux and MacOS with ``$XDG_CONFIG_HOME`` defaulting to ``~/.config`` and
* the default config in the DMT installation directory (for example: ``.../venv/lib/python3.10/site-packages/DMT/config/DMT_config.py``)

In this last file you can check for the possible configuration options DMT offers and also copy the file altogether if needed. Each DMT module should additionally contain documentation that explains the relevant configuration options.

For example to use ngspice on a Unix system the command is

.. code:: bash

    ngspice

If this is different on your machine (for example because the `ngspice` callable is not in your path), you should to change this command for your user or workspace config 

.. code:: yaml

    commands:
        NGSPICE:    ngspice # Command to execute the circuit simulator ngspice.


The configuration in the working directory will overwrite the user configuration on the home directory and the default configuration. This can be usefully if you have different projects on the same user, which need different database directories or custom_specifiers.

More installation details
----------------------------

Further installation and configuration guides for DMT are:

.. toctree::
    :glob:
    :maxdepth: 1

    *
