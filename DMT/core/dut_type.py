""" Used to flag the dut type for each dut view

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
from enum import Flag, auto, unique


class DutTypeInt(object):
    """Class for DutType flags. Adds the nodes attribute to an integer value. This allows direct assignment of nodes to a DutType.

    Parameters
    ----------
    value : int
    node  : [str]
        List of nodes.
    """

    def __init__(self, value, nodes=None, string=None):
        try:
            self.value = value.value
        except AttributeError:
            self.value = int(value)

        if nodes is not None:
            self.nodes = nodes
        else:
            try:
                self.nodes = value.nodes
            except AttributeError:
                self.nodes = []

        self.string = string

    def get_nodes(self):
        """Return the nodes that are typically found in this Dut_type. For convenience.

        Repeated here just to get rid of the pylint error. The real method is below in the DutType-flag

        Returns
        -------
        nodes  :  list of strings
            List of strings
        """
        return self.nodes

    def get_string(self):
        """Return the string that describes this Dut_type.

        Returns
        -------
        string  :  string
            the string that describes this object
        """
        return self.string

    def __and__(self, other):
        try:
            return DutTypeInt(self.value & other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value & other, nodes=self.nodes)

    def __rand__(self, other):
        return self.__and__(other)

    def __xor__(self, other):
        try:
            return DutTypeInt(self.value ^ other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value ^ other, nodes=self.nodes)

    def __rxor__(self, other):
        return self.__xor__(other)

    def __or__(self, other):
        try:
            return DutTypeInt(self.value | other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value | other, nodes=self.nodes)

    def __ror__(self, other):
        return self.__or__(other)

    def __eq__(self, other):
        try:
            return self.value == other.value
        except AttributeError:
            return self.value == other

    def __invert__(self):
        return DutTypeInt(~self.value, nodes=self.nodes)

    def __bool__(self):
        return bool(self.value)

    def __str__(self):
        return self.string

    def __int__(self):
        return self.value

    def is_subtype(self, other):
        """Test if a device is a subtype of an other device/devicetype

        Ignores the flag_subtype!

        Parameters
        ----------
        other : int, DutTypeInt
        """
        try:
            val = int(self.value & other.value)
        except AttributeError:
            val = int(self.value & other)

        # remove subtype flag..
        n_subtype_1 = ~int(DutTypeFlag._flag_subtype_1.value)
        n_subtype_2 = ~int(DutTypeFlag._flag_subtype_2.value)
        n_subtype_3 = ~int(DutTypeFlag._flag_subtype_3.value)
        n_subtype_4 = ~int(DutTypeFlag._flag_subtype_4.value)

        val = (val & n_subtype_1) & (val & n_subtype_2) & (val & n_subtype_3) & (val & n_subtype_4)

        return bool(val)

    def __lt__(self, other):
        try:
            return DutTypeInt(self.value < other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value < other, nodes=self.nodes)

    def __le__(self, other):
        try:
            return DutTypeInt(self.value <= other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value <= other, nodes=self.nodes)

    def __gt__(self, other):
        try:
            return DutTypeInt(self.value > other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value > other, nodes=self.nodes)

    def __ge__(self, other):
        try:
            return DutTypeInt(self.value >= other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value >= other, nodes=self.nodes)

    def __sub__(self, other):
        try:
            return DutTypeInt(self.value - other.value, nodes=self.nodes)
        except AttributeError:
            return DutTypeInt(self.value - other, nodes=self.nodes)

    def __hash__(self):
        return hash((self.value, tuple(self.nodes), self.string))

    def bit_length(self):
        return self.value.bit_length()


@unique  # do not allow same values for different types
class DutTypeFlag(Flag):
    """
    Flags which represents most common devices that might need to be handled by DMT

    Methods
    -------
    get_nodes(filename)
        Returns the names of the nodes typicall found in the specified DutType
    """

    _flag_subtype_1 = auto()
    _flag_subtype_2 = auto()
    _flag_subtype_3 = auto()
    _flag_subtype_4 = auto()
    flag_device = auto()
    flag_bulk = auto()
    flag_meas_struct = auto()
    flag_deemb_struct = auto()
    flag_transistor = auto()
    flag_bjt = auto()
    flag_bjt_deemb = auto()
    flag_mos = auto()
    flag_mos_deemb = auto()
    flag_diode = auto()
    flag_cap = auto()
    flag_res = auto()
    flag_tetrode = auto()
    flag_tlm = auto()
    flag_deem = auto()
    flag_vdp = auto()

    flag_npn = auto()
    flag_pnp = auto()
    flag_n_mos = auto()
    flag_p_mos = auto()

    flag_open = auto()
    flag_short = auto()

    def get_nodes(self):
        """
        Return the nodes that are typically found in this DutType. For convenience.

        Returns
        -------
        nodes  :  list of strings
            List of strings
        """
        return ""

    def get_string(self):
        """
        Return the string that describes this DutType.

        Returns
        -------
        nodes  :  string
            String that describes this DutType.
        """
        return ""

    def __str__(self):
        return str(self.value.__class__)


class DutType(object):
    """concrete DutTypes to be used for DutViews"""

    dummy = DutTypeInt(0)  # dummy is nothing! Use DutTypeInt to allow get_nodes
    device = DutTypeInt(DutTypeFlag.flag_device)
    bulk = DutTypeInt(DutTypeFlag.flag_bulk)
    meas_struct = DutTypeInt(DutTypeFlag.flag_meas_struct)
    deemb_struct = DutTypeInt(DutTypeFlag.flag_deemb_struct)

    # now the mixed flags, are DutTypeInts as the numbers are already given:
    transistor = DutTypeInt(device | DutTypeFlag.flag_transistor)
    bjt = DutTypeInt(transistor | DutTypeFlag.flag_bjt, nodes=["B", "C", "E", "S"], string="bjt")
    mos = DutTypeInt(transistor | DutTypeFlag.flag_mos, nodes=["G", "D", "S", "B"], string="mos")
    deem_bjt = DutTypeInt(
        deemb_struct | DutTypeFlag.flag_bjt_deemb,
        nodes=["B", "C", "E", "S"],
        string="bjt_deemb",
    )  # because of node names :(
    deem_mos = DutTypeInt(
        deemb_struct | DutTypeFlag.flag_mos_deemb,
        nodes=["G", "D", "S", "B"],
        string="mos_deemb",
    )  # because of node names :(

    npn = DutTypeInt(bjt | DutTypeFlag.flag_npn, string="npn")  # nodes are inherited from bjt
    pnp = DutTypeInt(bjt | DutTypeFlag.flag_pnp, string="pnp")
    n_mos = DutTypeInt(mos | DutTypeFlag.flag_n_mos, string="nmos")
    p_mos = DutTypeInt(mos | DutTypeFlag.flag_p_mos, string="pmos")

    diode = DutTypeInt(device | DutTypeFlag.flag_diode, nodes=["C", "A"], string="diode")
    pn_diode = DutTypeInt(diode | DutTypeFlag._flag_subtype_1, string="pn-diode")
    pin_diode = DutTypeInt(diode | DutTypeFlag._flag_subtype_2, string="pin-diode")
    cap = DutTypeInt(device | DutTypeFlag.flag_cap, nodes=["C", "A"], string="capacitance")
    res = DutTypeInt(device | DutTypeFlag.flag_res, nodes=["C", "A"], string="resistor")

    tlm = DutTypeInt(
        meas_struct | DutTypeFlag.flag_tlm, nodes=["L", "M", "R"], string="tlm"
    )  # left, middle, right
    tlmb = DutTypeInt(tlm | DutTypeFlag._flag_subtype_1, string="tlm-base")
    tlmc = DutTypeInt(tlm | DutTypeFlag._flag_subtype_2, string="tlm-collector")
    tlmbc = DutTypeInt(tlm | DutTypeFlag._flag_subtype_3, string="tlm-base-collector")

    vdp = DutTypeInt(
        meas_struct | DutTypeFlag.flag_vdp, nodes=["A", "B", "C", "D"], string="vdp"
    )  # four arbitrary contacts

    deem_open_bjt = DutTypeInt(deem_bjt | DutTypeFlag.flag_open, string="open")
    deem_short_bjt = DutTypeInt(deem_bjt | DutTypeFlag.flag_short, string="short")

    deem_open_mos = DutTypeInt(deem_mos | DutTypeFlag.flag_open, string="open")
    deem_short_mos = DutTypeInt(deem_mos | DutTypeFlag.flag_short, string="short")

    tetrode = DutTypeInt(
        meas_struct | DutTypeFlag.flag_tetrode,
        nodes=["B1", "B2", "E", "C", "S"],
        string="tetrode",
    )

    cap_ac = DutTypeInt(
        cap | meas_struct, nodes=["L", "R", "G", "S"], string="capacitance-ac"
    )  # capacitance in GSG pads, each pad is one Capacitance, so S(1,1) and S(2,2) are wanted...
