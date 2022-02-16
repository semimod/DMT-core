# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-device>
#
# This file is part of DMT_core.
#
# DMT_core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DMT_core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

# dirty: check which modules available

from importlib import util

core_exists = util.find_spec("DMT.core") is not None
extraction_exists = util.find_spec("DMT.extraction") is not None

# if core_exists and not extraction_exists:
#     mode = "free version"
# elif core_exists and extraction_exists:
#     mode = "all"

print("-----------------------------------------------------------------------")
print("DMT Copyright (C) 2020 Markus Müller, Mario Krattenmacher, Pascal Kuthe")
print("This program comes with ABSOLUTELY NO WARRANTY.")
print("DMT_core is free software, and you are welcome to redistribute it.")
print("DMT_other is free for non-commercial use, see LICENSE.md. ")
print("-----------------------------------------------------------------------")

name = "core"

import numpy as np

# compile cython DMT modules
import pyximport

pyximport.install(setup_args={"include_dirs": np.get_include()}, language_level=3)

import os

from . import constants

# Helper
from .singleton import Singleton
from .hasher import create_md5_hash

# one unit registry for all of DMT
from pint import UnitRegistry

unit_registry = UnitRegistry()
from DMT.config import DATA_CONFIG

from pkg_resources import Requirement, resource_filename

path_core = os.path.dirname(os.path.abspath(__file__))
unit_registry.load_definitions(os.path.join(path_core, "dmt_units.txt"))

# helper for model equations and mcard memoization
from .utils import print_progress_bar
from .utils import check_nan_inf
from .utils import vectorize
from .utils import flatten
from .utils import strictly_increasing
from .utils import enumerate_reversed
from .utils import resolve_siunitx
from .utils import tex_to_text

# naming conventions
from .naming import specifiers
from .naming import sub_specifiers
from .naming import specifiers_ss_para
from .naming import get_specifier_from_string
from .naming import get_nodes
from .naming import set_col_name
from .naming import SpecifierStr
from .naming import get_sub_specifiers
from .naming import natural_scales

# compact modelling stuff
from .mc_parameter import McParameter, McParameterComposition
from .utils import memoize
from .va_file import VAFile
from .mcard import MCard
from .technology import Technology
from .circuit import Circuit, CircuitElement

# plotting
from .plot import Plot
from .plot import SmithPlot
from .plot import save_or_show
from .plot import Plot2YAxis
from .plot import COMPARISON_3

from .tikz_postprocess import TikzPostprocess

# Data management and processing
try:
    from .data_processor_pyx import DataProcessor

    print("Using the pyx data-processor")
except ImportError:
    from .data_processor_py import DataProcessor

    print("Using the py data-processor")

from .data_frame import DataFrame
from .sweep import Sweep, SweepDef
from .database_manager import DatabaseManager
from .data_reader_py import (
    read_data,
    read_ADS_bin,
    read_DEVICE_bin,
    read_elpa,
    read_mdm,
    read_hdf,
    read_feather,
)


# Simulation management
from .sim_con import SimCon
from .df_to_sweep import df_to_sweep

# DutView tree
from .dut_view import DutView
from .dut_type import DutType
from .dut_lib import DutLib

from .dut_meas import DutMeas
from .dut_dummy import DutDummy

from .dut_circuit import DutCircuit

from .dut_tcad import DutTcad

import tables
