import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="DMT_core",
    version="1.3.0-rc.2",  # obtain by start DMT.core.__init__.py interactive and grab the next version
    author="M.Mueller, M.Krattenmacher",
    author_email="markus.mueller@semimod.de and mario.krattenmacher@semimod.de",
    description="Device Modeling Toolkit Core",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/dmt-development/dmt",
    project_urls={
        "Bug Tracker": "https://gitlab.com/dmt-development/dmt",
        "Documentation": "https://dmt-development.gitlab.io/dmt-core/",
        "Source Code": "https://gitlab.com/dmt-development/dmt",
    },
    packages=setuptools.find_namespace_packages(include=["DMT.*"]),
    license="GNU GPLv3+",
    classifiers=["Programming Language :: Python :: 3.8", "Operating System :: OS Independent"],
    package_data={"": ["*.yaml", "*.txt"]},
    include_package_data=True,
    install_requires=[
        "scipy",
        "numpy",
        "scikit-rf",
        "reprint",
        "pandas",
        "numba",
        "h5py",
        "tables",
        "joblib",
        "pyqtgraph",
        "matplotlib",
        "pylint",
        "pytest",
        "pylatex",
        "pylatexenc",
        "pint",
        "pyyaml",
        "pypandoc",
        "more_itertools",
        "paramiko",
        "scp",
        "colormath",
        "semver",
        "verilogae>=0.9b4",
    ],
)
