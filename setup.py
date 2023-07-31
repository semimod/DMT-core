import setuptools
from itertools import chain

with open("README.md", "r") as fh:
    long_description = fh.read()

EXTRAS_REQUIRE = {
    "HDF5": ["tables"],
    "pyqtgraph": ["pyqtgraph"],
    "matplotlib": ["matplotlib"],
    "pyside2": ["PySide2"],
    "pyside6": ["PySide6"],
    "pyqt5": ["PyQt5"],
    "smithplot": ["matplotlib", "pysmithplot-3.10"],
    "develop": ["pylint", "black"],
    "latex": ["pylatex", "pylatexenc"],
    "remote": ["paramiko", "scp"],
}
EXTRAS_REQUIRE["full"] = list(set(chain(*EXTRAS_REQUIRE.values())))
EXTRAS_REQUIRE["full"].remove("PyQt5")  # not always needed

setuptools.setup(
    name="DMT_core",
    version="9.9.9",
    author="M.Mueller, M.Krattenmacher",
    author_email="markus.mueller@semimod.de, mario.krattenmacher@semimod.de",
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
    classifiers=[
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
    package_data={"": ["*.yaml", "*.txt", "*.tex", "*.bib"]},
    include_package_data=True,
    install_requires=[
        "scipy",
        "numpy",
        "scikit-rf",
        "reprint",
        "pandas",
        "pyarrow",
        "joblib",
        "pytest",
        "pint",
        "pyyaml",
        "more_itertools",
        "semver",
        "verilogae>=0.9b4",
        "h5py",
        "cycler",
        "colormath",
        "requests",
    ],
    extras_require=EXTRAS_REQUIRE,
)
