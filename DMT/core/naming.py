r""" Global namings for DMT

Internally all variables and column names which contain a quantity of a specifier must have the same given names, e.g. all voltages will be called: 'V\_'
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

from __future__ import annotations
import copy
import numpy as np
from typing import List, Union
from pint.formatting import siunitx_format_unit
from more_itertools import unique_everseen
from DMT.config import DATA_CONFIG
from DMT.core import Singleton, unit_registry
import pint

UNIT_PREFIX = {
    1e-12: r"\tera",
    1e-9: r"\giga",
    1e-6: r"\mega",
    1e-3: r"\kilo",
    1: r"",
    1e3: r"\milli",
    1e6: r"\micro",
    1e9: r"\nano",
    1e12: r"\pico",
    1e15: r"\femto",
}
UNIT_PREFIX_MIX = {
    "J": {  # current density
        1e-9: r"\milli\ampere\per\square\micro\meter",
        1e-6: r"\micro\ampere\per\square\micro\meter",
        1e-3: r"\milli\ampere\per\square\micro\meter",
        1e-0: r"\ampere\per\square\micro\meter",
    },
    "F": {
        1: r"\volt\per\meter",
        1e-5: r"\kilo\volt\per\centi\meter",
    },  # field
}
UNIT_PREFIX_DENOMINATOR = {
    1e-6: r"\centi",
}


class SpecifierStr(str):
    """Acts like a string, but at the same time has the attribute "nodes"

    https://stackoverflow.com/a/2673863

    Yeah it is already implemented :P

    Parameters
    ----------
    specifier : str
    nodes : [str], optional
    sub_specifiers : [str], str, {'', sub_specifier}, optional

    Attributes
    ----------
    specifier : str
    nodes : [str]
    sub_specifiers : [str]

    """

    specifier: str = ""
    nodes: List[str] = []
    sub_specifiers: List[str] = []

    # pylint: disable=no-member
    def __new__(
        cls,
        specifier: Union[str, SpecifierStr],
        *nodes: str,
        sub_specifiers: Union[List[Union[str, SpecifierStr]], str, SpecifierStr, None] = None,
    ):
        if not nodes and sub_specifiers is None:
            try:
                nodes = specifier.nodes  # type: ignore
                sub_specifiers = specifier.sub_specifiers  # type: ignore
                specifier = specifier.specifier  # type: ignore
            except AttributeError:
                # revert old state if an Attribute error occurs!
                nodes = ()
                sub_specifiers = None

        # cast to list
        if sub_specifiers is None:
            sub_specifiers = []
        elif isinstance(sub_specifiers, str):
            sub_specifiers = [sub_specifiers]

        for i, sub_specifier in enumerate(sub_specifiers):
            if isinstance(sub_specifier, SpecifierStr):
                sub_specifiers[i] = sub_specifier.sub_specifiers[0]

        # check if any sub_specifiers are empty
        while "" in sub_specifiers:
            sub_specifiers.remove("")

        sub_specifiers = [str(sub_specifier) for sub_specifier in sub_specifiers]  # string cast :/

        # unique
        sub_specifiers = list(unique_everseen(sub_specifiers))

        # check if all are valid sub_specifiers
        # if any(sub_specifier not in SUB_SPECIFIERS_STR for sub_specifier in sub_specifiers):
        #     # add the new sub_specifier to naming.sub_specifiers and also to SUB_SPECIFIERS_STR
        #     # Not done because parameter sub_specifiers replaces the module attribute
        #     raise SpecifierNotKnown('The sub_specifiers part of a column name can only be one of the following:\n' + str(SUB_SPECIFIERS_STR))

        if nodes and "".join(nodes):  # string cast :/
            nodes = [str(node) for node in nodes]  # type: ignore
            node_str = "_" + "".join(nodes)
        else:
            node_str = ""
            nodes = []  # type: ignore
            # make sure nodes is a list not a tuple

        if sub_specifiers:
            sub_specifiers_str = "|" + "|".join(sub_specifiers)
        else:
            sub_specifiers_str = ""

        col_name = str(specifier) + node_str + sub_specifiers_str

        obj = str.__new__(cls, col_name)
        obj.specifier = str(specifier)
        obj.nodes = nodes  # type: ignore
        obj.sub_specifiers = sub_specifiers  # type: ignore
        return obj

    def get_tex_unit(self, scale=1, add="") -> str:
        r"""Get the unit of a given specifier in base units.

        If scale is different from one, a suitable unit prefix is chosen. E.g. scale=1e3 and specifier=CURRENT -> \si{\milli\ampere}

        Parameters
        ----------
        scale : float, integer
            Unit prefix determination scale.
        add : string
            Additional string that is added to the unit

        Returns
        -------
        unit : string
            TeX representation of the specifer's unit
        """
        unit = self.get_pint_unit()

        if sub_specifiers.PHASE.sub_specifiers[0] in self.sub_specifiers:
            return r"\si{\degree}"

        elif self.specifier in UNIT_PREFIX_MIX:  # mixed unit
            try:
                unit_prefix_mix = UNIT_PREFIX_MIX[self.specifier][np.round(scale, decimals=10)]
                return r"\si{" + unit_prefix_mix + r"}"
            except KeyError as err:
                raise IOError(
                    "DMT -> Plot: natural unit for " + self.specifier + " not implemented."
                ) from err

        else:  # pure unit
            # for non-mixed quantities like voltages and current

            # get unit from pint
            try:
                unit = siunitx_format_unit(unit)  # type: ignore
            except TypeError:
                unit = siunitx_format_unit(
                    unit._units, unit_registry
                )  # new version has other interface

            if unit.startswith("\\per"):
                # for 1/m^3 -> unit prefix should be in the denominator
                unit = "\\per" + UNIT_PREFIX_DENOMINATOR[scale] + unit[4:]
            else:
                unit = UNIT_PREFIX[scale] + unit

            return r"\si{" + unit + add + r"}"

    def to_label(self, scale=1, negative=False, divide_by_unit=False) -> str:
        """Generates a label for plots for this specifier, where scale determines the unit prefix.

        Parameters
        ----------
        scale : float, integer, optional
            Unit prefix determination scale.

        negative : bool, optional
            If True, a minus sign is added before the label

        divide_by_unit : bool, optional
            If True, the unit is given as division, if False in brackets.

        Returns
        -------
        unit : string
            TeX representation of the specifer's unit
        """
        tex_unit = self.get_tex_unit(scale=scale)
        if divide_by_unit:
            if tex_unit == unit_registry.dimensionless or tex_unit == "\\si{}":
                tex_unit = ""
            else:
                tex_unit = "/" + tex_unit
            if negative:
                return r"$-" + self.to_tex() + tex_unit + r"$"
            else:
                return r"$" + self.to_tex() + tex_unit + r"$"
        else:
            left_brack = r"\left("
            right_brack = r"\right)"
            if tex_unit == unit_registry.dimensionless or tex_unit == "\\si{}":
                left_brack = ""
                right_brack = ""
            if negative:
                return r"$-" + self.to_tex() + left_brack + tex_unit + right_brack + r"$"
            else:
                return r"$" + self.to_tex() + left_brack + tex_unit + right_brack + r"$"

    def to_legend_with_value(self, value, scale=1, **kwargs) -> str:
        """Creates a SI legend entry in the form : specifier_tex = \\SI{value}{scale, spec_unit}

        Parameters
        ----------
        value : float
            Value to print into the legend
        scale : int, optional
            Scaling of unit and value using SI prefixes, by default 1.
        **kwargs
            Are passed to specifier.to_tex

        Returns
        -------
        str
            math tex legend entry
        """
        value = np.real(value)

        unit = self.get_pint_unit()
        try:
            unit = siunitx_format_unit(unit)  # type: ignore
        except TypeError:
            unit = siunitx_format_unit(
                unit._units, unit_registry
            )  # new version has other interface
        # for non-mixed quantities like voltages and current
        if self.specifier in UNIT_PREFIX_MIX:  # mixed unit
            unit_with_prefix = UNIT_PREFIX_MIX[self.specifier][np.round(scale, decimals=10)]

            return f"${self.to_tex(**kwargs):s}=\\SI{{{value * scale:.2f}}}{{{unit_with_prefix:s}{unit:s}}}$"

        else:
            unit_prefix = UNIT_PREFIX[scale]

            return f"${self.to_tex(**kwargs):s}=\\SI{{{value * scale:.2f}}}{{{unit_prefix:s}{unit:s}}}$"

    def to_raw_string(self) -> str:
        """get a raw string from the specifier -> can be used for string operations and variable naming...

        Returns
        -------
        str : string
            string conversion of self...
        """
        return str(self)  # not tested

    def string_to_save(self) -> str:
        """Generates a single string which allows to identify the specifers, nodes and subspecifiers. Used to save into HDF5 as there the columns have to be valid strings."""
        return (
            "$"
            + str(self.specifier)
            + "#"
            + "?".join([str(node) for node in self.nodes])
            + "!"
            + "|".join([str(sub_specifier) for sub_specifier in self.sub_specifiers])
        )

    @classmethod
    def string_from_load(cls, string) -> str:
        """Generates a SpecifierStr from a string if the string was generated using :meth:`~DMT.core.specifiers.SpecifierStr.string_to_save`."""
        if string.startswith("$"):  # SpecifierStr
            splitted = string[1:].split("#")
            spec = splitted[0]
            splitted = splitted[1].split("!")

            nodes = splitted[0].split("?")
            sub_specifiers = splitted[1].split("|")
            return SpecifierStr(spec, *nodes, sub_specifiers=sub_specifiers)
        else:  # it was just a regular str
            return string

    def __add__(
        self: SpecifierStr, other: Union[SpecifierStr, str, list[Union[str, SpecifierStr]]]
    ) -> SpecifierStr:
        """Method stub"""
        raise NotImplementedError

    def __radd__(self, other):
        # if isinstance(other, SpecifierStr): # not needed since __add__ is taking care of this!
        if isinstance(other, str):  # reflected str + SpecifierStr
            return SpecifierStr(
                other + self.specifier, *self.nodes, sub_specifiers=self.sub_specifiers
            )
        else:
            return NotImplemented

    def __eq__(self, other: Union[str, SpecifierStr]) -> bool:
        """Checks if two objects are equal

        Parameters
        ----------
        other : str | SpecifierStr
            Compare to this column name

        Returns
        -------
        bool
            True if equal
        """
        if isinstance(other, SpecifierStr):
            if self.specifier == other.specifier and self.nodes == other.nodes:
                # order of subspecifiers does not matter Oo
                if all(
                    sub_spec in other.sub_specifiers for sub_spec in self.sub_specifiers
                ) and all(
                    sub_spec in self.sub_specifiers for sub_spec in other.sub_specifiers
                ):  # check both directions...
                    return True
        elif isinstance(other, str):
            if str(self) == other:
                return True
            else:
                col_other = get_specifier_from_string(other, nodes=self.nodes)
                if isinstance(col_other, SpecifierStr):  # here also the order does not matter -.-
                    if self == col_other:
                        return True
        elif other is not None:
            return NotImplemented

        return False

    def __contains__(self, other: Union[str, SpecifierStr]) -> bool:
        """String contains

        Parameters
        ----------
        other : str | SpecifierStr
            Other string or specifier which may contains self

        Returns
        -------
        bool
            str(other) in str(self)
        """
        return str(other) in str(self)

    def __hash__(self):
        return hash(str(self))

    def get_pint_unit(self) -> pint.Unit:
        """Declaration of function, to be set later

        Returns
        -------
        pint.UnitRegistry
            [description]

        Raises
        ------
        NotImplementedError
            [description]
        """
        raise NotImplementedError()

    def get_descriptor(self) -> str:
        """Declaration of function, to be set later

        Returns
        -------
        str
            [description]

        Raises
        ------
        NotImplementedError
            [description]
        """
        raise NotImplementedError

    def to_tex(self) -> str:
        """Declaration of function, to be set later

        Returns
        -------
        str
            [description]

        Raises
        ------
        NotImplementedError
            [description]
        """
        raise NotImplementedError


class GlobalObj(object):
    """A simple class used to store class variables that are global. Also one can iterate over the class attributes in a sorted way."""

    _MEMBERS = []

    def __iter__(self):
        if not self._MEMBERS:
            self._set_members()

        for elem in list.__iter__(self._MEMBERS):
            yield elem

    def _set_members(self):
        """sets self._MEMBERS in a sorted fashion with a possible additional list."""
        members = [
            getattr(self, attribute)
            for attribute in dir(self)
            if not attribute.startswith("__")
            and not callable(getattr(self, attribute))
            and not attribute == "_MEMBERS"
        ]
        self._MEMBERS = sorted(members, key=len, reverse=True)


#############################################
# HOLY DEFINITION OF DMT NAMING CONVENTIONS #
#############################################
class _sub_specifiers(GlobalObj, metaclass=Singleton):

    PERIMETER = SpecifierStr("", sub_specifiers="PERI")
    AREA = SpecifierStr("", sub_specifiers="AREA")
    LENGTH = SpecifierStr("", sub_specifiers="LENGTH")
    WIDTH = SpecifierStr("", sub_specifiers="WIDTH")
    CORNER = SpecifierStr("", sub_specifiers="CORNER")
    FORCED = SpecifierStr("", sub_specifiers="FORCED")
    AC_BASE = SpecifierStr("", sub_specifiers="AC_BASE")
    AC_COLLECTOR = SpecifierStr("", sub_specifiers="AC_COLLECTOR")
    AC_GATE = SpecifierStr("", sub_specifiers="AC_GATE")
    AC_DRAIN = SpecifierStr("", sub_specifiers="AC_DRAIN")
    AC = SpecifierStr("", sub_specifiers="AC")
    REAL = SpecifierStr("", sub_specifiers="REAL")
    IMAG = SpecifierStr("", sub_specifiers="IMAG")
    MAG = SpecifierStr("", sub_specifiers="MAG")
    PHASE = SpecifierStr("", sub_specifiers="PHASE")
    NOISE = SpecifierStr("", sub_specifiers="NOISE")
    QUASISTATIC = SpecifierStr("", sub_specifiers="QUASISTATIC")
    JUNCTION = SpecifierStr("", sub_specifiers="JUNCTION")
    MINORITY = SpecifierStr("", sub_specifiers="MINORITY")
    MAJORITY = SpecifierStr("", sub_specifiers="MAJORITY")
    ELECTRONS = SpecifierStr("", sub_specifiers="ELECTRONS")
    HOLES = SpecifierStr("", sub_specifiers="HOLES")
    CHANNEL = SpecifierStr("", sub_specifiers="CHANNEL")
    MAX = SpecifierStr("", sub_specifiers="MAX")
    MIN = SpecifierStr("", sub_specifiers="MIN")
    MID = SpecifierStr("", sub_specifiers="MID")
    TRAPS = SpecifierStr("", sub_specifiers="TRAPS")
    YDIR = SpecifierStr("", sub_specifiers="YDIR")
    XDIR = SpecifierStr("", sub_specifiers="XDIR")
    ZDIR = SpecifierStr("", sub_specifiers="ZDIR")

    def add_members(self, members):
        for name, value in members:
            if name in dir(self):
                raise OSError("The subspecifier " + name + " already exists!")
            setattr(self, name, SpecifierStr("", sub_specifiers=value))

        self._set_members()


class _specifiers(GlobalObj, metaclass=Singleton):
    # Only Natural Quantities here
    VOLTAGE = SpecifierStr("V")
    FIELD = SpecifierStr("F")
    VELOCITY = SpecifierStr("VELO")
    GRADING = SpecifierStr("GRADING")
    RESISTANCE = SpecifierStr("R")
    POWER = SpecifierStr("P")
    CURRENT = SpecifierStr("I")
    CAPACITANCE = SpecifierStr("C")
    CHARGE = SpecifierStr("Q")
    INDUCTANCE = SpecifierStr("L")
    TEMPERATURE = SpecifierStr("TEMP")
    TIME = SpecifierStr("TIME")
    FREQUENCY = SpecifierStr("FREQ")
    VOLTAGE = SpecifierStr("V")
    ELECTRONS = SpecifierStr("N")
    CONDUCTION_BAND_EDGE = SpecifierStr("EC")
    VALENCE_BAND_EDGE = SpecifierStr("EV")
    HOLES = SpecifierStr("P")
    NET_DOPING = SpecifierStr("NNET")
    DONNORS = SpecifierStr("DON")
    ACCEPTORS = SpecifierStr("ACC")
    CURRENT_DENSITY = SpecifierStr("J")
    SPACE_CHARGE = SpecifierStr("RHO")
    QUASI_FERMI_POTENTIAL = SpecifierStr("PHI")
    ELECTRICAL_POTENTIAL = SpecifierStr("PSI")
    MOBILITY = SpecifierStr("MU")
    X = SpecifierStr("x")
    Y = SpecifierStr("y")
    Z = SpecifierStr("z")
    ENERGY = SpecifierStr("E")

    # only derived quantities here
    DC_CURRENT_AMPLIFICATION = SpecifierStr("BETA")
    TRANSCONDUCTANCE = SpecifierStr("GM")
    TRANSIT_FREQUENCY = SpecifierStr("F_T")
    MAXIMUM_OSCILLATION_FREQUENCY = SpecifierStr("F_MAX")
    MAXIMUM_AVAILABLE_GAIN = SpecifierStr("MAG")
    MAXIMUM_STABLE_GAIN = SpecifierStr("MSG")
    TRANSIT_TIME = SpecifierStr("TAU_F")
    UNILATERAL_GAIN = SpecifierStr("GU")

    # SpecifierStr objects for small signal parameters
    SS_PARA_S = SpecifierStr("S")
    SS_PARA_H = SpecifierStr("H")
    SS_PARA_Y = SpecifierStr("Y")
    SS_PARA_Z = SpecifierStr("Z")
    SS_PARA_A = SpecifierStr("A")
    SS_PARA_T = SpecifierStr("T")

    def add_members(self, members):
        for name, value in members:
            if name in dir(self):
                raise OSError("The specifier " + name + " already exists!")
            setattr(self, name, SpecifierStr(value))

        self._set_members()


class _specifiers_ss_para(GlobalObj, metaclass=Singleton):
    # SpecifierStr objects for small signal parameters, need to be repeated since these specifiers have unique properties
    SS_PARA_S = SpecifierStr("S")
    SS_PARA_H = SpecifierStr("H")
    SS_PARA_Y = SpecifierStr("Y")
    SS_PARA_Z = SpecifierStr("Z")
    SS_PARA_A = SpecifierStr("A")
    SS_PARA_T = SpecifierStr("T")


specifiers_ss_para: _specifiers_ss_para = _specifiers_ss_para()
"""Small signal parameters known to DMT."""

specifiers: _specifiers = _specifiers()
"""Specifiers known to DMT. In a written form these would be the variable."""

sub_specifiers: _sub_specifiers = _sub_specifiers()
"""Sub specifiers known to DMT. In a written form these would be placed in the subscript of a variable."""

specifiers.add_members(DATA_CONFIG["custom_specifiers"])
sub_specifiers.add_members(DATA_CONFIG["custom_sub_specifiers"])

# needed for addition
SUB_SPECIFIERS_STR = [
    str(member).replace("|", "") for member in sub_specifiers._MEMBERS
]  # pylint: disable=protected-access

##################################################
# add methods to SpecifierStr that depend on the defined specifiers above
##################################################


def add(self: SpecifierStr, other: Union[SpecifierStr, str, List[Union[str, SpecifierStr]]]):
    """Method is defined later, since we need the SUB_SPECIFIERS_STR list here...thanks python"""
    if isinstance(other, SpecifierStr):
        spec_new = self.specifier + other.specifier
        nodes_new = self.nodes + other.nodes
        sub_specifiers_new = self.sub_specifiers + other.sub_specifiers
        return SpecifierStr(spec_new, *nodes_new, sub_specifiers=sub_specifiers_new)

    elif isinstance(other, str):
        if other == "":
            return self

        if other[0] == "_" or other[0] == "|":
            other = other[1:]

        if other in SUB_SPECIFIERS_STR:
            return SpecifierStr(
                self.specifier, *self.nodes, sub_specifiers=self.sub_specifiers + [other]
            )
        else:
            return SpecifierStr(
                self.specifier, *self.nodes, other, sub_specifiers=self.sub_specifiers
            )  # @Mario we should discuss this

    elif isinstance(other, list):
        if self.nodes:
            return SpecifierStr(
                self.specifier, *self.nodes, sub_specifiers=self.sub_specifiers + other  # type: ignore
            )
        else:
            return SpecifierStr(self.specifier, *other, sub_specifiers=self.sub_specifiers)

    else:
        return NotImplemented


SpecifierStr.__add__ = add


def get_pint_unit(self) -> pint.Unit:
    """Return the DMT base unit of this specifier as a pint unit"""
    if sub_specifiers.PHASE.sub_specifiers[0] in self.sub_specifiers:
        return unit_registry.degree

    unit_converter = {
        specifiers_ss_para.SS_PARA_Y: unit_registry.siemens,
        specifiers_ss_para.SS_PARA_H: unit_registry.dimensionless,
        specifiers_ss_para.SS_PARA_S: unit_registry.dimensionless,
        specifiers.UNILATERAL_GAIN: unit_registry.dimensionless,
        specifiers.VOLTAGE: unit_registry.volt,
        specifiers.CAPACITANCE: unit_registry.farad,
        specifiers.FREQUENCY: unit_registry.hertz,
        specifiers.CURRENT: unit_registry.ampere,
        specifiers.CURRENT_DENSITY: unit_registry.ampere_per_square_meter,
        specifiers.TEMPERATURE: unit_registry.kelvin,
        specifiers.RESISTANCE: unit_registry.ohm,
        specifiers.POWER: unit_registry.watt,
        specifiers.TIME: unit_registry.second,
        specifiers.X: unit_registry.meter,
        specifiers.TRANSIT_FREQUENCY: unit_registry.hertz,
        specifiers.MAXIMUM_OSCILLATION_FREQUENCY: unit_registry.hertz,
        specifiers.TRANSIT_TIME: unit_registry.second,
        specifiers.TRANSCONDUCTANCE: unit_registry.siemens,
        specifiers.ENERGY: unit_registry.volt,
        specifiers.FIELD: unit_registry.volt / unit_registry.meter,
        specifiers.DC_CURRENT_AMPLIFICATION: unit_registry.dimensionless,
        specifiers.MAXIMUM_STABLE_GAIN: unit_registry.dimensionless,
        specifiers.NET_DOPING: 1 / unit_registry.meter / unit_registry.meter / unit_registry.meter,
        specifiers.ACCEPTORS: 1 / unit_registry.meter / unit_registry.meter / unit_registry.meter,
        specifiers.DONNORS: 1 / unit_registry.meter / unit_registry.meter / unit_registry.meter,
    }  # type: dict[SpecifierStr, pint.Unit]
    try:
        return unit_converter[self.specifier]
    except KeyError as err:
        raise IOError(
            "DMT -> Naming: no unit defined for specifier " + self.specifier + "."
        ) from err


SpecifierStr.get_pint_unit = get_pint_unit


def get_descriptor(self):
    """Can be generalized using the _specifiers class."""
    descriptor = {
        specifiers.CURRENT: "current",
        specifiers.CURRENT_DENSITY: "current density",
        specifiers.CAPACITANCE: "capacitance",
        specifiers.VOLTAGE: "voltage",
        specifiers.RESISTANCE: "resistance",
        specifiers.POWER: "power",
        specifiers.ENERGY: "energy",
    }
    return descriptor[self.specifier]


SpecifierStr.get_descriptor = get_descriptor


def to_tex(self, subscript="", superscript=""):
    """Return a Tex representation of this specifier. If subscript is not None the string in subscript will be appended. If superscript is not None, a superscript will be added.

    Parameters
    ----------
    subscript : str
        Subscript to add to the specifier's Tex representation
    superscript : str
        Superscript to add to the specifier's Tex representation

    Returns
    -------
    tex : str
            A Tex representation fo the specifier.
    """
    if self.specifier in specifiers_ss_para:
        nodes_temp = copy.deepcopy(self.nodes)

        for i_nodes, node in enumerate(nodes_temp):
            node = node.replace("B", "1")
            node = node.replace("C", "2")
            node = node.replace("G", "1")
            node = node.replace("D", "2")
            nodes_temp[i_nodes] = node

        if subscript == "":
            tex = (
                r"\underline{"
                + str(self.specifier)
                + r"}_{\mathrm{"
                + str("".join(nodes_temp))
                + r"}}"
            )
        else:
            tex = (
                r"\underline{"
                + str(self.specifier)
                + r"}_{\mathrm{"
                + str("".join(nodes_temp))
                + r","
                + subscript
                + r"}}"
            )

    # first catch special cases and add subscript
    elif self.specifier == specifiers.TRANSIT_FREQUENCY:
        tex = r"f_{\mathrm{T" + subscript + r"}}"
    elif self.specifier == specifiers.DC_CURRENT_AMPLIFICATION:
        tex = r"\beta_{\mathrm{DC}}"
    elif self.specifier == specifiers.MAXIMUM_OSCILLATION_FREQUENCY:
        tex = r"f_{\mathrm{max" + subscript + r"}}"
    elif self.specifier == specifiers.TRANSIT_TIME:
        tex = r"\tau_{\mathrm{f" + subscript + r"}}"
    elif self.specifier == specifiers.FREQUENCY:
        tex = r"f_{\mathrm{" + subscript + r"}}"
    elif self.specifier == specifiers.TRANSCONDUCTANCE:
        tex = r"g_{\mathrm{m," + subscript + r"}}"
    elif self.specifier == specifiers.TEMPERATURE:
        tex = r"T_{\mathrm{" + subscript + r"}}"
    elif self.specifier == specifiers.NET_DOPING:
        tex = r"N_{\mathrm{net}}"
    elif self.specifier == specifiers.ACCEPTORS:
        tex = r"N_{\mathrm{A}}"
    elif self.specifier == specifiers.DONNORS:
        tex = r"N_{\mathrm{D}}"
    elif self.specifier == specifiers.TIME:
        if subscript:
            tex = r"t_{\mathrm{" + subscript + r"}}"
        else:
            tex = r"t"
    else:  # general case
        if subscript:
            tex = (
                str(self.specifier)
                + r"_{\mathrm{"
                + str("".join(self.nodes))
                + r","
                + subscript
                + r"}}"
            )
        else:
            tex = str(self.specifier) + r"_{\mathrm{" + str("".join(self.nodes)) + r"}}"

    # add superscript
    if superscript:
        tex = tex + r"^{" + superscript + r"}"

    # add sub_specifiers that wrap the main specifier
    if sub_specifiers.REAL.sub_specifiers[0] in self.sub_specifiers:
        tex = r"\Re\{" + tex + r"\}"
    elif sub_specifiers.IMAG.sub_specifiers[0] in self.sub_specifiers:
        tex = r"\Im\{" + tex + r"\}"
    elif sub_specifiers.MAG.sub_specifiers[0] in self.sub_specifiers:
        tex = r"|" + tex + r"|"
    elif sub_specifiers.PHASE.sub_specifiers[0] in self.sub_specifiers:
        tex = r"\angle\{" + tex + r"\}"

    # add specifiers that are appended to the string
    for specifier in self.sub_specifiers:
        if "|" + specifier in [
            sub_specifiers.PERIMETER,
            sub_specifiers.AREA,
            sub_specifiers.CORNER,
            sub_specifiers.LENGTH,
            sub_specifiers.WIDTH,
        ]:
            tex = tex + "|" + specifier

    return tex


SpecifierStr.to_tex = to_tex


def set_col_name(specifier, *nodes, sub_specifiers=None):
    """Returns the valid DMT name for this column.

    Parameters
    ----------
    specifier : str
        Ideally a specifier from :mod:`~DMT.core.specifiers`
    *nodes : str, optional
        Nodes for the column. Like 'B' for base or 'B', 'E' for base-emitter
    sub_specifiers : str, {'', :py:const:`DMT.core.sub_specifiers.PERIMETER`, :py:const:`DMT.core.sub_specifiers.AREA`}

    Returns
    -------
    col : str
        If nodes are given: specifier + '_' + ''.join(nodes)
        Without nodes: specifier
    """

    return SpecifierStr(specifier, *nodes, sub_specifiers=sub_specifiers)


def get_nodes(string, nodes, fallback=None):
    """Return the nodes present in string in the correct order.

    Parameters
    ----------
    string          :  string
        String to be analyzed, e.g. 'V_BE'

    nodes           :  string
        Comma seperated list of possible nodes to be extracted.

    fallback        :  {string:string}
        Other nodes that may be present in string. If a key of this dict is found, the node name is mapped to its value.
        If value == '', the node is ignored.

    Returns
    -------
    relevant_nodes  :  list of string
        list of strings with the nodes in string.
    """
    # cast nodes from string to list of strings and order by string length.
    if isinstance(nodes, str):
        nodes = nodes.split(",")

    # go through string and find the nodes in the string and their position
    # code also accounts for nodes that occur multiple times, e.g. 'V' in 'V_BxB' where 'B' and 'Bx' are nodes
    nodes_ = copy.deepcopy(nodes)
    if fallback is not None:
        nodes_ = list(fallback.keys()) + nodes_
        nodes_ = set(nodes_)
        nodes_ = list(nodes_)

    nodes_.sort(key=len, reverse=True)  # order nodes by number of characters in node name
    pos_underscore = string.find("_")
    if pos_underscore == -1:  # if no underscore found, assume first letter is the specifier
        pos_underscore = 0
    string_ = string[pos_underscore + 1 :]  # throw away type specifier, i.e. 'C_'
    pos_sub_specifiers = string_.find("|")
    if pos_sub_specifiers != -1:  # sub_specifiers are optional
        string_ = string_[:pos_sub_specifiers]  # throw away sub_specifiers

    relevant_nodes_dict = {}
    for node in nodes_:
        while True:
            pos = string_.find(node)
            if pos != -1:
                relevant_nodes_dict[pos] = node
                string_ = string_.replace(node, "ä" * len(node), 1)
            else:
                break

    if string_.replace("ä", ""):
        # if string_ not empty, then the index is not only build of nodes -> do nothing!
        return ""

    relevant_nodes = list(relevant_nodes_dict.keys())  # for correct length
    for key, node in relevant_nodes_dict.items():
        relevant_nodes[key] = node

    # replace nodes from fallback dictionary with the desired node names
    if fallback is not None:
        for i, node in enumerate(relevant_nodes):
            if node in fallback.keys():
                if fallback[node] == "":
                    relevant_nodes[i] = node
                else:
                    relevant_nodes[i] = fallback[node]

    relevant_nodes = [node for node in relevant_nodes if node != ""]  # delete empty nodes

    return relevant_nodes


def get_sub_specifiers(string):
    """Returns the present sub_specifiers in string

    Parameters
    ----------
    string     : str
        The specifier of type str that is to be analyzed.

    Returns
    -------
    sub_specifiers : [str]
        A list of the sub_specifiers in specifier in the correct order.
    """
    relevant_subspecifiers = []
    for sub_specifier in SUB_SPECIFIERS_STR:
        if sub_specifier in string:
            relevant_subspecifiers.append(sub_specifier)
            string = string.replace(sub_specifier, "")  # delete the ones which are already found

    return relevant_subspecifiers


def get_specifier_from_string(string, nodes=None):
    """Try to create a SpecifierStr object from a given string.

    If method fails, string is returned as is.
    if a string is given, which is already a specifier string, it is also returned as is.

    Parameters
    ----------
    string : str
        The string that shall be converted to SpecifierStr
    nodes  : iterable(str), optional
        An iterable that contains the nodes that shall be looked for in string.
    """
    if isinstance(string, SpecifierStr):
        return string

    # find the correct specifier
    specifier_in_string = ""
    # specifiers_sorted = sorted(SPECIFIERS, key=lambda speci: len(speci), reverse=True) SPECIFIERS are always sorted now...
    for speci in specifiers:
        if string.startswith(speci):
            specifier_in_string = speci
            break

    # did we find the specifier?
    if str(specifier_in_string) == string:  # yes, and it is the whole string, nice
        return specifier_in_string
    elif not specifier_in_string:  # no :(
        return string

    # yes but there is more...

    # if nodes are given we can check them next
    nodes_in_string = []
    if nodes is not None:
        nodes_in_string = get_nodes(string, nodes)

    # sub specifiers?
    sub_specifiers_in_string = get_sub_specifiers(string)

    specifier = SpecifierStr(
        specifier_in_string, *nodes_in_string, sub_specifiers=sub_specifiers_in_string
    )

    # test if everything is inside the new specifier
    rest = string.replace(str(specifier_in_string), "")
    if nodes_in_string:
        rest = rest.replace("_" + "".join(nodes_in_string), "")
    if sub_specifiers_in_string:
        for sub_spec in sub_specifiers_in_string:
            rest = rest.replace("|" + sub_spec, "")

    if rest:
        return string
    else:
        return specifier


# a dict that holds natural scaling for a few specifiers. Convenient for Plotting.
natural_scales = {
    specifiers.VOLTAGE: 1,
    specifiers.MAXIMUM_STABLE_GAIN: 1,
    specifiers.CURRENT: 1e3,  # mA
    specifiers.CURRENT_DENSITY: 1e3 / (1e6 * 1e6),  # mA/um^2
    specifiers.MAXIMUM_OSCILLATION_FREQUENCY: 1e-9,
    specifiers.TRANSCONDUCTANCE: 1,
    specifiers.TRANSIT_FREQUENCY: 1e-9,
    specifiers.CAPACITANCE: 1e15,
    specifiers.SS_PARA_Y: 1e3,
    specifiers.DC_CURRENT_AMPLIFICATION: 1,
    specifiers.FREQUENCY: 1e-9,  # GHz
    specifiers.TEMPERATURE: 1,
    specifiers.X: 1e9,
    specifiers.POWER: 1e3,  # mW
    specifiers.RESISTANCE: 1,  # Ohm
    specifiers.ENERGY: 1,  # eV
    specifiers.UNILATERAL_GAIN: 1,
    specifiers.NET_DOPING: 1e-6,  # 1/cm^3
}
