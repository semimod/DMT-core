.. _install_pyqtgraph:

Known PyQtGraph issues
======================

While testing some of our users ran into some pyqtgraph issues. One group was related to the Qt platform plugin "xcb". The error message reads:

.. code-block:: 

    qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.

To resolve that issue some more dependencies have to be installed. On Ubuntu this is:

.. code-block:: bash

    sudo apt-get install -y libxkbcommon-x11-0 x11-utils
    sudo apt-get install --no-install-recommends -y libyaml-dev libegl1-mesa libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xinerama0

More information about this can be cound  `here <https://stackoverflow.com/questions/67067368/pyqtgraph-runtime-error-could-not-load-plugin-xcb>`__.


Using a Docker container
------------------------

A similar error may appear when running DMT inside a Docker container as shown :ref:`here <using_docker>`.

There the solution is to give Docker access to X windows system. The easiest way to acchive that is by disabling the access control:

.. code-block:: bash

    xhost +

before starting the container.