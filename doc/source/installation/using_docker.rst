.. _using_docker:

Using Docker
============

It is possible to run DMT inside a docker container. Currently we do not offer an "official" DMT container, as we are busy bringing our dependcies up to better standards, in order to reduce depency issues.

Anyways, thankfully Dilwar provided one `<https://gitlab.com/dilawar/dmt-core/-/blob/joss/Dockerfile>`__. 

The essence is

.. code-block:: Dockerfile

    FROM archlinux:base-20220501.0.54834

    RUN groupadd -r ${APP_USER} && useradd --no-log-init -r -m -g ${APP_USER} ${APP_USER}

    RUN pacman -Syyu --noconfirm

    RUN pacman -S --noconfirm --needed cmake pkgconfig git python-pip python sudo base-devel \
        freetype2 libglvnd \
        python-setuptools python-wheel \
        python-pandas \
        python-pytables \
        python-matplotlib python-pint \
        python-pyqtgraph bc \
        && yes | pacman -Scc

    RUN pacman -S --noconfirm --needed ngspice && yes | pacman -Scc
    RUN pacman -S --noconfirm --needed texlive-most && yes | pacman -Scc

    COPY . /dmt

    RUN cd /dmt && pip install .[full]


For this help, the sadly not fully working Xyce simulator is removed. ngspice is installed and works great, so circuit simulations are easily possible.

To run this container in the local DMT folder use:

.. code-block:: bash

    docker build -t dmt:latest .
    docker run -it -u $(id -u):$(id -g) -e DISPLAY=$DISPLAY -w /dmt -v /tmp/.X11-unix:/tmp/.X11-unix dmt:latest python RELATIV_PATH_TO_FILE_TO_RUN.py

