""" DMT description of a circuit.

Must be used to describe a circuit and then passed to a circuit simulator dut.

Later on this can be extended to allow (pseudo-)simulations directly inside DMT.

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
import warnings
from typing import Callable, Iterable, Optional, Union, List, Tuple
from DMT.core import MCard, McParameterCollection


RESISTANCE = "R"
""" Indicates a resistance in a circuit. """
CAPACITANCE = "C"
""" Indicates a capacitance in a circuit. """
INDUCTANCE = "L"
""" Indicates a inductance in a circuit. """
CURRENT = "I_Source"
""" Indicates a current source in a circuit. """
VOLTAGE = "V_Source"
""" Indicates a voltage source in a circuit. """
SHORT = "Short"
""" Indicates a voltage source in a circuit. """
HICUML2_HBT = "BHT"
""" Indicates a bipolar transistor modeled with HICUM/L2 in a circuit. """
HICUML0_HBT = "BHT0"
""" Indicates a bipolar transistor modeled with HICUM/L0 in a circuit. """
SGP_BJT = "BJT"
""" Indicates a bipolar transistor modeled with SGP in a circuit. """
DIODE = "diode"
""" Indicates a diode in a circuit. """


class CircuitElement(object):
    """Class that is used to describe netlist elements such as resistors, capacitors or inductors.

    The possible CircuitElements define the DMT netlist format. Circuit simulators need to convert the DMT netlist format to their respective one.
    This class has a special emphasis on good error messages and typesetting.

    Possible element types:

    * :py:const:`RESISTANCE`
    * :py:const:`CAPACITANCE`Sequence
    * :py:const:`SHORT`
    * va_module -> could be a transistor

    Parameters
    ----------
    element_type
        Element type, for example: 'R' for resistor. possible values: 'V_Source', 'I_Source', 'R', 'C', 'L', 'Short' ,'va_module'
    name
        Element name, for example: 'R1' for resistor 1. Names should be unique within their netlist.
    contact_nodes
        Contact nodes of the element, for example: ('n__1', 'n__2')
    parameters
        Parameters of the element, for example: [('R', '1k')]

    Attributes
    ----------
    element_type
        Element type, for example: 'R' for resistor
    name
        Element name, for example: 'R1' for resistor 1
    contact_nodes
        Contact nodes of the element, for example: ('n__1', 'n__2')
    parameters
        Parameters of the element, for example: [('R', '1k')]
    """

    possible_types = [
        VOLTAGE,
        CURRENT,
        RESISTANCE,
        CAPACITANCE,
        INDUCTANCE,
        SHORT,
        HICUML2_HBT,
        HICUML0_HBT,
        SGP_BJT,
        DIODE,
        "va_module",
        "pdk",
        '"hbt_n1s"',
        "n1s_sgp",
        "hbt_n1s",
        "hbt_n2s",
        '"hbt_n2s"',
        "hbt_n3s",
        '"npn_hicum"',
        '"npn_hs"',
        "npn_hs",
        "TSC250_Models_lib_TSC_250nm_Agilent_v1p0_schematic",
        '"TSC250_Models_lib_TSC_250nm_Agilent_v1p0_schematic"',
    ]

    def __init__(
        self,
        element_type: str,
        name: str,
        contact_nodes: Iterable[str],
        parameters: Optional[Union[List[Tuple[str, str]], MCard, McParameterCollection]] = None,
        method: Optional[Callable] = None,
    ):
        if isinstance(parameters, MCard) or isinstance(parameters, McParameterCollection):
            CircuitElement.possible_types.append(parameters.default_module_name)  # type: ignore

        if isinstance(element_type, str):
            if element_type in self.possible_types:
                self.element_type = element_type

            else:
                raise IOError(
                    "DMT -> Circuit: Element Type "
                    + str(element_type)
                    + " is unknown. \n Possible types: "
                    + str(CircuitElement.possible_types)
                )

        else:
            raise TypeError("DMT -> element_type: element_type needs to be a string.")

        if isinstance(name, str):
            self.name = name
        else:
            raise TypeError(
                "The element name has to be a string! Given was "
                + str(name)
                + " of type "
                + type(name)
            )

        if isinstance(contact_nodes, (tuple, list)):
            for i_node, node in enumerate(contact_nodes):
                if not isinstance(node, str):
                    raise TypeError(
                        "The element contact nodes have to be a tuple of strings! Given was a tuple of different elements. The node "
                        + str(i_node)
                        + " had the type "
                        + type(node)
                    )

            self.contact_nodes = contact_nodes

        else:
            raise TypeError(
                "The element contact nodes have to be a tuple of strings! Given was "
                + str(contact_nodes)  # type: ignore
                + " of type "
                + type(contact_nodes)
            )

        if parameters is None:
            pass

        elif isinstance(parameters, list):
            for i_parameter, parameter in enumerate(parameters):
                if isinstance(parameter, tuple):
                    for parameter_part in parameter:
                        if not isinstance(parameter_part, str):
                            raise TypeError(
                                "The parameters have to be a list of tuple of strings! Given was a list of tuples with at least one element of "
                                + type(parameter_part)
                                + " in the tuple "
                                + str(i_parameter)
                            )
                else:
                    raise TypeError(
                        "The parameters have to be a list of tuple of strings! Given was a list with at least one element of "
                        + type(parameter)
                        + " at position "
                        + str(i_parameter)
                    )

        elif isinstance(parameters, MCard) or isinstance(parameters, McParameterCollection):
            # Allow model cards!
            pass

        else:
            raise TypeError(
                "The parameters have to be a list of tuple of strings or a modelcard! Given was a "
                + type(parameters)
            )

        self.parameters = parameters

        if method is not None:
            warnings.warn(
                "method will be deprecated in future DMT releases. This feature is not needed anymore since VAE is mature.",
                category=DeprecationWarning,
            )
        self.method = method

    def __repr__(self):
        str_nodes = ",".join(self.contact_nodes)
        return f"DMT.CircuitElement:{self.name:s} model {self.element_type:s} nodes {str_nodes:s}"


class Circuit(object):
    """Circuit description as a list of :class:`CircuitElement`

    Parameters
    ----------
    circuit_elements
        Either directly the netlist elements as a list of CircuitElements or strings (for equations)

    Attributes
    ----------
    netlist
        Either directly the netlist elements as a list of CircuitElements or strings (for equations)
    """

    def __init__(self, circuit_elements: List[Union[str, CircuitElement]]):
        if isinstance(circuit_elements, str):
            raise NotImplementedError(
                "The default circuit has been moved into the corresponding module. Access the circuit from there!"
            )

        for i_element, element in enumerate(circuit_elements):
            if not isinstance(element, (CircuitElement, str)):
                raise TypeError(
                    "The netlist has to be a list of CircuitElement or str! At position "
                    + str(i_element)
                    + " is a entry of type "
                    + type(element)
                )

        self.netlist = circuit_elements
