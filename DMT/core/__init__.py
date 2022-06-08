# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-core>
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

from pint import UnitRegistry
from pathlib import Path

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

__version__ = VersionInfo(major=1, minor=6, patch=1, prerelease="rc.2")
# to get the next version:
# __version__.next_version(x) - with x = "major", "minor", "patch", "prerelease"

name = "core"


from . import constants

# Helper
from .singleton import Singleton
from .hasher import create_md5_hash

# one unit registry for all of DMT

unit_registry = UnitRegistry()
from DMT.config import DATA_CONFIG


path_core = Path(__file__).resolve().parent
unit_registry.load_definitions(str(path_core / "dmt_units.txt"))

# helper for model equations and mcard memoization
from .utils import print_progress_bar
from .utils import enumerate_reversed

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
from .mc_parameter import McParameter, McParameterCollection, McParameterComposition
from .va_file import VAFile
from .mcard import MCard
from .technology import Technology
from .circuit import Circuit, CircuitElement

# plotting
from .plot import Plot
from .plot import save_or_show
from .plot import COMPARISON_3
from .plot_smith import SmithPlot
from .plot_2yaxis import Plot2YAxis

# Data management and processing
from .data_processor import is_iterable, flatten, strictly_increasing, DataProcessor

from .data_frame import DataFrame
from .sweep import Sweep, SweepDef, get_sweepdef
from .database_manager import DatabaseManager
from .data_reader import (
    read_data,
    save_elpa,
    read_ADS_bin,
    read_DEVICE_bin,
    read_elpa,
    read_mdm,
    read_hdf,
    read_feather,
)


# Simulation management
from .sim_con import SimCon

# DutView tree
from .dut_view import DutView
from .dut_type import DutType
from .dut_lib import DutLib

from .dut_meas import DutMeas
from .dut_dummy import DutDummy

from .dut_circuit import DutCircuit

from .dut_tcad import DutTcad

# docu
from .docu_dut_lib import DocuDutLib

# determine which modules are present
core_exists = True  # always, without DMT is not possible
try:
    import DMT.extraction

    extraction_exists = True
except ImportError:
    extraction_exists = False


if core_exists and not extraction_exists:
    mode = "free version"
elif core_exists and extraction_exists:
    mode = "all"

print("-----------------------------------------------------------------------")
print("DMT Copyright (C) 2022 SemiMod")
print("This program comes with ABSOLUTELY NO WARRANTY.")
print("DMT_core is free software, and you are welcome to redistribute it.")
if extraction_exists:
    print("DMT_other is free for non-commercial use, see LICENSE.md. ")
print("-----------------------------------------------------------------------")
