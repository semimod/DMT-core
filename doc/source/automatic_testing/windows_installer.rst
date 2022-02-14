Generating the windows installer
=================================

Prerequisites
-------------

- Innosetup_
- 7zip_
- A copy of the dmt installer archive

The windows installer provided with dmt is a simple `portable python installation`_ customized for DMT, with dmt preinstalled
and some tweaks to allow ``dmt_batched`` be called from the console anywhere.

To generate the installer you simply need to extract the installer archive to a directory.
In that directory there should now be directory named ``WPy64-3870`` and 3 files (``7zr.exe``, ``DMT_Logo.ico``, ``installer.iss``).

Start the `WinPython Powershell Prompt.exe` file in the ``WPy64-3870`` directory.
This will open a power shell with the python interpreter preloaded.
Now change into some arbitrary directory (not inside the WPy64-3870 directory) and git clone dmt.
Change directory into the DMT folder and run the following commands:

.. code-block:: bash

    pip install ./DMT_core_pkg --force
    pip install ./DMT_other[vae_models, batch_mode] --force

After the commands complete DMT has been installed inside the portable installation.
Finally open the folder into which the installer was extracted and right click the ``WPy64-3870`` folder.
Select 7zip and the create an archive.
You should select a fairly low compression ratio, because the installation will be slow otherwise.
Rename the resulting archive to ``winpython.7z``

Finally open ``installer.iss`` with innosetup (if installed correctly simply double click) and click compile.
After the compilation finishes (should be quick) the resulting file can be found in the ``Output`` directory.


.. _`portable python installation`: https://winpython.github.io/
.. _`winpython`:  https://winpython.github.io/
.. _Innosetup: https://jrsoftware.org/isdl.php
.. _7zip: https://www.7-zip.org/