

.. _install_DMT:

Installation
=============

In this short document, we will explain how to install DMT and many of its dependencies, including how to connect them to DMT.

This tutorial is written for Unix-users. Most of the command-line commands given herein have very similar windows equivalents and we hope that this tutorial is helpful for both Windows aswell as Unix users. DMT can be run both on Windows and Unix (probably also Mac, but we have not tried that, yet).

Before you get started with DMT, please note that DMT is a high-level project (in terms of programming level abstraction), meaning that it has many dependencies. Additionally, DMT is still in development and if you use DMT be careful when updating to new versions. We try to keep everything backwards compatible as much as possible and also breaking changes will be denoted by a new master version, but this major version increase may happen earlier than you like.

So before we get started, please:

- Make sure you have Python >= 3.8 installed.
- If run circuit or TCAD simulations, make sure you have one installed on your system which is interfaced by DMT. The Core package offers `Hdev <https://gitlab.com/metroid120/hdev_simulator>`__, `Xyce <https://xyce.sandia.gov/>`__ and `ngspice <http://ngspice.sourceforge.net/>`__. If you need a different simulator, either you have to implement it yourself or contact the DMT team for it.
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

    python3.10 -m pip install DMT-core --extra-index-url https://__token__:<personal_access_token>@gitlab.com/api/v4/groups/5568716/-/packages/pypi/simple

To run this you must register your `personal access token at gitlab <https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html>`__. This installs DMT-core to be used by your project.

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

Configuration
--------------

DMT is a modular, high-level project, that relies heavily on other python packages.
Furthermore some DMT modules interface to other (possibly proprietary) software such as ADS.
If you want to use such interfaces, you need:

* the corresponding DMT module
* the other software

Using other software may require DMT to be configured for your user and also for your current
working directory.
The default config file is placed inside the DMT python package (DMT/DMT_default_config.py) and can be
copied manually to your ~/.DMT (for Linux) or C:\Users\<CurrentUserName>\.DMT for windows when installing DMT. In this file you also can check for most of the possible configuration options DMT offers.
Each DMT module should contain documentation that explains the relevant configuration options.

In example to use ADS on a Unix system one needs to type

.. code:: bash

    hpeesofsim

into the console. This command may be different and needs to be known to DMT.
If you want to change this command for your user change in ~/.DMT/DMT_config.yaml

.. code:: yaml

    commands:
        ADS:        hpeesofsim_user # Command to execute the circuit simulator of ADS.


This changes the default bash command to start the software.

Additionally you can add a DMT configuration file "DMT_config.yaml" into your working directory.
The configuration in the working directory will overwrite the user configuration on the home directory and the default configuration.
This can be usefully if you have different projects on the same user, which need different database directories or custom_specifiers.

DMT always tries to load:

* the default config in the DMT installation directory
* the user config in $home/.DMT/DMT_config.yaml
* the local config the working directory

the default config is overwritten by the user config, which is in turn overwritten by the local config.

More installation details
----------------------------

Further installation and configuration guides for DMT are:

.. toctree::
    :glob:
    :maxdepth: 1

    *
