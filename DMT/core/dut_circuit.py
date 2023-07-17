""" Provdes a class for cirtuit DuTs

Provides a interface superclass. Here all methods which must be implemented by all circuit simulator interfaces are collected.

A DuT can be supplied using the input_circuit parameter. This parameter can be:

* :class:`~DMT.core.circuit.Circuit`
* String with path to a netlist of a circuit
* String with the netlist of a circuit
* List with paths to netlists or strings with netlists, these will be combined into the netlist to simulate.


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
from collections import OrderedDict
from typing import List, Dict
from DMT.core import create_md5_hash, DutView, McParameterCollection, DutType, Technology
from DMT.core.mcard import MCard

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

SEMVER_DUTCIRCUIT_CURRENT = VersionInfo(major=1, minor=0)


class DutCircuit(DutView):
    """Superclass for common methods and attributes of cirtuit DuTs

    Makes a circuit simulator like ADS or XYCE useable by DMT

    Parameters
    ----------
    database_dir    : string
        This is the directory were the DUT will create its database.
    name      :  string
        Prefix for the database
    dut_type   : :class:`~DMT.core.dut_type.DutType`
        Type of the DUT.
    nodes     : string
        Strings with comma separated node names of DUT. If nodes is None, nodes will be requested from Dut_type class.
    inp_header : str, list[str] or :class:`~DMT.classes.circuit.Circuit`
        Depending of the used simulator, here different options are possible.
    simulator_options : OrderedDict


    Attributes
    ----------
    sim_command : str
        Command to start the correct circuit simulator
    sim_args : list[str]
        List of arguments for the simulator command, will be added one by one before the input file.
    """

    def __init__(
        self,
        database_dir: str,
        name: str,
        dut_type: DutType,
        inp_circuit,
        simulator_options: dict = None,
        get_circuit_arguments: dict = None,
        **kwargs
    ):
        self._inp_header = ""

        super().__init__(database_dir, name, dut_type, **kwargs)

        if simulator_options is None:
            self.simulator_options = OrderedDict()
        else:
            self.simulator_options = OrderedDict(sorted(simulator_options.items()))

        if get_circuit_arguments is None:
            self.get_circuit_arguments = OrderedDict()
        else:
            self.get_circuit_arguments = OrderedDict(sorted(get_circuit_arguments.items()))

        # save for later use
        self._inp_circuit = None
        self._modelcard = None
        self.inp_header = inp_circuit

    @property
    def inp_header(self):
        """Getter method for the input header of the simulation input file"""
        return self._inp_header

    @inp_header.setter
    def inp_header(self, value):
        """Setter method for the input header. This removes any stored data from the object, as it is not valid anymore! Automatically calls create_inp_header, if it is not a string or a list of strings.

        Parameters
        ----------
        value : str, list[string] or valid for create_inp_header
        """
        value = copy.deepcopy(value)
        self._inp_circuit = None
        self._data = {}  # empty the data dict!
        if isinstance(value, str):
            try:
                with open(value, "r") as inp_file:
                    self._inp_header = inp_file.read()
            except IOError:
                # could not open input file. Assume it is already a netlist
                self._inp_header = value
        elif isinstance(value, (list, tuple)):
            # list of files and/or netlist strings. They are all joined into one input header.
            inp_header = ""
            for netlist in value:
                try:
                    with open(netlist, "r") as inp_file:
                        inp_header = inp_header + "\n" + inp_file.read()
                except IOError:
                    # could not open input file. Assume it is already a netlist
                    inp_header = inp_header + "\n" + netlist

            self._inp_header = inp_header
        else:
            self._inp_circuit = copy.deepcopy(value)
            self._inp_header = self.create_inp_header(value)

    def info_json(self, **_kwargs) -> Dict:
        """Returns a dict with serializeable content for the json file to create.

        The topmost dict MUST have only one key: The string casted class name.
        Inside the parameters are:

            * A version key,
            * all extra parameters of DutCircuit compared to DutView and
            * the info_json of DutView.

        Returns
        -------
        dict
            str(DutCircuit): serialized content
        """
        modelcard = None
        if self._modelcard is not None:
            modelcard = self._modelcard.dumps_json()
        return {
            "__DutCircuit__": str(SEMVER_DUTCIRCUIT_CURRENT),
            "parent": super(DutCircuit, self).info_json(**_kwargs),
            "inp_header": self.inp_header,
            "simulator_options": self.simulator_options,
            "get_circuit_arguments": self.get_circuit_arguments,
            "modelcard": modelcard,
        }

    @classmethod
    def from_json(
        cls,
        json_content: Dict,
        classes_technology: List[type[Technology]],
        subclass_kwargs: Dict = None,
    ) -> "DutCircuit":
        """Static class method. Loads a DutCircuit object from a pickle file with full path save_dir.

        Calls the from_json method of DutView with all dictionary inside the "parent" keyword. Afterwards the additional parameters are set correctly.

        Parameters
        ----------
        json_content  :  dict
            Readed dictionary from a saved json DutCircuit.
        classes_technology : List[type[Technology]]
            All possible technologies this loaded DutCircuit can have. One will be choosen according to the serialized technology loaded from the file.
        subclass_kwargs : Dict, optional
            Additional kwargs necessary to create the concrete subclassed DutView.

        Returns
        -------
        DutTcad
            Loaded object.
        """
        if json_content["__DutCircuit__"] != SEMVER_DUTCIRCUIT_CURRENT:
            raise NotImplementedError("DMT.DutCircuit: Unknown version of DutCircuit to load!")

        if subclass_kwargs is None:
            subclass_kwargs = {}
        subclass_kwargs["inp_circuit"] = json_content["inp_header"]

        dut_view = super().from_json(
            json_content["parent"], classes_technology, subclass_kwargs=subclass_kwargs
        )

        dut_view._modelcard = json_content["modelcard"]
        dut_view.simulator_options = json_content["simulator_options"]
        dut_view.get_circuit_arguments = json_content["get_circuit_arguments"]

        return dut_view

    @property
    def modelcard(self):
        """Returns the saved modelcard"""
        return self._modelcard

    @modelcard.setter
    def modelcard(self, modelcard):
        """Forces a new inp_header!

        Parameters
        ----------
        modelcard : MCard
        """
        if isinstance(modelcard, MCard) or isinstance(modelcard, McParameterCollection):
            self._modelcard = modelcard
            self.inp_header = modelcard
        else:
            raise OSError("The modelcard has to be a instance of MCard or its children!")

    def get_hash(self):
        """Returns a md5 hash generated from self.inp_header, if it is not set, this will return False!

        Is overwritten here, to include the imported and appended files!

        Returns
        -------
        str or False

        Notes
        -----
        Also account for dut.name?
        """
        if self.inp_header is None:
            return False

        if self._list_va_file_contents:
            list_va = [
                vafile.get_tree_hash() for vafile in self._list_va_file_contents
            ]  # directly use the hash here - hash of hash should be ok :)
        else:
            list_va = []
        return create_md5_hash(self.inp_header, *self.list_copy, *list_va)

    def create_inp_header(self, inp_circuit):
        """Creates the inp_header from the given circuit.

        Parameters
        ----------
        inp_circuit
            Type and content depends on implementation of inheriting class!

        Returns
        -------
        str
            input header
        """
        raise NotImplementedError("create_inp_file() must be implemented in inheriting class!")

    def _convert_CircuitElement_netlist(self, circuit_element):
        """Transforms a :class:`~DMT.classes.circuit.CircuitElement` into a string fitting for the inheriting DutCircuit.

        Parameters
        ----------
        circuit_element
            CircuitElement to transform

        Returns
        -------
        str
            Netlist line
        """
        raise NotImplementedError(
            "_convert_CircuitElement_netlist() must be implemented in inheriting class!"
        )

    def scale_modelcard(self):
        """Scales the given modelcard to the actual size of the dut."""
        if self.technology is None or not hasattr(self.technology, "scale_modelcard"):
            self.modelcard = self.modelcard
        else:
            self.modelcard = self.technology.scale_modelcard(
                self.modelcard,
                self.length,
                self.width,
                self.nfinger,
                self.contact_config,
            )
