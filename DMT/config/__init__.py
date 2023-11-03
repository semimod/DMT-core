""" DMT config management

Collects the config from 3 different locations:

* Local script directory (DMT_config.yaml).
* User's home directory (%LOCALAPPDATA%\\DMT\\DMT_config.yaml or $XDG_CONFIG_HOME/DMT/DMT_config.yaml with $XDG_CONFIG_HOME defaulting to ~/.config) and
* DMT package installation directory (DMT/config/DMT_config.yaml)

They are all read and finally taken in the order given here. This means that anything given in the local directory overwrites all others.

"""
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

name = "config"

import os
import platform
import pkgutil
import warnings
import yaml
from pathlib import Path
from DMT.external.os import recursive_copy

# dmt default config
path_config = Path(__file__).resolve().parent
default_config_file = path_config / "DMT_config.yaml"
DATA_CONFIG = yaml.safe_load(default_config_file.read_text())

# dmt user config

if platform.system() == "Windows":
    user_config = os.getenv("LOCALAPPDATA")
elif platform.system() == "Linux":
    user_config = os.getenv("XDG_CONFIG_HOME")
elif platform.system() == "Darwin":
    user_config = os.getenv("XDG_CONFIG_HOME")
else:
    raise OSError(
        f"Unknown platform:{platform.system()}. Currently only Windows, Linux and MacOS (Darwin) are recognized"
    )

if user_config:
    user_config = Path(user_config).expanduser() / "DMT" / "DMT_config.yaml"
else:
    user_config = Path.home() / ".config" / "DMT" / "DMT_config.yaml"

data_user = {}
try:
    data_user = yaml.safe_load(user_config.read_text())
except FileNotFoundError:
    try:
        user_config_old = Path.home() / ".DMT" / "DMT_config.yaml"
        data_user = yaml.safe_load(user_config_old.read_text())
        warnings.warn(
            (
                "The DMT user configuration file has been moved. The new paths are:\n"
                + "Windows: %LOCALAPPDATA%\\DMT\\DMT_config.yaml\n"
                + "Linux and MacOS: $XDG_CONFIG_HOME/DMT/DMT_config.yaml\n"
                + "Defaulting to ~/.config/DMT/DMT_config.yaml"
            ),
            category=DeprecationWarning,
        )
    except FileNotFoundError:
        pass

    user_config.parent.mkdir(exist_ok=True, parents=True)
    user_config.write_text(yaml.safe_dump(data_user))

if data_user:
    for key, value in DATA_CONFIG.items():
        if key in data_user.keys():
            if hasattr(DATA_CONFIG[key], "update"):
                DATA_CONFIG[key].update(data_user[key])
            else:
                if isinstance(DATA_CONFIG[key], list):  # lists are appended.
                    DATA_CONFIG[key] = DATA_CONFIG[key] + data_user[key]
                else:
                    DATA_CONFIG[key] = data_user[key]

# finally workspace path
try:
    data_folder = yaml.safe_load(Path("DMT_config.yaml").read_text())

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

for key, str_path in DATA_CONFIG["directories"].items():
    try:
        DATA_CONFIG["directories"][key] = Path(str_path).expanduser().resolve()
    except TypeError:
        pass


# measurement data overview report template
if DATA_CONFIG["directories"]["libautodoc"] is None:
    DATA_CONFIG["directories"]["libautodoc"] = path_config.parent / "libautodoc_template"
else:
    DATA_CONFIG["directories"]["libautodoc"] = (
        Path(DATA_CONFIG["directories"]["libautodoc"]).expanduser().resolve()
    )

# xtraction result overview report template
if DATA_CONFIG["directories"]["autodoc"] is None:
    package = pkgutil.get_loader("DMT.extraction")
    if package is not None:
        path_autodoc_default = (
            Path(package.get_filename()).resolve().parent.parent / "autodoc_template"
        )
        DATA_CONFIG["directories"]["autodoc"] = Path(path_autodoc_default)
else:
    DATA_CONFIG["directories"]["autodoc"] = Path(DATA_CONFIG["directories"]["autodoc"]).expanduser()

# not needed anymore. It is directly obtained from DATA_CONFIG.
# This allows to add configs without changing anything here. Do it always like this in future!
COMMANDS = DATA_CONFIG["commands"]

COMMAND_TEX = (DATA_CONFIG["commands"]["TEX"], DATA_CONFIG["commands"]["TEXARGS"])
""" TEX build command """

# DO NOT ADD ANYTHING HERE. JUST DIRECTLY IMPORT DATA_CONFIG INSIDE YOUR MODULE
# If wanted add documentation here and/or in DMT_config.yaml


def print_config(file_path=None):
    """Prints the current used config either to stdout or into a file

    Parameters
    ----------
    file_path : str, optional
        Path to print the config to, by default None.
    """
    if file_path is None:
        print(DATA_CONFIG)
    else:
        yaml.safe_dump(DATA_CONFIG, file_path)


def generate_libdoc_template(directory):
    """Copies the DMT template for the DutLib documentation into the given directory. This allows to change the template according to your needs.

    Parameters
    ----------
    directory : str
        Path to copy to.
    """
    if isinstance(directory, Path):
        destination = directory
    else:
        destination = Path(directory)

    destination.mkdir(parents=True, exist_ok=True)
    recursive_copy(DATA_CONFIG["directories"]["libautodoc"], destination)


def export_autodoc_template(directory):
    """Copies the DMT template for the extraction documentation into the given directory. This allows to change the template according to your needs.

    Only possible if the extraction module is installed!

    Parameters
    ----------
    directory : str
        Path to copy to.
    """
    if isinstance(directory, Path):
        destination = directory
    else:
        destination = Path(directory)

    destination.mkdir(parents=True, exist_ok=True)
    recursive_copy(DATA_CONFIG["directories"]["autodoc"], destination)
