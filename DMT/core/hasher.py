""" Creates MD5-HASH from given string-convertable data.

In DMT this is used mainly to ensure unique simulation folders and keys.
A simulation folder consist of 3 parts:

* The simulation directory in used the :ref:`config`
* The dut subfolder named `<dut_name><dut_hash>`. The dut name is a attribute of :ref:`DutView<dut_view>`. The hash calculation depends on the subclass, but most times this is simply the MD5-Hash of all input files, for example the netlist file and the Verilog-AMS code.
* The sweep subfolder named `<sweep_name><sweep_hash>`. The sweep name is a attribute of :ref:`Sweep<sweep>`. The hash is calculated from text converted sweep definition.

Author: Mario Krattenmacher | Mario.Krattenmacher@semimod.de
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
import hashlib
import os
from typing import Union


def create_md5_hash(*contents: Union[str, os.PathLike]):
    """Construct the hash MD5 string with all parameters

    Parameters
    ----------
    contents : str
        Either a path to a file to read or some object which can be converted to a string using str()

    Returns
    -------
    str
        MD5 string
    """
    str_to_hash = ""

    for content in contents:
        try:  # is content a file?
            with open(content) as my_file:
                str_to_hash += my_file.read()
        except (OSError, ValueError, TypeError):
            # content is a castable?
            str_to_hash += str(content)

    # create hash object from python lib
    hash_creator = hashlib.md5()
    # feed the binary string into the object
    hash_creator.update(str_to_hash.encode())

    return hash_creator.hexdigest()
