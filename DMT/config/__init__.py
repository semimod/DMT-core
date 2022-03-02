""" DMT config management

Collects the config from 3 different locations:

* Local script directory. (DMT_config.yaml)
* User's home directory (~/.DMT/DMT_config.yaml)
* DMT package installation directory (DMT_config.yaml)

They are all read and finally taken in the order given here. This means that anything given in the local directory overwrites all others.

"""
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

name = "config"

from pathlib import Path
import yaml
import os

path_config = os.path.dirname(os.path.abspath(__file__))
default_config_file = os.path.join(path_config, "DMT_default_config.yaml")
with open(default_config_file) as yaml_data_file:
    DATA_CONFIG = yaml.safe_load(yaml_data_file)

try:
    user_config = Path.home() / ".DMT" / "DMT_config.yaml"
    # with open(os.path.expanduser(os.path.join('~', '.DMT', 'DMT_config.yaml'))) as yaml_data_file:
    with user_config.open() as yaml_data_file:
        data_user = yaml.safe_load(yaml_data_file)

    for key, value in DATA_CONFIG.items():
        if key in data_user.keys():
            if hasattr(DATA_CONFIG[key], "update"):
                DATA_CONFIG[key].update(data_user[key])
            else:
                if isinstance(DATA_CONFIG[key], list):  # lists are appended.
                    DATA_CONFIG[key] = DATA_CONFIG[key] + data_user[key]
                else:
                    DATA_CONFIG[key] = data_user[key]
except FileNotFoundError:
    pass

try:
    local_config = Path("DMT_config.yaml")
    with local_config.open() as yaml_data_file:
        data_folder = yaml.safe_load(yaml_data_file)

    for key, value in DATA_CONFIG.items():
        if key in data_folder.keys():
            try:
                DATA_CONFIG[key].update(data_folder[key])
            except AttributeError:
                if isinstance(DATA_CONFIG[key], list):  # lists are appended.
                    DATA_CONFIG[key] = DATA_CONFIG[key] + data_folder[key]
                else:
                    DATA_CONFIG[key] = data_folder[key]
except FileNotFoundError:
    pass

USER_NAME = DATA_CONFIG["user_name"]
USER_EMAIL = DATA_CONFIG["user_email"]
""" Name of the DMT user for documentation. """

DIRECTORIES = DATA_CONFIG["directories"]
for key, str_path in DIRECTORIES.items():
    try:
        DIRECTORIES[key] = Path(str_path).expanduser()
    except TypeError:
        pass

DATA_CONFIG["directories"] = DIRECTORIES


DB_DIR = DIRECTORIES["database"]

import pkgutil

# measurement data overview report template
if DATA_CONFIG["directories"]["libautodoc"] is None:
    package = pkgutil.get_loader("DMT.core")
    if package is not None:
        path_libautodoc_default = Path(package.get_filename()).parent.parent / "libautodoc_template"
        DATA_CONFIG["directories"]["libautodoc"] = path_libautodoc_default.expanduser()
else:
    DATA_CONFIG["directories"]["libautodoc"] = Path(
        DATA_CONFIG["directories"]["libautodoc"]
    ).expanduser()

# xtraction result overview report template
if DATA_CONFIG["directories"]["autodoc"] is None:
    package = pkgutil.get_loader("DMT.extraction")
    if package is not None:
        path_autodoc_default = Path(package.get_filename()).parent.parent / "autodoc_template"
        DATA_CONFIG["directories"]["autodoc"] = Path(path_autodoc_default).expanduser()
else:
    DATA_CONFIG["directories"]["autodoc"] = Path(DATA_CONFIG["directories"]["autodoc"]).expanduser()

# not needed anymore. It is directly obtained from DATA_CONFIG.
# This allows to add configs without changing anything here. Do it always like this in future!
COMMANDS = DATA_CONFIG["commands"]

COMMAND_TEX = (DATA_CONFIG["commands"]["TEX"], DATA_CONFIG["commands"]["TEXARGS"])
""" TEX build command """

USE_HDF5STORE = DATA_CONFIG["useHDF5Store"]
""" Saves data as HDF5 Databases, if False, pickle is used. """

# DO NOT ADD ANYTHING HERE. JUST DIRECTLY IMPORT DATA_CONFIG INSIDE YOUR MODULE
# If wanted add documentation here and/or in DMT_config.yaml
