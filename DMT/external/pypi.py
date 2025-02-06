"""DMT interaction with pypi"""

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

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo


def get_pypi_url(package="DMT-core", version=None, pattern=".whl"):
    """Obtains the download url to a file inside a pypi released package

    Parameters
    ----------
    package : str, optional
        Package name from which a file url is wanted, by default "DMT-core"
    version : _type_, optional
        Version of the release to be checked, by default None=newest release
    pattern : str, optional
        Pattern to search for inside the release, by default ".whl"

    Raises
    ------
    IOError
        If the package was not found on PyPi
    IOError
        Raised if pattern not found in any file of the release

    Returns
    -------
    str
        url to download the file from
    """
    package = requests.get(
        f"https://pypi.python.org/pypi/{package:s}/json",
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "DNT": "1",
            "Host": "pypi.org",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        },
    ).json()
    if "message" in package and package["message"] == "Not Found":
        raise IOError("DMT->pypi: Package not found as a pypi python module.")

    if version is None:
        version = max(package["releases"].keys())
    # ... check compatibility
    try:
        file_to_get = next(
            file for file in package["releases"][version] if re.search(pattern, file["filename"])
        )
    except StopIteration as err:
        raise IOError(
            "DMT->pypi: Did not find any file name containing the given pattern."
        ) from err
    return file_to_get["url"]


def check_version(to_check, package="DMT-core"):
    if to_check.startswith("Version_"):
        to_check = to_check[8:]

    to_check = VersionInfo.parse(to_check)
    if to_check.prerelease is not None and not to_check.prerelease.startswith("rc."):
        raise IOError("The DMT naming schneme is: X.Y.Z-rc.A")

    # try:
    package = requests.get(
        f"https://pypi.python.org/pypi/{package:s}/json",
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "DNT": "1",
            "Host": "pypi.org",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        },
    ).json()
    if package.get("message") == "Not Found":
        # did not find package on pypi
        # so any version which is parseable is ok
        return str(to_check)

    latest_version = max(package["releases"].keys())

    version_pkg = latest_version.split(".")
    if "rc" in version_pkg[2]:
        patch = version_pkg[2].split("rc")[0]
        rc = version_pkg[2][len(patch) + 2 :]
        latest_version = VersionInfo(
            major=version_pkg[0],
            minor=version_pkg[1],
            patch=patch,
            prerelease="rc." + rc,
        )
    else:
        latest_version = VersionInfo(
            major=version_pkg[0], minor=version_pkg[1], patch=version_pkg[2]
        )
    # except

    if to_check > latest_version:
        return str(to_check)
    else:
        raise IOError("Version is smaller than or equal as already published version")


def extract_version(to_check):
    if to_check.startswith("Version_"):
        to_check = to_check[8:]

    to_check = VersionInfo.parse(to_check)
    if to_check.prerelease is not None and not to_check.prerelease.startswith("rc."):
        raise IOError("The DMT naming schneme is: X.Y.Z-rc.A")

    return str(to_check)


parser = argparse.ArgumentParser(description="Obtain information about a module on pypi.org")

parser.add_argument(
    "--check_version",
    type=str,
    help="Check if given version is a valid SemVer version and also a valid next version for the given package.",
    required=False,
    default=None,
)
parser.add_argument(
    "--extract_version",
    type=str,
    help="Extracts the version from a commit tag.",
    required=False,
    default=None,
)
parser.add_argument(
    "--wheel_link",
    action="store_true",
    help="Pass to obtain a wheel link.",
    required=False,
)
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

if __name__ == "__main__":
    args = parser.parse_args()

    if args.wheel_link:
        file_link = get_pypi_url(package=args.package, version=args.version, pattern=args.pattern)
        print(file_link)
    elif args.check_version is not None:
        version = check_version(args.check_version, package=args.package)
        print(version)
    elif args.extract_version is not None:
        print(extract_version(args.extract_version))
    else:
        raise IOError()
