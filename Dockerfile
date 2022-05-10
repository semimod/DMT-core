FROM archlinux:base-20220501.0.54834

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

