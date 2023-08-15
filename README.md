# DMT-core

[![pyversion](https://img.shields.io/pypi/pyversions/DMT-core)](https://pypi.org/project/DMT-core/)
[![Build Status](https://gitlab.com/dmt-development/dmt-core/badges/main/pipeline.svg)](https://gitlab.com/dmt-development/dmt-core/-/pipelines)
[![Coverage](https://gitlab.com/dmt-development/dmt-core/-/jobs/artifacts/main/raw/badge_coverage.svg?job=test_DMT)](https://gitlab.com/dmt-development/dmt-core/-/jobs/artifacts/main/file/htmlcov/index.html?job=test_DMT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![status](https://joss.theoj.org/papers/f9829bb4e4c10b85144b22f888756045/status.svg)](https://joss.theoj.org/papers/f9829bb4e4c10b85144b22f888756045)

[![logo](https://gitlab.com/uploads/-/system/project/avatar/33580822/DMT_Logo_wText.png)](https://gitlab.com/uploads/-/system/project/avatar/33580822/DMT_Logo_wText.png)

DeviceModelingToolkit (DMT) is a Python tool targeted at helping modeling engineers extract model parameters, run circuit and TCAD simulations and automate their infrastructure.

See the [DMT-website](https://dmt-development.gitlab.io/dmt-core/index.html) for further information.

This project is funded by [Nlnet](https://nlnet.nl/project/DMT-Core/) under the [NGI Zero Entrust fund](https://nlnet.nl/entrust/).

<img src="pictures/banner_nlnet.svg" width="325"/>

## Usage

### Installation to virtual environment

After installing python 3.8 or later, create a virtual environment and install the release version using

```bash

    python3 -m pip install DMT-core[full]

```

For more information have a look at our [installation guide](https://dmt-development.gitlab.io/dmt-core/installation/install_dmt.html)

Currently, DMT is developed mostly on Ubuntu using Python 3.10. So for the easiest install this is the best supported platform.
If you want or have to use Windows and MacOS there may be more dependency and installation issues, although needed projects we use support these platforms. Please report these issues to us. In our installation guide, we collect guides to solve the already known issues.

### Full docker container

DMT is tested inside a docker container and this container can be used to run python/DMT scripts locally on your machine. See `docker/dmt` for an example bash script to run a file. Notice the configuration, this is needed so that simulation results and read measurement files persist on your host machine and do not vanish each time the container is closed. 

For more information have a look at our [docker guide](https://dmt-development.gitlab.io/dmt-core/installation/install_dmt.html)

## Questions, bugs and feature requests

If you have any questions or issues regarding DMT, we kindly ask you to contact us. Either mail us directly or open an issue [here](https://gitlab.com/dmt-development/dmt-core/-/issues). There we have prepared [several templates](https://docs.gitlab.com/ee/user/project/description_templates.html#use-the-templates) for the description:

* [Questions](https://gitlab.com/dmt-development/dmt-core/-/issues/new?issuable_template=question)
* [Bug reports](https://gitlab.com/dmt-development/dmt-core/-/issues/new?issuable_template=bug_report)
* [Feature requests](https://gitlab.com/dmt-development/dmt-core/-/issues/new?issuable_template=feature_request)

## Authors

- M. Müller | Markus.Mueller@semimod.de
- M. Krattenmacher | Mario.Krattenmacher@semimod.de
- P. Kuthe | jarodkuthe@protonmail.com

### Contributing

More contributors and merge-requests are always welcome. When contributing to this repository, please first discuss the change you wish to make via issue, email, or any other method with the owners of this repository before making a change.

Contact Markus or Mario, if you are interested to join the team permanently.

### Pull Request Process

If you want to supply a new feature, you have implemented in your fork, to DMT, we are looking forward to your [merge request](https://gitlab.com/dmt-development/dmt-core/-/merge_requests/new). There we have a template for the merge request, including a checklist of suggested steps.

The steps are:

1. Implement the new feature
2. Add test cases for the new feature with a large coverage
3. Add new python dependencies to `setup.py`
4. If a interface is used, add a Dockerfile in which the interfaced software is installed and run the tests inside this Dockerfile
5. Add additional documentation to the new features you implemented in the code and the documentation.
6. Format the code using `black`
7. Update the CHANGELOG with your changes and increase the version numbers in the changed files to the new version that this Pull Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).


## License

This project is licensed under GLP-v3-or-later
