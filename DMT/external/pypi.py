#!/usr/bin/python3
""" DMT interaction with pypi
"""
# DMT_core
# Copyright (C) from 2022  SemiMod
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
import requests
import re
import argparse


def get_file_idx(release, pattern=".whl"):
    return next(file_a for file_a in release if re.search(pattern, file_a["filename"]))


def get_pypi_url(package="DMT-core", version=None, pattern=".whl"):
    package = requests.get(f"https://pypi.python.org/pypi/{package:s}/json").json()
    if version is None:
        version = max(package["releases"].keys())
    # ... check compatibility
    file_to_get = next(
        file for file in package["releases"][version] if re.search(pattern, file["filename"])
    )
    return file_to_get["url"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Obtain the link to a file at pypi.org")
    parser.add_argument(
        "--package",
        type=str,
        help="Package to query (default: %(default)s).",
        default="DMT-core",
        required=False,
    )
    parser.add_argument(
        "--version",
        type=str,
        help="Version of the query. If None, the newest version is used (default: %(default)s).",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--pattern",
        type=str,
        help="Pattern to scan the different files of the release (default: %(default)s).",
        default=".whl",
        required=False,
    )
    parser.parse_args()

    file_link = get_pypi_url()
    print(file_link)
