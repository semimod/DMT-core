xyce interface
===================

The interface to the simulator `Xyce <https://xyce.sandia.gov/>`__ is implemented by inheritance of the  :ref:`DutCircuit<dut_circuit>` in the :ref:`DutXyce<dut_Xyce>`.

Installing xyce
------------------

The Xyce installation is more difficult since xyce can be installed in two different ways. One for simple simulations and the second if Verilog-AMS models should be used. For DMT the second variant is more useful, since DMT is focussed on models and hence Verilog-AMS support is quite useful. To make this work, the DMT CI/CD container has ADMS, Trilinos and Xyce build from source with special flags enabled. The full build process is shown here:

.. code-block:: bash

    # adms
    cd /home && curl -L -O https://github.com/Qucs/ADMS/releases/download/release-2.3.7/adms-2.3.7.tar.gz
    cd /home && tar xvfz adms-2.3.7.tar.gz && mkdir ADMS_build && mkdir local
    cd /home/ADMS_build && /home/adms-2.3.7/configure --prefix="/home/local/"
    cd /home/ADMS_build && make install
    PATH="/home/local/bin:${PATH}"

    # trilinos
    cd /home && curl -L -O https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-12-12-1.tar.gz
    cd /home && tar xvfz trilinos-release-12-12-1.tar.gz && mkdir Trilinos_build
    cd /home/Trilinos_build && cmake \
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

    cd /home/Trilinos_build && make && make install

    # xyce
    xyce/Xyce-7.3.tar.gz /home/
    cd /home && tar xzf Xyce-7.3.tar.gz && mkdir Xyce_build
    cd /home/Xyce_build && /home/Xyce-7.3/configure \
        CXXFLAGS="-O3" \
        ARCHDIR="/home/local/" \
        CPPFLAGS="-I/usr/include/suitesparse" \
        --enable-xyce-shareable \
        --enable-shared \
        --enable-stokhos \
        --enable-amesos2 \
        --prefix="/home/local/"

    cd /home/Xyce_build && make && make install

This installs the software tools in the correct versions. For especially the xyce version 7.3 worked best for our needs.

Usually no further configuration for DMT is needed to call xyce. But in case you have a multiple xyce installations or something like this, the correct installation can be chosen in the :ref:`config` with the key:

.. code-block:: yaml

    commands:
        XYCE: Xyce