""" OS interaction of DMT
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
import os
import shutil
import re
from pathlib import Path

##MARKUS CONTEXT MANAGER AWESOMENESS ###############
# this is a cd command that support context_manager python commands.


class cd:
    """Context manager for changing the current working directory

    Usage::

        with cd(dir):
            pass

    """

    def __init__(self, newPath):
        self.savedPath = ""
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def recursive_copy(src, dst, force=False):
    """Recursively copies a full directory to a new destination folder.

    Parameters
    ----------
    src : str or os.Pathlike
        Path to the source folder
    dst : str or os.Pathlike
        Path to the destination folder
    force : bool, optional
        When true, all files are overwritten. Else, already existing ones are kept.
    """
    if not isinstance(src, Path):
        src = Path(src)
    if not isinstance(dst, Path):
        dst = Path(dst)
    for item_src in src.iterdir():
        item_dst = dst / item_src.name
        if item_src.is_file():
            if not item_dst.exists() or force:
                shutil.copy(item_src, dst)

        elif item_src.is_dir():
            item_dst.mkdir(exist_ok=True)
            recursive_copy(item_src, item_dst)
        else:
            raise ValueError("DMT->recursive_copy: I do not know this filettype.")


def rmtree(root):
    """rmtree method for Path objects

    Parameters
    ----------
    root : str or os.Pathlike
        Directory to remove
    """
    if not isinstance(root, Path):
        root = Path(root)
    if not root.exists():
        return  # nothing to do here -.-

    for p in root.iterdir():
        if p.is_dir():
            rmtree(p)
        else:
            p.unlink()

    root.rmdir()


def slugify(s: str) -> str:
    """https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    s = str(s).strip().replace(" ", "_")
    s = s.replace(".", "_dot_")
    return re.sub(r"(?u)[^-\w.]", "", s)
