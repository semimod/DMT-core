FROM python:3.10.2-buster as BUILD_DEPS

# python installation
RUN apt-get update && apt-get -y install bc bison flex libxaw7 libxaw7-dev libx11-6 libx11-dev libreadline7 libxmu6
RUN apt-get update && apt-get -y install build-essential libtool gperf libxml2 libxml2-dev libxml-libxml-perl libgd-perl
RUN apt-get update && apt-get -y install g++ gfortran make cmake libfl-dev libfftw3-dev libsuitesparse-dev libblas-dev liblapack-dev git

# add ngspice to test DutNGSpice
RUN wget -O /home/ngspice.tar.gz https://sourceforge.net/projects/ngspice/files/ng-spice-rework/37/ngspice-37.tar.gz/download
RUN cd /home && tar -xf ngspice.tar.gz
RUN cd /home/ngspice-37 && chmod a+rwx compile_linux.sh && ./compile_linux.sh --disable-debug

# add Xyce to test DutXyce

# adms
RUN cd /home && curl -L -O https://github.com/Qucs/ADMS/releases/download/release-2.3.7/adms-2.3.7.tar.gz
RUN cd /home && tar xvfz adms-2.3.7.tar.gz && mkdir ADMS_build && mkdir local
RUN cd /home/ADMS_build && /home/adms-2.3.7/configure --prefix="/home/local/"
RUN cd /home/ADMS_build && make install
ENV PATH="/home/local/bin:${PATH}"

# trilinos
RUN cd /home && curl -L -O https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-12-12-1.tar.gz
RUN cd /home && tar xvfz trilinos-release-12-12-1.tar.gz && mkdir Trilinos_build
RUN cd /home/Trilinos_build && cmake \
    -G "Unix Makefiles" \
    -DCMAKE_C_COMPILER=gcc \
    -DCMAKE_CXX_COMPILER=g++ \
    -DCMAKE_Fortran_COMPILER=gfortran \
    -DCMAKE_CXX_FLAGS="-O3 -fPIC" \
    -DCMAKE_C_FLAGS="-O3 -fPIC" \
    -DCMAKE_Fortran_FLAGS="-O3 -fPIC" \
    -DCMAKE_INSTALL_PREFIX="/home/local/" \
    -DCMAKE_MAKE_PROGRAM="make" \
    -DTrilinos_ENABLE_NOX=ON \
    -DNOX_ENABLE_LOCA=ON \
    -DTrilinos_ENABLE_EpetraExt=ON \
    -DEpetraExt_BUILD_BTF=ON \
    -DEpetraExt_BUILD_EXPERIMENTAL=ON \
    -DEpetraExt_BUILD_GRAPH_REORDERINGS=ON \
    -DTrilinos_ENABLE_TrilinosCouplings=ON \
    -DTrilinos_ENABLE_Ifpack=ON \
    -DTrilinos_ENABLE_AztecOO=ON \
    -DTrilinos_ENABLE_Belos=ON \
    -DTrilinos_ENABLE_Teuchos=ON \
    -DTeuchos_ENABLE_COMPLEX=ON \
    -DTrilinos_ENABLE_Amesos=ON \
    -DAmesos_ENABLE_KLU=ON \
    -DTrilinos_ENABLE_Amesos2=ON \
    -DAmesos2_ENABLE_KLU2=ON \
    -DAmesos2_ENABLE_Basker=ON \
    -DTrilinos_ENABLE_Sacado=ON \
    -DTrilinos_ENABLE_Stokhos=ON \
    -DTrilinos_ENABLE_Kokkos=ON \
    -DTrilinos_ENABLE_ALL_OPTIONAL_PACKAGES=OFF \
    -DTrilinos_ENABLE_CXX11=ON \
    -DTPL_ENABLE_AMD=ON \
    -DAMD_LIBRARY_DIRS="/usr/lib64" \
    -DTPL_AMD_INCLUDE_DIRS="/usr/include/suitesparse" \
    -DTPL_ENABLE_BLAS=ON \
    -DTPL_ENABLE_LAPACK=ON \
    "/home/Trilinos-trilinos-release-12-12-1"

RUN cd /home/Trilinos_build && make && make install

# xyce
RUN cd /home && curl -L -O https://xyce.sandia.gov/files/xyce/Xyce-7.5.tar.gz
RUN cd /home && tar xzf Xyce-7.5.tar.gz && mkdir Xyce_build
RUN cd /home/Xyce_build && /home/Xyce-7.5/configure \
    CXXFLAGS="-O3" \
    ARCHDIR="/home/local/" \
    CPPFLAGS="-I/usr/include/suitesparse" \
    --enable-xyce-shareable \
    --enable-shared \
    --enable-stokhos \
    --enable-amesos2 \
    --prefix="/home/local/"

RUN cd /home/Xyce_build && make && make install

FROM python:3.10.2-buster
# ngspice binary
COPY --from=BUILD_DEPS /usr/local/bin/ngspice /usr/local/bin/ngspice
# ngspice libraray
COPY --from=BUILD_DEPS /usr/local/lib/ngspice /usr/local/lib/ngspice
# ADMS, trilinos and Xyce
COPY --from=BUILD_DEPS /home/local /home/local
ENV PATH="/home/local/bin:${PATH}"
# runtime dependencies
RUN apt-get update && apt-get -y install libfftw3-dev libsuitesparse-dev libblas-dev liblapack-dev
RUN apt-get update && apt-get -y install libxaw7 libxaw7-dev libx11-6 libx11-dev libreadline7 libxmu6
# RUN apt-get update && apt-get -y install bison flex
# RUN apt-get update && apt-get -y install libxml2 libxml2-dev libxml-libxml-perl libgd-perl
# RUN apt-get update && apt-get -y install libfl-dev

# testing
RUN admsXml --version
RUN Xyce -v
RUN ngspice -v

RUN apt-get update && apt-get -y install python3-dev graphviz cmake vim bc libsz2
RUN pip install --upgrade pip
RUN pip install virtualenv
RUN virtualenv venv
RUN . venv/bin/activate && pip install setuptools scipy numpy scikit-rf reprint pandas h5py tables cython sphinx_rtd_theme pylint pylatex pylatexenc pint pytest pytest-cov sphinx numpydoc pypandoc anybadge
RUN . venv/bin/activate && pip install numba pyqtgraph matplotlib PySide2 cycler pyyaml joblib more_itertools paramiko scp colormath semver black
RUN . venv/bin/activate && pip install git+https://github.com/SuperKogito/sphinxcontrib-pdfembed
RUN . venv/bin/activate && pip install python-levenshtein fuzzywuzzy verilogae twine

# runtime version of Hdev
RUN git clone https://gitlab.com/metroid120/hdev_simulator.git && cd hdev_simulator/HdevPy && pip install -e .
RUN cd /home/local/bin && wget "https://gitlab.com/metroid120/hdev_simulator/-/jobs/artifacts/master/raw/builddir_docker/hdev?job=build:linux" -O hdev && chmod +x hdev
# installed version of pip
COPY . /dmt/
RUN . venv/bin/activate && cd /dmt && pip install -e .[full]

# apply read-write rights to some files inside the container for everyone 
RUN chmod --recursive a+rw /dmt 
RUN chmod --recursive a+rw /venv 
RUN chmod --recursive a+rw /home/local/bin 
# more Python dependencies add on bottom to not disturb the build chain
