FROM ubuntu:22.04 as BUILDER

# python installation
RUN apt-get update \
    && apt-get -y install \
    wget bc bison flex libxaw7 libxaw7-dev libx11-6 libx11-dev libreadline8 libxmu6 build-essential libtool gperf libxml2 libxml2-dev libxml-libxml-perl libgd-perl g++ gfortran make cmake libfl-dev libfftw3-dev libsuitesparse-dev libblas-dev liblapack-dev git

RUN apt-get update \
    && apt-get -y install \
    libreadline-dev

# add ngspice to test DutNGSpice
RUN cd /home \
    && wget -O ngspice.tar.gz https://sourceforge.net/projects/ngspice/files/ng-spice-rework/37/ngspice-37.tar.gz/download \
    && tar -xf ngspice.tar.gz \
    && cd ngspice-37 \
    && chmod +rwx compile_linux.sh \
    && ./compile_linux.sh --disable-debug

# add Xyce to test DutXyce

RUN apt-get update \
    && apt-get -y install \
    curl

# adms
RUN cd /home \
    && curl -L -O https://github.com/Qucs/ADMS/releases/download/release-2.3.7/adms-2.3.7.tar.gz \
    && tar xvfz adms-2.3.7.tar.gz \
    && mkdir ADMS_build \
    && mkdir local \
    && cd ADMS_build \
    && /home/adms-2.3.7/configure --prefix="/home/local/" \
    && make -j8 install

ENV PATH="/home/local/bin:${PATH}"

# trilinos
RUN cd /home \
    && curl -L -O https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-12-12-1.tar.gz \
    && tar xvfz trilinos-release-12-12-1.tar.gz \
    && mkdir Trilinos_build \
    && cd /home/Trilinos_build \
    && cmake \
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

RUN cd /home/Trilinos_build && make -j8 && make install

# xyce
RUN cd /home \
    && curl -L -O https://xyce.sandia.gov/files/xyce/Xyce-7.5.tar.gz \
    && tar xzf Xyce-7.5.tar.gz \
    && mkdir Xyce_build \
    && cd Xyce_build \
    && /home/Xyce-7.5/configure \
    CXXFLAGS="-O3" \
    ARCHDIR="/home/local/" \
    CPPFLAGS="-I/usr/include/suitesparse" \
    --enable-xyce-shareable \
    --enable-shared \
    --enable-stokhos \
    --enable-amesos2 \
    --prefix="/home/local/"

RUN cd /home/Xyce_build && make -j8 && make install
