""" Skywater modelcard

Author: Mario Krattenmacher | Mario.Krattenmacher@semimod.de
"""

# DMT
# Copyright (C) from 2022  SemiMod
# <https://gitlab.com/dmt-development/dmt-device>
#
# This file is part of DMT_core.
#
# DMT_other is free software for non-commercial use only. DMT_other is licensed
# under the DMT License.
#
# DMT_other is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# DMT_LICENSE.md in the root directory of DMT for more details.
#
# You should have received a copy of the DMT License along with this program.
from __future__ import annotations
import copy

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

from DMT.core import MCard, McParameter, unit_registry
from DMT.core.circuit import SGP_BJT, Circuit, CircuitElement, RESISTANCE, VOLTAGE

SEMVER_MCSKYWATER_CURRENT = VersionInfo(major=1, minor=0)


class McSkywater(MCard):
    """All model parameters of Skywater130 pdk models

    Parameters
    ----------
    load_model_from_path : str, optional
        Initialise the modelcard with the parameter from the given file path.
    version : float, optional
        Version of the model card. Default is 1.0
    pdk_path : str
        Path to the Skywater pdk: ".../sky130.lib.spice"
    pdk_corner : str
        Corner for this modelcard ("tt" ...)
    """

    def __init__(
        self,
        load_model_from_path=None,
        version=1.0,
        default_circuit="common_source",
        __McSkywater__=SEMVER_MCSKYWATER_CURRENT,
        nodes_list=("D", "G", "S", "B"),
        default_subckt_name="X1",
        default_module_name="sky130_fd_pr__nfet",
        possible_groups=None,
        vae_module=None,
        **kwargs,
    ):
        if possible_groups is None:
            possible_groups = {"geo": "Geometrie"}

        super().__init__(
            nodes_list,
            default_subckt_name,
            default_module_name,
            version=version,
            possible_groups=possible_groups,
            vae_module=vae_module,
            **kwargs,
        )

        if not isinstance(__McSkywater__, VersionInfo):
            try:
                __McSkywater__ = VersionInfo.parse(__McSkywater__)
            except TypeError:
                __McSkywater__ = VersionInfo.parse(f"{__McSkywater__:1.1f}.0")

        if __McSkywater__ != SEMVER_MCSKYWATER_CURRENT:
            raise IOError("DMT->McSkywater: The given version of __McSkywater__ is unknown!")

        if self.va_codes:
            raise IOError("The Skywater mcard has no VA-Code!")

        self.add(McParameter("l", value=1, unit=unit_registry.metre, group="geo"))
        self.add(McParameter("w", value=1, unit=unit_registry.metre, group="geo"))
        self.add(McParameter("nf", value=1, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("ad", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("as", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("pd", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("ps", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("nrd", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("nrs", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("sa", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("sb", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("sd", value=0, unit=unit_registry.dimensionless, group="geo"))
        self.add(McParameter("mult", value=1, unit=unit_registry.dimensionless, group="geo"))

        if load_model_from_path is not None:
            super().load_model_parameters(
                load_model_from_path, force=False
            )  # False: there may be invalid parameters in the file

        self.default_circuit = default_circuit

    def info_json(self, **kwargs):
        """Returns a dict with serializeable content for the json file to create. Add the info about the concrete subclass to create here!"""
        info_dict = super(McSkywater, self).info_json(**kwargs)
        info_dict["__McSkywater__"] = str(
            SEMVER_MCSKYWATER_CURRENT
        )  # make versions, so we can introduce compatibility here!
        info_dict["default_circuit"] = self.default_circuit

        return info_dict

    def get_circuit(self, use_build_in=False, topology=None, **kwargs) -> Circuit:
        """Here the modelcard defines it's default simulation circuit.

        Parameters
        ----------
        use_build_in : {False, True}, optional
            Creates a circuit for the modelcard using the build-in model
        topology : optional
            If a model has multiple standard circuits, use the topology to differentiate between them..
        """
        if use_build_in:
            mcard = self.get_build_in()
        else:
            mcard = self

        if topology is None:
            topology = self.default_circuit

        if topology == "common_source":
            return Circuit(
                [
                    CircuitElement(
                        self.default_module_name,
                        "x1",
                        ["n_D", "n_G", "n_S", "n_B"],
                        parameters=mcard,
                    ),
                    CircuitElement(RESISTANCE, "R_D", ["n_D", "n_DX"], parameters=[("R", "1")]),
                    CircuitElement(
                        VOLTAGE, "V_D", ["n_DX", "0"], parameters=[("Vdc", "V_D"), ("Vac", "1")]
                    ),
                    CircuitElement(
                        VOLTAGE, "V_G", ["n_GX", "0"], parameters=[("Vdc", "V_G"), ("Vac", "1")]
                    ),
                    CircuitElement(RESISTANCE, "R_G", ["n_GX", "n_G"], parameters=[("R", "1")]),
                    CircuitElement(RESISTANCE, "R_S", ["n_S", "0"], parameters=[("R", "0")]),
                    CircuitElement(RESISTANCE, "R_B", ["n_B", "0"], parameters=[("R", "0")]),
                ]
            )
        else:
            raise NotImplementedError(f"DMT.McSkywater: unknown topology {topology}")

    def get_build_in(self):
        """Return the parameters embedded in a build-in model (no Va code and correct module name etc)"""
        return copy.deepcopy(self)

    def get_clean_modelcard(self):
        """Returns all parameters which are part of SGP and adds correct units"""
        default_mcard = McSkywater(
            version=self.version,
            default_circuit=self.default_circuit,
            pdk_path=self.pdk_path,
            pdk_corner=self.pdk_corner,
        )
        for para in self:
            if para in default_mcard:
                default_mcard.set(para)
            else:
                print("Warning: parameter " + para.name + " was removed by clean_mcard.")

        return default_mcard
