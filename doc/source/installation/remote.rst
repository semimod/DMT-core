.. _configure_remote:

Configure DMT for Remote Simulations
====================================

This file describes how to set up DMT for remote simulations.
The server communication is done with ssh, which is natively supported on
unix-based systems.
On windows the installation is more involved.

Linux
---------

The first step is to set up an ssh connection.
If you do not already have a public/private key pair, generate it by running

.. code:: bash

    ssh-keygen -t rsa

The private and public keys are generated in
```/home/user/.ssh/id_rsa``` and ```/home/user/.ssh/id_rsa.pub``` by default.
Now you need to copy the public key onto the server using:

.. code:: bash

    ssh-copy-id -i /home/user/.ssh/id_rsa.pub user@host

You should now be able to login to the server without using a password. Test this by running

.. code:: bash

    ssh user@host

which should now work without you needing to type in a password.

Now you need to set a few values in
your DMT config file. Here is an example from the author of this document:

.. code:: bash

    backend_remote: yes # with yes, the simulations are run on the specified server, per default.
    server:
        adress:     141.30.5.20 # Server IP in the form 0.0.0.0.
        ssh_user:   user # User to log in on the server.
        ssh_key:    ~/.ssh/id_rsa # Path to the ssh key used for the simulations.
        simulation_path: ~/.DMT/simulations/ # Simulation path on the given server. Make sure that this path exists!

Make sure the simulation_path actually exists on the server, it is not created by DMT!

Also you need the python modules "paramiko" and "scp" in order to access the server with DMT.
These can be installed with pip.

Now you can test if everything works by running the DMT test test_server_ads.py, provided your server has ADS simulation
capability.

Windows
----------


TODO
