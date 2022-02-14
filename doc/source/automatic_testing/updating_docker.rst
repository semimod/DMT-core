Updating the Docker image on gitlab.com
=======================================

When a dependency of DMT changes, the Docker image used to run the DMT test cases
needs to be re-built as-well.
This is a short explanation how to update the docker image.

For details, see the `gitlab Container Registry <https://gitlab.com/help/user/packages/container_registry/index>`.

Docker generals
-----------------

First, you need to set-up Docker on your local machine.

In Debian this can be done by:

.. code-block:: bash

  sudo apt install docker.io

Also make sure that your user is added to the docker group (`see here for more info <https://www.configserverfirewall.com/ubuntu-linux/add-user-to-docker-group-ubuntu/>`):
The docker installation can be tested by:

.. code-block:: bash

  docker run hello-world

Download Current Image
----------------------------------------

In the first step we login into the correct registry:

.. code-block:: bash

  docker login registry.gitlab.com

Then we can get the existing docker image:

.. code-block:: bash

  docker pull registry.gitlab.com/dmt-development/dmt

Prepare the image
----------------------------------------

The DMT test image Dockerfile is placed right next to this file. Change it according to the new dependencies (if possible just append the new dependencies at the bottom, this makes building and uploading faster). Then build the image for the registry:

.. code-block:: bash

  docker build -t registry.gitlab.com/dmt-development/dmt .

Upload the image
----------------------------------------


And finally push the image to the server:

.. code-block:: bash

  docker push registry.gitlab.com/dmt-development/dmt

That's it. Now the next test run is done with the new image.
