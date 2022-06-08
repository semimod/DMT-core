""" Provdes a class for TCAD DuTs

Provides a interface superclass. Here all methods which must be implemented by all TCAD interfaces are collected.

Author: Mario Krattenmacher | Mario.Krattenmacher@semimod.de
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
import copy
import logging
from DMT.core import create_md5_hash, DutView


class DutTcad(DutView):
    """Superclass for common methods and attributes of TCAD DuTs

    Makes a TCAD simulator like DEVICE or Hdev useable by DMT

    Parameters
    ----------
    database_dir    : string
        This is the directory were the DUT will create its database.
    name      : string
        Prefix for the database
    dut_type   : :class:`~DMT.core.dut_type.DutType`
        Type of the DUT.
    nodes     : string
        Strings with comma separated node names of DUT. If nodes is None, nodes will be requested from Dut_type class.
    inp_structure : str or InpTcad
        One of 3 different possibilities: special obj for create_inp_header(), string with path to file or direct input file string
    simulator_command : str
        Command to start the correct TCAD simulator
    simulator_arguments : list[str]
        List of arguments for the simulator command, will be added one by one before the input file.

    Attributes
    ----------
    sim_command : str
        Command to start the correct TCAD simulator
    sim_args : list[str]
        List of arguments for the simulator command, will be added one by one before the input file.

    Methods
    -------
    inp_header(value)
        Returns input header of a simulation input file, or sets it to a new value, removing attached files.
    inp_structure(value)
        Returns input structure for DUT, or sets it while automatically creating a new header.
    get_hash()
        Returns hash if inp_header is set.
    get_start_sim_command()
        Returns command to start a specific type of simulation (DEVICE, Hdev, ...).
    run_sim(sweep)
        Starts a simulation.
    create_inp_header(inp_structure)
        Creates an inp_header for a given inp_structure. Has to be set by inheriting class.
    set_param()
        Enables setting model parameters for a simulation. Has to be set by in heriting class.
    get_param()
        Enables getting model parameters for a simulation. Has to be set by in heriting class.
    """

    def __init__(self, database_dir, name, dut_type, inp_structure, **kwargs):
        # use the property setter method to analyze inp_structure.
        self._inp_header = None
        self._inp_structure = None

        super().__init__(database_dir, name, dut_type, **kwargs)

        # set the input structure to the input header property and let it handle it.
        self.inp_header = inp_structure

    @property
    def inp_header(self):
        """Getter method for the input header of the simulation input file"""
        return self._inp_header

    @inp_header.setter
    def inp_header(self, value):
        """Setter method for the input header. This removes any stored data from the object, as it is not valid anymore!
        Automatically recalls create_inp_header, if it is not a string.

        Parameters
        ----------
        value : str or anything fitting for overwritten create_inp_header
        """
        self._data = {}
        self._inp_structure = None

        if isinstance(value, str):
            try:
                with open(value, "r") as inp_file:
                    self._inp_header = inp_file.read()
            except IOError:
                # could not open input file. Assume it is the already read string
                self._inp_header = value
        else:
            self._inp_structure = copy.deepcopy(value)
            self._inp_header = self.create_inp_header(value)

        logging.info(
            "Successfully created input header of dut %s%s!", self.name, str(self.get_hash())
        )
        logging.debug("Content:\n%s", self._inp_header)

    def get_hash(self):
        """Returns a md5 hash generated from self.inp_header, if it is not set, this will return False!

        In case a InpStructure is set, this always recreates the inp_header :/.

        Returns
        -------
        str or False
        """
        if self.inp_header is None:
            return False

        # i have to ensure always correct hash for a dut... sorry
        if self._inp_structure is not None:
            self._inp_header = self.create_inp_header(self._inp_structure)

        return create_md5_hash(self._inp_header + self.sim_command)

    def create_inp_header(self, inp_structure):
        """Creates the inp_header from the given parameter object.

        Parameters
        ----------
        inp_structure
            Type and content depends on implementation of inheriting class!

        Returns
        -------
        str
            Input circuit
        """
        raise NotImplementedError("create_inp_header() must be implemented in inheriting class!")
