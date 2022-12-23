CI/CD File
==================================================

This page explains the Gitlab CI/CD file, which automatically runs a number of
test-cases and generates the documentation when a new commit is added to the DMT master or pre-master branch.

For the full how-to check the documentation of `gitlab <https://docs.gitlab.com/ee/ci/index.html>`__.


Explanation to the automatic test and result generation
----------------------------------------------------------

Next, the yaml-File .gitlab-ci.yml is briefly explained. The first lines

.. code-block:: yaml

  #
  image: registry.gitlab.com/dmt-development/dmt:latest

  # ... configs

  before_script:
  - ... # bash commands

specify the Docker image to be used for testing. This image needs to be available on Docker-hub and is built manually
whenever a dependency of DMT changes. The first step is then to install DMT into this Docker image.

In the next step, the core module is tested

.. code-block:: yaml

  run_core:
    stage: build
    script:
      - ... # bash commands
    only:
      - main

GitLab has the stages `build`, `test` and `deploy`, which are run one after another.
The last stage is used to generate the coverage report and the documentation:

.. code-block:: yaml

  coverage:
    stage: deploy
    script:
      - ... # bash commands
    after_script:
      - ... # bash commands
    artifacts:
      paths:
        - coverage_report.txt
        - htmlcov
        - badge_coverage.svg
    only:
      - master

  pages:
    stage: deploy
    script:
      - ... # bash commands
    artifacts:
          paths:
            - public
    only:
      - master

The artifacts that are generated in this step can be download from `pipelines <https://gitlab.com/dmt-development/dmt-core/pipelines>`__.

Automatic Testing
----------------------------------------------------------

To run all test cases in a folder the following command needs to be executed in the file .gitlab-ci.yml

.. code-block:: bash

  pytest test/test_X/

, where X refers to one of the test folders in the test/ directory.


Generating coverage reports
----------------------------------------------------------

During testing the coverage report can be created on the local machine to save time.
For this one needs to call pytest with activated coverage module.
This package is no requirement of DMT, but can be installed by running:

.. code-block:: bash

  pip3 install pytest-cov

The coverage report is basically generated using the command

.. code-block:: bash

  pytest --cov=DMT/ test/test_core_no_interfaces/

`--cov=DMT/core/` activates the coverage plug-in of pytest and sets the path to cover,
this limits the report to the files in the specified directory.
If multiple directories should be included in the test, the cov argument can be repeated:

.. code-block:: bash

  pytest --cov=DMT/ --cov-append test/test_interface_ngspice/test_*.py

Additionally `--cov-append` is used to append the new results to the already existing ones.
This is done the same way for the ngspice module and then finally while testing xyce,
additionally 2 reports are generated:

.. code-block:: bash

  pytest --cov-report term-missing --cov-report html --cov=DMT/ --cov-append test/test_interface_xyce/test_*.py | tee coverage_report.txt


  * On one hand, the regular output is appended by the untested lines (`--cov-report term-missing`) and saved into `coverage_report.txt`.
  * On the over hand, `--cov-report html` creates the `htmlcov` folder and an nice looking html report, where all the separet files can be parsed and visually checked.

After the script, the yaml file defines how the badge for the readme is generated. This is done by the python module `anybadge` and using a regular expression matching into the `coverage_report` to grab the total covered percentage.


Running the test suite locally
------------------------------

The test container can be run locally using gitlab-runner. This is substantially faster and can also be used on non-CI/CD branches.

.. code-block:: bash

  gitlab-runner exec docker <test_stage>

This will download the correct docker container and execute the tests inside the container as it would do on the gitlab.com server.
