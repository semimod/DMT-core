.. _install_mac:

Known Mac issues
================

Although Mac is not used by one of the developers currently, some bugs have been reported. They will be collected here.

M1 mac
------

HDF5: There seem to be issues regarding the installation of HDF5 using the M1 mac. It can be solved by installing HDF5 using homebrew first

.. code:: bash

    brew install hdf5


and then adding the following line to the ~/.zshrc file to set the environment variable :

.. code:: bash

   export HDF5_DIR="/opt/homebrew/opt/hdf5"

More details can be found `here <https://github.com/PyTables/PyTables/issues/832>`__ and `here <https://stackoverflow.com/questions/65839750/installing-python-tables-on-mac-with-m1-chip>`__