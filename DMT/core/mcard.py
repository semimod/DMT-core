""" Base class to handle verilog-a modelcards.

Author: Mario Krattenmacher | Mario.Krattenmacher@semimod.de
Author: Markus Müller       | Markus.Mueller3@tu-dresden.de
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
from __future__ import annotations
import numpy as np
import re
import os
import pickle
import logging
import scipy.io as sciio
import ast
import operator
import warnings
from pathlib import Path
from typing import Union, Optional
from types import ModuleType

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

import verilogae

from DMT.core import unit_registry, VAFile
from DMT.core.mc_parameter import McParameterCollection, McParameter


unit_converter = {
    "s": unit_registry.second,
    "sec": unit_registry.second,
    "A": unit_registry.ampere,
    "A^2s": unit_registry.ampere * unit_registry.ampere * unit_registry.second,
    "V": unit_registry.volt,
    "1/V": 1 / unit_registry.volt,
    "K": unit_registry.kelvin,
    "1/K": 1 / unit_registry.kelvin,
    "K^-1": 1 / unit_registry.kelvin,
    "C": unit_registry.celsius,
    "ohm": unit_registry.ohm,
    "Ohm": unit_registry.ohm,
    "F": unit_registry.farad,
    "Coul": unit_registry.coulomb,
    "K/W": unit_registry.kelvin / unit_registry.watt,
    "J/W": unit_registry.joule / unit_registry.watt,
    "V/K": unit_registry.volt / unit_registry.kelvin,
    "1/K^2": 1 / unit_registry.kelvin / unit_registry.kelvin,
    "Ws/K": unit_registry.watt * unit_registry.second / unit_registry.kelvin,
    "M^(1-AF)": unit_registry.dimensionless,
    "m": unit_registry.meter,
    "m^2": unit_registry.meter * unit_registry.meter,
    "Am^-1": unit_registry.ampere / unit_registry.meter,
    "Am^-2": unit_registry.ampere / unit_registry.meter / unit_registry.meter,
    "Am^-3": unit_registry.ampere / unit_registry.meter / unit_registry.meter / unit_registry.meter,
    "AV^-3": unit_registry.ampere / unit_registry.volt / unit_registry.volt / unit_registry.volt,
    "AV^-3m": unit_registry.ampere
    / unit_registry.volt
    / unit_registry.volt
    / unit_registry.volt
    * unit_registry.meter,
    "Fm^-1": unit_registry.farad / unit_registry.meter,
    "Fm^-2": unit_registry.farad / unit_registry.meter / unit_registry.meter,
    "cm^-3": 1 / unit_registry.meter / unit_registry.meter / unit_registry.meter,  # mhm centi ?
    "Vm^-1": unit_registry.volt / unit_registry.meter,
    "VA^-1m": unit_registry.volt / unit_registry.ampere * unit_registry.meter,
    "VA^-1m^2": unit_registry.volt
    / unit_registry.ampere
    * unit_registry.meter
    * unit_registry.meter,
    "": unit_registry.dimensionless,
}

SEMVER_MCARD_CURRENT = VersionInfo(major=2, minor=1)


class MCard(McParameterCollection):
    """DMT class that implements attributes and methods that are common between all ModelCards such as HICUM and BSIM.

    Parameters
    ----------
    nodes_list        :  tuple(str)
        Port list for this model.
    default_subckt_name  :  str
        Default name for the subcircuit to be included.
    default_module_name  :  str
        Default name of the module of the VA-File for this device.
    version              :  float
        Version of the model.
    va_file : str, optional
        Path to a Verilog-AMS file
    circuit : {None,:class:`~DMT.core.circuit.Circuit`}
        Circuit to simulate this model card.
    mod_name : str
        Name of the Model, this is used by EvalTradica, so it must fit there, e.g. 'HICUM'
    level_num : str
        Level of the Model, this is used by EvalTradica, so it must fit there, e.g. '2'

    Attributes
    ----------
    nodes_list : tuple(str)
        Port list for this model.
    circuit : {None,:class:`~DMT.core.circuit.Circuit`}
        Circuit to simulate this model card.
    default_subckt_name : str
        Default name for the subcircuit to be included.
    default_module_name : str
        Default name of the module of the VA-File for this device.
    version : float
        Version of the model.
    va_file : str
        Path to a Verilog-AMS file *deprecated*
    va_codes : {os.Pathlike: str}
        Dictionary of relative paths and codes -> full VA code structure.
    ignore_checksum: bool, optional
        If True, the checksum of the save modelcard json is ignored, defaults to False.

    """

    def __init__(
        self,
        nodes_list: list[str],
        default_subckt_name: str,
        default_module_name: str,
        version: Union[str, float] = "-",
        va_file: Optional[Union[str, os.PathLike]] = None,
        va_codes=None,
        vae_module=None,
        directory_va_file: Optional[Union[str, os.PathLike]] = None,
        __MCard__=SEMVER_MCARD_CURRENT,
        ignore_checksum: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if not isinstance(__MCard__, VersionInfo):
            try:
                __MCard__ = VersionInfo.parse(__MCard__)
            except TypeError:
                __MCard__ = VersionInfo.parse(f"{__MCard__:1.1f}.0")

        if __MCard__ == VersionInfo(major=1, minor=0):
            # try to obtain the VA-Code
            if (
                va_file is not None
                and not isinstance(va_file, Path)
                and not Path(va_file).is_file()
            ):
                # in Version 1 the code was not part of the MCard. Try to find it...
                print(
                    "The loaded MCard was from Version 1. The VA-Code was not saved inside of the json-file.  "
                )
                if directory_va_file is not None:
                    print("DMT tries to find it. The search location is " + str(directory_va_file))
                    if not isinstance(directory_va_file, Path):
                        directory_va_file = Path(directory_va_file)

                    if (directory_va_file / va_file).is_file():
                        print("File found in the given folder and will be used!")
                        va_file = directory_va_file / va_file
                    else:
                        print("File not found in the folder. No VA-Code is set by core!")
                        va_file = None  # delete file name to escape error while try to load
                else:
                    print("No directory for the va-file is set. No VA-Code is set by core!")
                    print(
                        "To set the directory use: MCard.load_json(path_to_json, directory_va_file=path_to_directory)"
                    )
                    va_file = None  # delete file name to escape error while try to load

            if vae_module is not None:
                raise NotImplementedError

        elif __MCard__ == VersionInfo(major=2, minor=0):
            pass  # nothing to do here?!
        elif __MCard__ != SEMVER_MCARD_CURRENT:
            raise NotImplementedError("DMT->MCard: Unknown version of MCard to create!")

        self.nodes_list = nodes_list
        self.default_subckt_name = default_subckt_name
        self.default_module_name = default_module_name
        self.version = version

        self._va_codes = None
        if va_codes is not None:
            if isinstance(va_codes, dict):
                self._va_codes = VAFile.import_dict(va_codes, ignore_checksum=ignore_checksum)
            else:
                self._va_codes = va_codes
        elif va_file is not None:
            self.set_va_codes(va_file)

        if self._va_codes:
            self.update_from_vae()

    @property
    def va_codes(self) -> Union[VAFile, None]:
        """Return the attribute directly

        Returns
        -------
        VAFile

        """
        return self._va_codes

    # @va_codes.setter
    # def va_codes(self, va_codes_new: VAFile):
    #     """Set the va_codes

    #     Parameters
    #     ----------
    #     va_codes_new : VAFile
    #         New rel paths with codes
    #     """
    #     self._va_codes = va_codes_new

    def set_va_codes(
        self, path_to_main_code: Union[os.PathLike, str], version: Union[str, float] = None
    ):
        """Sets self._va_codes by extracting all included files from the main file down the include tree.

        Parameters
        ----------
        path_to_main_code : Union[os.PathLike, str]
            Relative or Absolute path to the main Verilog-AMS file
        version : Union[str, float], float
            If the given code has a different model version as currently set.

        Raises
        ------
        NotImplementedError
            If a file is included via absolute path.
        """
        if not isinstance(path_to_main_code, Path):
            path_to_main_code = Path(path_to_main_code)

        self._va_codes = VAFile(path_to_main_code.name)
        self._va_codes.read_structure(path_to_main_code.parent)

        if version is not None:
            self.version = version

    def get_verilogae_model(self) -> ModuleType:
        """Returns the Verilogae Model for this modelcard

        Returns
        -------
        ModuleType
            The Veriloae-module

        Raises
        ------
        FileNotFoundError
            Raised if no VA-Code is set.
        """
        if self.va_codes is None:
            raise FileNotFoundError("No VA-Code set for this MCard!")
        return verilogae.load(self.va_codes.root_vfs, vfs=self.va_codes.vfs)  # type: ignore

    def update_from_vae(self, remove_old_parameters=False):
        """
        Updates the modelcard with information such as parameter boundries and default values, nodes, modules and op vars
        obtained from the Verilog-A source code using `VerilogAE <https://dspom.gitlab.io/verilogae/>`__.

        Parameters
        ----------
        remove_old_parameters : bool, optional
            Deletes parameters which are not part of the VA-Code, by default False
        """
        vae_module = self.get_verilogae_model()
        paras_new = []
        # Updated parameter properties
        for para_name, para_properties in vae_module.modelcard.items():
            try:
                # para = next(para for para in self._paras if para.name == para_name)
                para = self.get(para_name)
                self.remove(para_name)
                ty = type(para_properties.default)

                if para.min > para_properties.min:
                    para.min = para_properties.min
                    para.inc_min = para_properties.min_inclusive  # type: ignore

                if para.max < para_properties.max:
                    para.max = para_properties.max
                    para.inc_max = para_properties.max_inclusive  # type: ignore

                para.unit = unit_converter[para_properties.unit]  # type: ignore
                para.description = para_properties.description  # type: ignore
                para.group = para_properties.group  # type: ignore
                para.val_type = ty  # type: ignore
            except KeyError:
                para = McParameter(
                    para_name,
                    value=para_properties.default,
                    minval=para_properties.min,
                    maxval=para_properties.max,
                    value_type=type(para_properties.default),
                    inc_min=para_properties.min_inclusive,
                    inc_max=para_properties.max_inclusive,
                    exclude=None,  # ? really needed
                    group=para_properties.group,
                    unit=unit_converter[para_properties.unit],
                    description=para_properties.description,
                )
            paras_new.append(para)

        if remove_old_parameters:
            self._paras = []  # remove the old parameters fast...

        for para in paras_new:
            self.add(para, update=False)

        self.update_values()

        self.default_module_name = vae_module.module_name
        self.nodes_list = vae_module.nodes
        # self.version = ?? -> can be set in the submodules according to some model specific stuff

    def read_va_file_boundaries(self, remove_old_parameters=True):
        """Reads the parameter boundaries and possible OPvars from a Verilog-AMS-File

        Needs only to be done once per VA-File, as the boundaries then can
        be saved/loaded from a json (see dump_json)

        Parameters
        ----------
        remove_old_parameters : {True, False}, optional
            If False, parameters which are not found in the VA-File are not removed.
        """
        print(
            "DMT.MCard: Reading from VA-File using this Method is deprecated. Use update_from_vae!"
        )
        paras_new = []

        if self.va_codes is None:
            return

        for va_file, va_code in self.va_codes.iter_codes():
            logging.info(
                "Reading parameter boundaries and operation point variables from %s", va_file
            )

            lines = va_code.code.split("\n")
            group = None
            for line in lines:
                if re.match(r"\s*module", line):
                    # module hic0_full (c,b,e,s,tnode);
                    # module hicumL2va (c,b,e,s,tnode);
                    mo_module_name = re.search(r"module\s(\S+?)\s*\((.+?)\)", line)
                    self.default_module_name = mo_module_name.group(1)
                    self.nodes_list = mo_module_name.group(2).split(",")
                elif line.startswith(r"//"):
                    # only commented lines
                    comment = line.replace("//", "").strip()
                    try:
                        group = self.possible_groups[comment]
                        dummy = 1
                    except KeyError:
                        group = None

                elif re.search(r"parameter", line):
                    # found a parameter line
                    mo_parameter = re.search(
                        r"parameter\s+(real|integer)\s+(\w+)\s*=\s*(\S+)", line
                    )

                    if mo_parameter is None:
                        continue

                    parameter_type = mo_parameter.group(1)
                    parameter_name = mo_parameter.group(2)
                    parameter_default = mo_parameter.group(3)

                    parameter_default = parameter_default.replace(";", "")
                    if parameter_type == "integer":
                        parameter_type = int
                        parameter_default = int(parameter_default)
                    elif parameter_type == "real":
                        parameter_type = float
                        if parameter_default == "`INF":
                            parameter_default = np.inf
                        else:
                            parameter_default = float(parameter_default)
                    else:
                        raise NotImplementedError("Type unknown")

                    tuple_parameter_boundaries = re.findall(r"from\s+(\S+)", line)
                    if tuple_parameter_boundaries:
                        parameter_boundaries = tuple_parameter_boundaries[0].split(":")
                        # at the moment only 1st group is used, if VA-Code with
                        # parameter real a = 1 from 0:10 from 20:30
                        # is analyzed this needs to be extended!

                        if "(" in parameter_boundaries[0]:
                            parameter_include_min = False
                        else:  # else should be "[", not checked now
                            parameter_include_min = True

                        if ")" in parameter_boundaries[1]:
                            parameter_include_max = False
                        else:  # else should be "]", not checked now
                            parameter_include_max = True

                        if parameter_type == int:
                            parameter_min = int(
                                re.search(r"([-.0-9e]+)", parameter_boundaries[0]).group(1)
                            )
                            parameter_max = int(
                                re.search(r"([-.0-9e]+)", parameter_boundaries[1]).group(1)
                            )
                        elif parameter_type == float:
                            try:
                                parameter_min = float(
                                    re.search(r"([-.0-9e]+)", parameter_boundaries[0]).group(1)
                                )
                            except (AttributeError, ValueError):
                                if "INF" in parameter_boundaries[0].upper():
                                    parameter_min = -np.inf
                                else:
                                    raise
                            try:
                                parameter_max = float(
                                    re.search(r"([-.0-9e]+)", parameter_boundaries[1]).group(1)
                                )
                            except (AttributeError, ValueError):
                                if "INF" in parameter_boundaries[1].upper():
                                    parameter_max = np.inf
                                else:
                                    raise
                            # if more are added also add them to the validity checker!!
                        else:  # is impossible, only possibilities are real or integer (see 1st RegExp)
                            raise NotImplementedError(
                                "This parameter type is not implemented: " + str(parameter_type)
                            )
                    else:
                        if parameter_type == float:
                            parameter_min = -np.inf
                            parameter_max = np.inf
                        elif parameter_type == int:  # inf not possible in integer...
                            parameter_min = np.iinfo(int).min
                            parameter_max = np.iinfo(int).max
                        else:
                            raise NotImplementedError()
                        parameter_include_min = True
                        parameter_include_max = True

                    tuple_parameter_excludes = re.findall(r"exclude\s+([0-9:.]+)", line)
                    # at the moment only 1st group is used, if VA-Code with
                    # parameter integer a = 1 from -1:2 exclude 0 exclude 1
                    # parameter integer a = 1 from -1:2 exclude 0:1
                    # is analyzed this needs to be extended!

                    search_unit = re.search(r"unit\s*=\s*\"(.+?)\"", line)
                    if search_unit:
                        # convert from VA to pint...
                        unit = unit_converter[search_unit.group(1)]
                    else:
                        unit = unit_registry.dimensionless

                    search_desc = re.search(
                        r"(desc|info)\s*=\s*\"(.+?)\"", line
                    )  # 'desc' is VA standard, 'info' is ADMS standard
                    if search_desc:
                        desc = search_desc.group(2)
                    else:
                        desc = None

                    try:
                        para = self.get(parameter_name)
                        self.remove(parameter_name)
                    except KeyError:
                        para = McParameter(
                            parameter_name, value=parameter_default, value_type=parameter_type
                        )

                    para.val_type = parameter_type
                    para.max = parameter_max
                    para.min = parameter_min
                    para.inc_max = parameter_include_max
                    para.inc_min = parameter_include_min
                    para.exclude = None
                    #     warnings.warn('The group of the parameter {:s} is unknown from the VA-File'.format(para))
                    # else:
                    if group is not None:
                        para.group = group

                    if desc is not None:
                        para.description = desc

                    if unit is not None:
                        para.unit = unit
                    if tuple_parameter_excludes:  # just assume it is the type parameter...
                        para.exclude = [
                            parameter_type(exclude) for exclude in tuple_parameter_excludes
                        ]

                    paras_new.append(para)
                    # if para in self:
                    #     self.set(para)
                    # else:
                    #     self.add(para)

        if remove_old_parameters:
            self._paras = []  # remove the old parameters fast...

        for para in paras_new:
            self.add(para, update=False)

        self.update_values()

    def info_json(self, save_va_code=True, compress_va_code=False, **kwargs):
        """Returns a dict with serializeable content for the json file to create. Add the info about the concrete subclass to create here!

        Parameters
        ----------
        save_va_code : {True, False}, optional
            If False, the va_codes are not saved...
        compress_va_code : {False, True}, optional
            If True, the codes are saved using zlib compression and a checksum. See:
            https://code.activestate.com/recipes/355486-compress-data-to-printable-ascii-data/
        """
        info_dict = super(MCard, self).info_json(**kwargs)

        info_dict["__MCard__"] = str(
            SEMVER_MCARD_CURRENT
        )  # make versions, so we can introduce compatibility here!

        info_dict["nodes_list"] = self.nodes_list
        info_dict["default_subckt_name"] = self.default_subckt_name
        info_dict["default_module_name"] = self.default_module_name
        info_dict["version"] = self.version

        if save_va_code and self.va_codes is not None:
            info_dict["va_codes"] = self.va_codes.export_dict(compressed_code=compress_va_code)

        return info_dict

    @classmethod
    def load_json(
        cls,
        file_path: Union[str, Path],
        directory_va_file: Union[str, Path, None] = None,
        ignore_checksum: bool = False,
    ) -> MCard:
        """Load json file

        Just for type hints etc..

        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the json.
        directory_va_file : Union[str, Path, None], optional
            If a relative path to a va_file is set in the modelcard, pass the absolute path to the start folder here, by default None.
            This can be used to load old json modelcards from before saving the full code with the parameters.
        ignore_checksum : bool, optional
            When the code is saved compressed, a checksum is saved with it. If you want to ignore the checksum set this to true, by default False

        Returns
        -------
        MCard
            Loaded modelcard
        """

        return super().load_json(file_path, directory_va_file=directory_va_file, ignore_checksum=ignore_checksum)  # type: ignore

    def get_circuit(self, use_build_in=False, topology=None, **kwargs):
        """Here the modelcard defines it's default simulation circuit.

        Parameters
        ----------
        use_build_in : {False, True}, optional
            Creates a circtui the modelcard using the build-in model
        topology : optional
            If a model has multiple standard circuits, use the topology to differentiate between them..
        """

        raise NotImplementedError("The default modelcard has no circuit :(.")

    def get_build_in(self):
        """Return the parameters embedded in a build-in model (no Va code and correct module name etc)"""
        raise NotImplementedError("The submodels have to implement the build-in parameters")

    def print_to_file(
        self, path_to_file, file_mode="w", subckt_name=None, module_name=None, line_break="\n"
    ):
        """Generates a spectre .lib file which can be included into an netlist.

        Existence of lib file is not checked before writing!
        Name of File: path_to_file + ".lib"

        Parameters
        ----------
        path_to_file : str or os.Pathlike
            Absolute or relative path with file name to the file to generate.
        file_mode : str, optional
            Mode to open the file. Can be used to append :).
        subckt_name : str
            Name of the subcircuit to be included
        module_name : str
            Name of the module from the corresponding VA-File
        line_break : str, optional
            Is added after each parameter, is used as line breaks.
        """
        if subckt_name is None:
            subckt_name = self.default_subckt_name
        if module_name is None:
            module_name = self.default_module_name

        if isinstance(path_to_file, Path):
            path_to_file = path_to_file.with_suffix(".lib")
        else:
            path_to_file = Path(path_to_file + ".lib")

        str_modelcard = "simulator lang = spectre\n"

        str_modelcard += f"subckt {subckt_name:s} (" + " ".join(self.nodes_list) + ")\n"
        str_modelcard += " Q1 (" + " ".join(self.nodes_list) + f") {module_name:s} ({line_break:s}"

        for para in self:
            str_modelcard += f"  {para:<12s} = {para:10.3e} {line_break:s}"

        str_modelcard += ")\n"
        str_modelcard += f"ends {subckt_name:s} \n"

        with path_to_file.open(file_mode) as fp:
            fp.write(str_modelcard)

    def __eq__(self, other):
        """Allows comparing 2 model cards using mc1 == mc2

        mc1 != mc2 is included per default using python3:
        https://docs.python.org/3/reference/datamodel.html#object.__ne__

        """
        if isinstance(other, self.__class__):
            if self.version == other.version:
                # class, version and parameters equal is enough in most cases!
                return self.eq_paras(other)
            else:
                return False

        return NotImplemented

    def load_model(self, path_to_file, force=True):
        """deprecated method, will be removed soon. See load_model_parameters for documentation."""
        warnings.warn(
            "load_model is deprecated and will be renamed in future major releases to load_model_parameters.\n",
            category=DeprecationWarning,
        )
        self.load_model_parameters(path_to_file, force=force)

    def load_model_parameters(self, path_to_file, force=True):
        """Loads the model from a file

        The loading method is determined according to the file ending (last 3 characters!!)
        Possible is "mcp" (see save_model), "txt" or "mat" (planned)

        Parameters
        ----------
        path_to_file : str
            Filename (with ending!) including a relative or absolute path
        force : boolean, optional
            If True, values are force set. Set false if bounds from VA-File are used...
        """
        if not isinstance(path_to_file, Path):
            path_to_file = Path(path_to_file)

        modcard = None

        # Loading protocol depends on file ending
        file_ending = path_to_file.suffix
        if file_ending == ".mcp" or file_ending == ".mcard":
            logging.info("Loading model parameters from pickled model card: %s", str(path_to_file))

            with path_to_file.open("rb") as myfile:
                modcard = pickle.load(myfile)

        elif file_ending == ".mat":
            logging.info("Loading model parameters from mat-File: %s", str(path_to_file))

            modcard = sciio.loadmat(str(path_to_file))
            for key, value in modcard.items():
                if not key.startswith("__"):
                    modcard[key] = np.ndarray.item(value)

        elif file_ending == ".txt":
            logging.info("Loading model parameters from a txt-File: %s", str(path_to_file))

            modcard = []

            str_modelcard = path_to_file.read_text()

            # split it
            re_object = re.findall(r"[a-zA-Z0-9]+\s*=\s*\S+", str_modelcard)

            for param_value in re_object:
                param_value = param_value.split("=")
                modcard.append((param_value.strip(), float(param_value[1].strip())))
        elif file_ending == ".lib" or file_ending == "":
            logging.info("Loading model parameters from a TRADICA lib-File: %s", str(path_to_file))

            modcard = []
            str_lib = path_to_file.read_text()

            # get the model part
            search_parameters = re.search(
                r"(model|subckt)(.*)(ends|)", str_lib, flags=re.DOTALL | re.IGNORECASE
            )
            if search_parameters is not None:
                str_lib = search_parameters.group(2)
            # else there are only parameters

            # split it
            # re_object = re.findall(r"([a-zA-Z0-9]+\s*=\s*[a-zA-Z0-9.+()-]+\s*)", str_lib) # new and better: https://regex101.com/r/Bwvc69/1
            # re_object = re.findall(r"([a-zA-Z0-9]+)\s*=\s*[\(|]\s*(\S+)\s*[\|]", str_lib) # even newer and better https://regex101.com/r/DsZP2J/1
            re_object = re.findall(
                r"([a-zA-Z0-9]+)\s*=\s*((\(|)\s*\S+\s*(\)|))", str_lib
            )  # even newer and better https://regex101.com/r/DsZP2J/2

            for param_name, param_value, _bracket_start, _bracket_close in re_object:
                name = param_name.strip().lower()
                if name == "level" or name == "version" or name == "lang":
                    continue
                value = param_value.strip()
                if (
                    ")" in value and "(" not in value
                ):  # cuts out an probable single closing bracket.
                    value = value.replace(")", "").strip()
                if "***" in value:  # appears sometimes in TRADICA files
                    continue

                value = Calculator.evaluate(value)  # allow calculations in parameter value
                if value is None:
                    raise IOError(
                        "Error while reading lib-file! Could not evaluate the parameter value '"
                        + param_value[1].strip()
                        + "' of the parameter "
                        + name
                        + "!"
                    )
                modcard.append((name, value))
        else:
            raise IOError(
                "Was not able to load parameters from given file!\nGiven was: " + str(path_to_file)
            )

        if modcard is None:
            raise IOError("Loading from file did not work!")

        if isinstance(modcard, list):
            for (parameter_name, parameter_value) in modcard:
                try:
                    # do not reset the limits if parameter is already in modelcard
                    self.set_values({parameter_name: parameter_value}, force=force)
                except KeyError:
                    self.add(McParameter(parameter_name, value=parameter_value))
                except ValueError:
                    # if force==False and parameter value is out of bounds -> do not set the value...
                    logging.info(
                        "DMT->MCard: The parameter %s was not loaded from %s since the value %f was out of bounds.",
                        parameter_name,
                        path_to_file,
                        parameter_value,
                    )

        elif isinstance(modcard, McParameterCollection):
            for para in modcard:
                if not hasattr(para, "group"):
                    para.group = None

                try:
                    self.set(para)
                except KeyError:
                    self.add(para)
        elif isinstance(modcard, dict):
            for (parameter_name, parameter_value) in modcard.items():
                if not parameter_name.startswith("__"):
                    try:
                        # do not reset the limits if parameter is already in modelcard
                        self.set_values({parameter_name: parameter_value}, force=force)
                    except KeyError:
                        self.add(McParameter(parameter_name, value=parameter_value))
        else:
            raise OSError(
                "Loading from file worked, but I do not know how to handle the loaded content of type "
                + str(type(modcard))
                + "!"
            )


class Calculator(ast.NodeVisitor):
    """Small "safe" calculator to allow calculations of model parameters.

    Avoiding the unsafe "eval"...

    Source:
    https://stackoverflow.com/a/33030616

    """

    _UnaryOP_MAP = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Invert: operator.neg,
    }
    """ Implemented unary operators of the calculator (1 Number operations). """
    _BinaryOP_MAP = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }
    """ Implemented binary operators of the calculator (2 Number operations). """

    def visit_UnaryOp(self, node):
        operand = self.visit(node.operand)
        return self._UnaryOP_MAP[type(node.op)](operand)

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return self._BinaryOP_MAP[type(node.op)](left, right)

    def visit_Num(self, node):
        return node.n

    def visit_Expr(self, node):
        return self.visit(node.value)

    @classmethod
    def evaluate(cls, expression):
        tree = ast.parse(expression)
        calc = cls()
        return calc.visit(tree.body[0])
