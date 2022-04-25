""" Base class to handle Verilog-AMS modelcard parameters.

Each parameter has a type, unit, boundaries and invalid values (excludes),
this is taken care of here.
Usually the user has a group of parameters stored in a Collection.
The collection exposes methods to manage the group safely. In generall here many copies are used,
in the exposes methods always deepcopies are returned and set to the collection. This reduces crazy errors, but also need to be handled with care.

Additionally parameters can be compared, they are considered equal, if they have the
same name and value. Also collections can be compared, they are equal, if they have
the same parameters and all parameters are equal.

Finally the classes here also add some pretty printing and loading and saving using pickle.
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
import logging
import copy
import json
import warnings
from pint import Unit

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo


from pathlib import Path

import _pickle as cpickle  # type: ignore
import numpy as np
from typing import Dict, OrderedDict, Type, Union, List, Optional
from pint.formatting import siunitx_format_unit
from pint.errors import UndefinedUnitError

from DMT.core import unit_registry
from DMT.exceptions import (
    ValueExcludedError,
    ValueTooLargeError,
    ValueTooSmallError,
    BoundsError,
    ParaExistsError,
)

try:
    # try to import only, so it is a soft dependency...
    from pylatex import LongTable, MultiColumn, Section, NoEscape
    from DMT.external.pylatex import Tex  # pylint: disable=ungrouped-imports
except ImportError:
    pass

SEMVER_MCPARAMETER_CURRENT = VersionInfo(major=1, minor=0)
SEMVER_MCPARAMETER_Collection_CURRENT = VersionInfo(major=1, minor=0)


class McParameter(object):
    """Objects of this class represent a model card parameter. If you want to store many of them, see McParameterCollection class.

    Attributes
    ----------
    _value   :  Union[float, int, None]
        The value of this parameter.
    name     :  str
        The name of the parameter.
    inc_min  :  bool
        If True, value==min is allowed.
    inc_max  :  bool
        If True, value==max is allowed.
    min      :  Union[float, int]
        The minimum boundary of this parameter.
    max      :  Union[float, int]
        The maximum boundary of this parameter.
    exclude  :  Optional[List[Union[float, int]]]
        Optional list of values that can be excluded as a valid value for value. E.g. if min=-1, max=1, sometimes you might want to exclude 0.
    val_type : Type[Union[int, float]]
        The type of the value.
    description : str
        Description of the parameter

    Parameters
    ----------
    name : str
        Name of the parameter.
    value : Union[float, int, None]
        Value for the parameter. Can also be a other Parameter, then all attributes are copied.
    unit : pint.unit
        Unit of the python Pint package.
    minval : Union[float, int, None]
        Minimum boundary value of the parameter.
    maxval : Union[float, int, None]
        Maximum boundary value of the parameter.
    group  : str
        Display is sorted by groups.
    value_type : Type[Union[int, float]]
        The type of the value.
    inc_min  :  bool
        If True, value==min is allowed.
    inc_max  :  bool
        If True, value==max is allowed.
    exclude  :  Optional[List[Union[float, int]]]
        List of values that are excluded as a valid value for value. E.g. if min=-1, max=1, sometimes you might want to exclude 0.
    description : str
        Description of the parameter

    Methods
    -------
    check_bounds(value)
        Check wheather or not value is within the bounds of this parameter.
    _set_forced( value)
        Force setting the value. ATTENTION: When used, the boundaries may be set to inf!
    dict_json()
        Returns a compact formatted json dump of this parameter
    load_json(cls, name, value, __McParameter__, min, max, type, inc_min, inc_max, exclude, group, unit, description)
        Creates a McParameter from a dictionary obtained by a json.load.

    """

    def __init__(
        self,
        name: str,
        value: Optional[Union[float, int]] = None,
        minval: Optional[Union[float, int]] = None,
        maxval: Optional[Union[float, int]] = None,
        value_type: Type = float,
        inc_min: bool = True,
        inc_max: bool = True,
        exclude: Union[List[Union[float, int]], float, int, None] = None,
        group: str = "",
        unit: Unit = unit_registry.dimensionless,
        description: str = "",
    ):

        if not isinstance(name, str):
            raise IOError("DMT -> McParameter: Parameter name not a string.")
        self.name = name
        self.inc_min = inc_min
        self.inc_max = inc_max
        if value_type == int:
            self._val_type = int
        elif value_type == float:
            self._val_type = float
        else:
            raise NotImplementedError(
                "The type "
                + str(value_type)
                + " of parameter value is not known! Allowed: int, float."
            )

        if (minval is None) or (minval == -np.inf):
            self._min = -np.inf
        else:
            self._min = self._val_type(minval)
        if (maxval is None) or (maxval == np.inf):
            self._max = np.inf
        else:
            self._max = self._val_type(maxval)

        self._exclude: List[Union[float, int]] = []
        self.exclude = exclude

        if value is None:
            self._value = None
        else:
            self._value = self._val_type(value)
        self.unit = unit
        self.group = group
        self.description = description

    def __repr__(self):
        """Set a better repr than McParameter Object at 0xTTTT

        Returns
        -------
        str
            This string could be passed to eval() to get a object with the same values as this one.
        """
        if self._val_type == int:
            str_type = "int"
        elif self._val_type == float:
            str_type = "float"
        else:
            str_type = str(self._val_type)  # make it reprable always...

        str_exclude = "[" + ";".join(f"{excluded:.5g}" for excluded in self.exclude) + "]"

        return (
            "McParameter("
            + self.name
            + f", value={self.value:g}"
            + f", minval={self._min:g}"
            + f", maxval={self._max:g}"
            + ", value_type="
            + str_type
            + ", inc_min="
            + str(self.inc_min)
            + ", inc_max="
            + str(self.inc_max)
            + ", exclude="
            + str_exclude
            + ', group="'
            + self.group
            + '", unit=unit_registry("'
            + str(self.unit)
            + '").units, description="'
            + self.description
            + '")'
        )

    def dict_json(
        self,
    ) -> dict[str, Union[float, int, str, bool, None, List[Union[float, int]]]]:
        """Returns a compact formatted json dump of this parameter"""

        if self._val_type == int:
            str_type = "int"
        elif self._val_type == float:
            str_type = "float"
        else:
            str_type = str(self._val_type)  # make it saveable always...

        try:
            desc = self.description
        except AttributeError:
            desc = ""

        # str_exclude = "[" + ";".join(f"{excluded:.5g}" for excluded in self.exclude) + "]"

        return {
            "name": self.name,
            "value": self._value,
            "min": self._min,
            "max": self._max,
            "inc_min": self.inc_min,
            "inc_max": self.inc_max,
            "exclude": self.exclude,
            "type": str_type,
            "unit": str(self.unit),
            "group": self.group,
            "description": desc,
            "__McParameter__": str(
                SEMVER_MCPARAMETER_CURRENT
            ),  # make versions, so we can introduce compatibility here!
        }

    @classmethod
    def load_json(
        cls,
        name: str,
        value: Union[float, int],
        __McParameter__: Union[float, str],
        min: Optional[Union[float, int]] = None,
        max: Optional[Union[float, int]] = None,
        type: str = "",
        inc_min: bool = True,
        inc_max: bool = True,
        exclude: Optional[List[Union[float, int]]] = None,
        group: str = "",
        unit: Union[str, Unit] = "",
        description: str = "",
    ):
        """Creates a McParameter from a dictionary obtained by a json.load."""
        if isinstance(__McParameter__, float):
            __McParameter__ = (
                f"{__McParameter__:1.1f}.0"  # if it is a number only MAJOR.MINOR is used
            )

        if VersionInfo.parse(__McParameter__) == SEMVER_MCPARAMETER_CURRENT:
            try:
                value_type = {"int": int, "float": float}[type]
            except KeyError:
                value_type = type

            if isinstance(unit, str):
                try:
                    unit = unit_registry(unit).units
                except UndefinedUnitError:
                    unit = unit_registry.dimensionless

            return McParameter(
                name,
                value=value,
                unit=unit,
                minval=min,
                maxval=max,
                group=group,
                value_type=value_type,
                inc_min=inc_min,
                inc_max=inc_max,
                exclude=exclude,
                description=description,
            )
        else:
            raise ValueError(
                f"DMT->McParameter: This dict has an unknown McParameter json version: {__McParameter__:f}"
            )

    @property
    def val_type(self):
        """Return the type of the value."""
        return self._val_type

    @val_type.setter
    def val_type(self, new_type):
        """Set the type of this parameter."""
        if self._value is None:
            self._val_type = new_type  # nothing to do here
        elif new_type == int:
            if self._value == int(self._value):  # test if roundable...
                self._value = int(self._value)
                self._val_type = int
            else:
                raise IOError(
                    "The parameter value was a floating number and it was tried to set the parameter type to integer. The parameter name is: "
                    + self.name
                )
        elif new_type == float:
            self._value = float(self._value)  # can be set always
            self._val_type = new_type
        else:
            raise IOError(
                "This type can not be set for McParameter: "
                + str(new_type)
                + ". The parameter name is: "
                + self.name
            )

    @property
    def min(self) -> Union[float, int]:
        """Return The minimum boundary as an array of length one."""
        return self._min

    @min.setter
    def min(self, min_new: Union[float, int]):
        """Set the minimum boundary and throw errors if min>value or min>max, testing inc_min before doing so."""
        if min_new > self.max:
            raise BoundsError(
                "DMT -> McParameter: The new minimum is above the maximum of the parameter"
            )

        if self._value is None:
            pass
        elif self.inc_min:
            if min_new > self._value:
                raise BoundsError(
                    "DMT -> McParameter: Parameter min value of "
                    + self.name
                    + " can not be set to "
                    + str(min_new)
                    + " since value is currently "
                    + str(self.value)
                    + " ."
                )
        else:
            if min_new >= self._value:
                raise BoundsError(
                    "DMT -> McParameter: Parameter min value of "
                    + self.name
                    + " can not be set to "
                    + str(min_new)
                    + " since value is currently "
                    + str(self.value)
                    + " ."
                )

        self._min = self.val_type(min_new)

    @property
    def max(self) -> Union[float, int]:
        """Return The minimum boundary as an array of length one."""
        return self._max

    @max.setter
    def max(self, max_new: Union[float, int]):
        """Set the max boundary and throw errors if max<value or max<max, testing inc_max before doing so."""
        if max_new < self.min:
            raise BoundsError(
                "DMT -> McParameter: The new minimum is above the maximum of the parameter"
            )

        if self._value is None:
            pass
        elif self.inc_max:
            if max_new < self._value:
                raise BoundsError(
                    "DMT -> McParameter: Parameter max value of "
                    + self.name
                    + " can not be set to "
                    + str(max_new)
                    + " since value is currently "
                    + str(self.value)
                    + " ."
                )
        else:
            if max_new <= self._value:
                raise BoundsError(
                    "DMT -> McParameter: Parameter max value of "
                    + self.name
                    + " can not be set to "
                    + str(max_new)
                    + " since value is currently "
                    + str(self.value)
                    + " ."
                )

        self._max = self.val_type(max_new)

    @property
    def value(self) -> Union[float, int, None]:
        """Returns the value."""
        if self._value is None:
            return None

        return self.val_type(self._value)

    @value.setter
    def value(self, value: Union[float, int, McParameter]):
        if isinstance(value, McParameter):
            self.name = value.name
            self._min = value._min  # pylint: disable=protected-access
            self._max = value._max  # pylint: disable=protected-access
            self.inc_max = value.inc_max
            self.inc_min = value.inc_min
            self.exclude = value.exclude
            self._val_type = value.val_type
            # self.value = value.value

            value = self.check_bounds(value.value)  # type: ignore
            self._value = value
        else:
            value = self.check_bounds(value)
            self._value = value

    @property
    def exclude(self):
        """Return the type of the value."""
        return self._exclude

    @exclude.setter
    def exclude(self, new_exclude: Union[List[Union[float, int]], float, int, None]):
        """Set the type of this parameter."""
        if new_exclude is None:
            self._exclude = []
        else:
            try:
                self._exclude = [self._val_type(val) for val in new_exclude]  # type: ignore
            except TypeError:
                self._exclude = [self._val_type(new_exclude)]  # type: ignore

    def _set_forced(self, value: Union[float, int]):
        """Force setting the value. ATTENTION: When used, the boundaries may be set to inf!"""
        try:
            # try without changing bounds
            self.value = value
        except (ValueTooLargeError, ValueTooSmallError, ValueExcludedError) as err:
            if isinstance(value, McParameter):
                raise IOError(
                    "McParameter _set_forced: The given McParameter is already inconsistent. Stop."
                ) from err
            else:
                # set to no bounds
                if self.val_type == float:
                    self._min = -np.inf
                    self._max = np.inf
                elif self.val_type == int:  # inf not possible in integer...
                    self._min = np.iinfo(int).min
                    self._max = np.iinfo(int).max
                else:
                    raise NotImplementedError("This type is not Implemented") from err
                self._value = self.val_type(value)

    def check_bounds(self, value: Union[float, int]):
        """Check wheather the value parameter is inside the boundaries defined by self.min and self.max.

        Parameters
        ----------
        value  :  int or float or convertable to float
            Value that shall be checked.

        Returns
        -------
        value  :  int or float
            Checked value
        """
        # type check, either int or float is allowed
        if self.val_type == int:
            if int(value) != value:
                raise TypeError(f"The parameter {self:s} is of type Integer!")

            value = int(value)
        elif not isinstance(
            value, (int, float)
        ):  # for floats also integer are allowed. This catches everything else like strings or lists etc.
            raise TypeError(f"The parameter {self:s} is of type Float!")

        # range check
        value_too_large = False
        value_too_small = False

        if self.inc_min and value < self.min:
            value_too_small = True
        elif not self.inc_min and value <= self.min:
            value_too_small = True

        if self.inc_max and value > self.max:
            value_too_large = True
        elif not self.inc_max and value >= self.max:
            value_too_large = True

        if value_too_large:
            raise ValueTooLargeError(
                f"Value of {self:s} above its maximum! Given: {value:e}! Maximum boundary : {self.max:e}!"
            )

        if value_too_small:
            raise ValueTooSmallError(
                f"Value of {self:s} below its minimum! Given: {value:e}! Minimum boundary : {self.min:e}!"
            )

        # exclude check
        if self.exclude is not None:
            if value in self.exclude:
                str_excluded = ";".join(f"{excluded:g}" for excluded in self.exclude)
                raise ValueExcludedError(
                    f"Value of {self:s} is excluded! Given: {value:e}! Excluded : [{str_excluded:s}]!"
                )

        return value

    def __format__(self, wanted_format: str) -> str:
        """Allows formating of McParameters using "{}".format(mc_parameter).

        If a number format (defg) is given, the value is formated, for strings (s) the name.
        Additionally the unit (u) in siunitx format is possible.
        """
        if (
            ("d" in wanted_format)
            or ("e" in wanted_format)
            or ("f" in wanted_format)
            # or ("g" in wanted_format)
        ):
            if self.value is None:
                return "-"  # dirty

            return f"{self.value:{wanted_format}}"
        if "g" in wanted_format:
            if self.value is None:
                return "-"  # dirty

            if self.val_type == float:
                return f"{self.value:{wanted_format}}"
            else:
                # 10.5g -> 10d
                wanted_format = wanted_format.split(".")[0] + "d"
                return f"{self.value:{wanted_format}}"

        if "s" in wanted_format:
            return f"{self.name:{wanted_format}}"

        if "u" in wanted_format:
            if hasattr(self, "unit") and self.unit is not None and not self.unit.dimensionless:
                # return siunitx_format_unit(self.unit)
                try:
                    return siunitx_format_unit(self.unit)  # type: ignore
                except TypeError:
                    return siunitx_format_unit(
                        self.unit._units, unit_registry
                    )  # new version has other interface
            else:
                return "-"

        raise IOError(f"The format {wanted_format} is unknown for McParameters!")

    def __eq__(self, other: McParameter) -> bool:
        """Comparing parameters, equal if name and value is equal."""
        if isinstance(other, McParameter):
            return (self.name == other.name) and (self.value == other.value)

        return NotImplemented


class McParameterCollection(object):
    """
    This parameter collection has properties which as a single parameter. This way a group of parameters and a single parameter can be treated equally.

    Attributes
    ----------
    paras : list
        The parameters of this group

    Parameters
    ----------
    possible_groups : dict[str, str], optional
        Dictionary of possible groups in this collection, saved as Description: GroupName, by default None
    __McParameterCollection__ : Union[VersionInfo, str, float], optional
        Version of the given creation parameters, by default SEMVER_MCPARAMETER_Collection_CURRENT

    Raises
    ------
    NotImplementedError
        Raised when the given version is unknown and hence the
    """

    def __init__(
        self,
        possible_groups: Optional[Dict[str, str]] = None,
        __McParameterCollection__: Union[
            VersionInfo, str, float
        ] = SEMVER_MCPARAMETER_Collection_CURRENT,
        **_kwargs,
    ):
        if not isinstance(__McParameterCollection__, VersionInfo):
            try:
                __McParameterCollection__ = VersionInfo.parse(__McParameterCollection__)  # type: ignore
            except TypeError:
                __McParameterCollection__ = VersionInfo.parse(
                    f"{__McParameterCollection__:1.1f}.0"
                )  # if it is a number only MAJOR.MINOR is used

        if __McParameterCollection__ != SEMVER_MCPARAMETER_Collection_CURRENT:
            raise NotImplementedError(
                "DMT->McParameterCollection: Unknown version of collection to create!"
            )

        self._paras: list[McParameter] = list()
        self._values: OrderedDict[str, Union[float, int]] = OrderedDict()

        if possible_groups is None:
            self.possible_groups = {}
        else:
            self.possible_groups = possible_groups

    @property
    def paras(self):
        """Return the parameters with updated values."""
        self.update_paras()
        return self._paras

    @paras.setter
    def paras(self, paras_new):
        """Set the parameters."""
        self._paras = paras_new
        self.update_values()

    def update_paras(self):
        """Writes back the values into the parameters."""
        for parameter in self._paras:
            parameter.value = self._values[parameter.name]

    def update_values(self):
        """Writes the parameter values into the values dict."""
        self._values = OrderedDict()
        for parameter in self._paras:
            self._values[parameter.name] = parameter.value  # type: ignore

    def info_json(self, **_kwargs):
        """Returns a dict with serializeable content for the json file to create. Add the info about the concrete subclass to create here!"""
        return {
            "possible_groups": self.possible_groups,
            "__McParameterCollection__": str(SEMVER_MCPARAMETER_Collection_CURRENT),
        }  # make versions, so we can introduce compatibility here!

    def dump_json(self, file_path, **kwargs):
        """Writes itself and the parameters in the collection to a file.

        To manipulate what is written to the file, change :py:method::`DMT.core.mc_parameter.McParameterCollection.dumps_json()`
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        content = []
        for para in sorted(self.paras, key=lambda x: (x.group, x.name)):
            content.append(para.dict_json())
        content.append(self.info_json(**kwargs))

        str_content = "["
        for subdict in content:
            str_content += "\n    " + json.dumps(subdict) + ","
        # remove trailing ,
        str_content = str_content[:-1]
        str_content += "]"

        file_path.write_text(str_content, encoding="utf8")

    @classmethod
    def load_json(
        cls,
        file_path: Union[str, Path],
        directory_va_file: Union[str, Path, None] = None,
        ignore_checksum: bool = False,
    ) -> McParameterCollection:
        """Loads the json file, creates the McParameterCollection (or inherited) and adds the McParameters.

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
        McParameterCollection
            The loaded collection

        Raises
        ------
        IOError
            If the collection dictionary is not found in the json file.
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        with file_path.open("r", encoding="utf8") as file_json:
            content = json.load(file_json)

        collection = None
        for dict_content in content:
            if (
                "__McParameterCollection__" in dict_content
                or "__McParameterComposition__" in dict_content
            ):
                collection = cls(
                    directory_va_file=directory_va_file,
                    ignore_checksum=ignore_checksum,
                    **dict_content,
                )
                break

        if collection is None:
            raise IOError(
                "DMT->McParameterCollection: Did not create the collection as no collection dictionary is found in the file.",
                "Try to create a collection object yourself and the load the parameter json files manually.",
            )

        for dict_content in content:
            if "__McParameter__" in dict_content:
                try:
                    collection.add(McParameter.load_json(**dict_content), update=False)
                except ParaExistsError:
                    collection.set(McParameter.load_json(**dict_content), update=False)

        collection.update_values()

        return collection

    def get(
        self, parameters: Union[str, McParameter, list[str], tuple[str], McParameterCollection]
    ) -> Union[McParameter, McParameterCollection]:
        """Returns a McParameterCollection with copies of all given parameter names.

        Parameters
        ----------
        parameters  : str, iterable(str) or McParameterCollection

        Returns
        -------
        mcard_collection : McParameterCollection

        Raises
        ------
        KeyError
            If the para was not in self.
        """
        if isinstance(parameters, (McParameterCollection, list, tuple)):
            mcard_collection = McParameterCollection()
            for para in parameters:
                mcard_collection.add(self.get(para), update=False)

            mcard_collection.update_values()
            return mcard_collection

        try:
            if isinstance(parameters, McParameter):
                my_para = next(para for para in self._paras if para.name == parameters.name)
            elif isinstance(parameters, str):
                my_para = next(para for para in self._paras if para.name == parameters)
            else:
                raise IOError("The parameter is neither of type McParameter or str.")

        except StopIteration as err:
            raise KeyError(
                f"The parameter {parameters:s} is not part of this parameter collection!"
            ) from err

        my_para.value = self._values[my_para.name]
        return copy.deepcopy(my_para)

    def __getitem__(self, para):
        """Allows paras['c10']"""
        return self.get(para)

    def set(self, parameters, update=True, force=False):
        """Set existing paramaters in self.

        Parameters
        ----------
        parameters : McParameter or McParameterCollection
            For each parameter, if it is found in self, it is removed and the given is added. If it is not found, a KeyError is raised.
        update : {True, False}, optional
            If set to False, the values dict is not updated.
        force :  {True, False}, optional
            If set to True, the parameter is added if it did not exist.

        Raises
        ------
        KeyError
            If the para was not in self.
        """
        if isinstance(parameters, McParameterCollection):
            for para in parameters:
                self.set(para, force=force, update=update)
            return

        try:
            index = self.name.index(parameters.name)
        except ValueError as err:
            if force:
                index = -1
            else:
                raise KeyError(
                    f"The parameter {parameters:s} is not part of this parameter collection!"
                ) from err

        if index >= 0:
            self.remove(parameters.name)

        self.add(parameters, index=index, update=False)

        if update:
            self._values[parameters.name] = parameters.val_type(parameters.value)

    def __setitem__(self, name, value):
        """Allows paras['c10']"""
        para = self[name]
        para.value = value
        self.set(para)

    def set_values(self, dict_parameters, force=False, policy_missing="error"):
        """Sets a dictionary of {'name':value} to the parameters in this collection

        Parameters
        ----------
        dict_parameters : {str: float64}
            For each parameter, if it is found in self, the given value is set.
        force : boolean, optional
            If True, values are force set.
        policy_missing : {"error", "ignore", "add"}, optional
            The policy for missing parameters to set, defaults to "error"

        Raises
        ------
        KeyError
            If the para was not in self.
        """
        for name, value in dict_parameters.items():
            try:
                index = self.name.index(name)
            except ValueError as err:
                if policy_missing == "ignore":
                    # nothing to do here
                    continue
                elif policy_missing == "add":
                    para = McParameter(name=name, value=value)
                    self.add(para)
                    index = self.name.index(name)
                else:
                    raise KeyError(
                        f"The parameter {name:s} is not part of this parameter collection!"
                    ) from err

            try:
                self._paras[index].value = value
            except ValueError:
                if force:
                    para = self.get(name)
                    para._set_forced(value)  # type: ignore
                    self.set(para, update=False)
                else:
                    raise

            dict_parameters[name] = self._paras[index].val_type(value)

        self._values.update(dict_parameters)

    def get_values(self, parameters):
        """Returns a list of the values of parameters.

        Returns
        -------
        {name:value}
            A dict with the name of the parameter as key and value as value.

        Raises
        ------
        KeyError
            If the para was not in self.
        """
        values = {}
        for name in parameters:
            values[name] = self._values[name]

        return values

    def set_bounds(self, dict_parameters):
        """Sets a dictionary of {'name':(min, max )} to the parameters in this collection

        Parameters
        ----------
        dict_parameters : {str: (float64, float64)}
            For each parameter, if it is found in self, the given values are set as minimum and maximum.

        Raises
        ------
        KeyError
            If the para was not in self.
        """
        for name, values in dict_parameters.items():
            try:
                index = self.name.index(name)
            except ValueError as err:
                raise KeyError(
                    f"The parameter {name:s} is not part of this parameter collection!"
                ) from err

            self.paras[index].min = values[0]
            self.paras[index].max = values[1]

    def to_kwargs(self):
        """Returns itself as a dictionary fitting to unpack into a function call.

        Returns
        -------
        dict
            {name: value}
        """
        # dict_a = {}
        # for para in self.paras:
        #     dict_a[para.name] = para.value

        return self._values

    def print_parameters(self, paras=None, line_break=""):
        """Just some pretty printing

        Parameters
        ----------
        param : list[str], optional
            List of parameter names to print, if not given, all children are returned!
        line_break : str, optional
            Is added after each parameter, can be used as line breaks

        Returns
        -------
        str
            String with all parameters.
        """
        temp_str = ""
        if paras is None:
            # if None iterate through all
            paras = self.paras
        else:
            paras = self.get(paras)

        try:
            for para in sorted(paras, key=lambda x: (x.group, x.name)):  # type: ignore
                temp_str += f"  {para:<12s} = {para:10.5e} {line_break}"
        except TypeError:  # no groups available
            for para in sorted(paras, key=lambda x: x.name):  # type: ignore
                temp_str += f"  {para:<12s} = {para:10.5e} {line_break}"

        return temp_str

    def print_to_file(self, path_to_file, line_break="", create_dir=False):
        """Prints the parameters into a file. Uses :meth:`print_parameters` to obtain the string to print.

        Parameters
        ----------
        path_to_file : str
            Path to the file to write. '.txt' is added automatically.
        line_break : str, optionally
            Is added after each parameter, can be used as line breaks
        create_dir : {False, True}, optionally
            If true, the respective directory is created first.
        """
        if not isinstance(path_to_file, Path):
            path_to_file = Path(path_to_file)

        if path_to_file.suffix != ".txt":
            path_to_file = path_to_file.with_suffix(".txt")

        if create_dir:
            path_to_file.parent.mkdir(parents=True, exist_ok=True)

        path_to_file.write_text(
            self.print_parameters(line_break=line_break) + "\n", encoding="utf8"
        )

    @classmethod
    def load(cls, path):
        """Load an object from a pickle file.

        Parameters
        ----------
        path : str
            Path to the file to load.

        Returns
        -------
        McParameterCollection
        """
        if not isinstance(path, Path):
            path = Path(path)

        with path.open("rb") as my_db:
            collection = cpickle.load(my_db)

        return collection

    @property
    def name(self):
        """Returns all names of the parameters in the collection"""
        # names = np.chararray(len(self.paras), itemsize=20)
        # for i in range(len(self.paras)):
        #     names[i] = self.paras[i].name
        return [para.name for para in self._paras]

    @property
    def group(self):
        """Returns all groups of the parameters in the collection as a set"""
        groups = []
        for para in self._paras:
            try:
                groups.append(para.group)
            except AttributeError:
                groups.append("")

        return set(groups)

    @property
    def unit(self):
        """Returns all units in the collection"""
        units = []
        for para in self._paras:
            try:
                units.append(para.unit)
            except AttributeError:
                units.append(unit_registry.dimensionless)

        return units

    @property
    def value(self):
        """Returns all parameter values as a np.ndarray."""
        vals = np.empty(len(self._paras))

        for i_para, para in enumerate(self._paras):
            vals[i_para] = para.value

        return vals

    @value.setter
    def value(self, value):
        """Sets all values for all Parameters. Value is a list, the children are set in the given order."""
        if len(value) != len(self._paras):
            raise IOError(
                "The amount of values to set must be the same as the amount of parameters in the collection!"
            )

        for para, val in zip(self._paras, value):
            para.value = val

        self.update_values()

    def remove(self, parameters):
        r"""Removes the given parameter names from the parameter collection.

        Parameters
        ----------
        parameters : str, iterable(str), McParameter or McParameterCollection

        """
        if isinstance(parameters, (list, tuple)):
            for para in parameters:
                self.remove(para)
            return
        elif isinstance(parameters, McParameterCollection):
            for para in parameters:
                self.remove(para.name)
            return

        if isinstance(parameters, McParameter):
            parameters = parameters.name  # extract the name

        try:
            i_para = next(i for i, my_para in enumerate(self._paras) if my_para.name == parameters)
        except StopIteration as err:
            raise KeyError(
                f"The parameter {parameters:s} is not part of this parameter collection and can not be removed!"
            ) from err

        del self._paras[i_para]
        del self._values[parameters]

    @property
    def min(self):
        """All minimal values of this group"""
        vals = np.empty(len(self))
        for i_para, para in enumerate(self._paras):
            vals[i_para] = para.min

        return vals

    @min.setter
    def min(self, min_new):
        """Sets all minimal values, sets each minimum specifically"""
        if len(min_new) != len(self):
            raise IOError(
                "The amount of minimum boundaries to set must be the same as the amount of parameters in the collection!"
            )

        for para, min_a in zip(self._paras, min_new):
            para.min = min_a

    @property
    def max(self):
        """All maximal values of this group"""
        vals = np.empty(len(self))
        for i_para, para in enumerate(self._paras):
            vals[i_para] = para.max

        return vals

    @max.setter
    def max(self, max_new):
        """Sets all maximal values, sets each maximum specifically"""
        if len(max_new) != len(self):
            raise IOError(
                "The amount of minimum boundaries to set must be the same as the amount of parameters in the collection!"
            )

        for para, max_a in zip(self._paras, max_new):
            para.max = max_a

    def print_tex(self):
        """Prints a modelcard as a tex table using PyLaTeX"""
        # try to clean first
        try:
            clean_mcard = self.get_clean_modelcard()  # type: ignore
        except (
            AttributeError,
            KeyError,
            ValueError,
        ):  # was a broad except (add more types if needed)
            clean_mcard = self

        doc = Tex()
        # Generate data table
        with doc.create(Section("Modelcard")):
            doc.append("The final modelcard is summarized in the table below:")
            with doc.create(
                LongTable("l S s", width=3, booktabs=True)
            ) as data_table:  # pylatex does not count s S columns from siunitx
                data_table.add_hline()
                data_table.add_row(["parameter name", NoEscape("{value}"), NoEscape("{unit}")])
                data_table.add_hline()
                data_table.end_table_header()
                data_table.add_hline()
                data_table.add_row(
                    (MultiColumn(3, align="r", data="continued on next Page"),), strict=False
                )
                data_table.add_hline()
                data_table.end_table_footer()
                data_table.add_hline()
                data_table.add_row((MultiColumn(3, align="r", data="Finish"),), strict=False)
                data_table.add_hline()
                data_table.end_table_last_footer()

                group = None
                for para in sorted(clean_mcard, key=lambda x: (x.group, x.name)):
                    if group != para.group:
                        if group is not None:
                            data_table.add_hline()  # horizontal line after each group and then the next group name

                        group = para.group
                        try:
                            group_desc = next(
                                description
                                for description, group_a in self.possible_groups.items()
                                if group_a == group
                            )
                            data_table.add_row(
                                (MultiColumn(3, align="l", data=group_desc),), strict=False
                            )
                        except StopIteration:
                            pass

                    data_table.add_row(
                        [f"{para:<12s}", NoEscape(f"{para:g}"), NoEscape(f"{para:u}")], strict=False
                    )

        return doc

    def __iter__(self):
        # return iter(self.paras)
        return iter(copy.deepcopy(self.paras))

    def sort_paras(self):
        """Sorts the parameters according to the groups."""
        self._paras.sort(key=lambda x: (x.group, x.name))

    def iter_alphabetical(self):
        """Returns an iterator on parameters sorted alphabetically by name"""
        return iter(sorted(copy.deepcopy(self.paras), key=lambda para: para.name))

    def __len__(self):
        return len(self._paras)

    def __contains__(self, other):
        return other.name in self.name

    def add(self, paras, index=None, update=True):
        """Add a parameter to self. This is only allowed, if the parameter name is not already known to the collection."""
        if isinstance(paras, (McParameterCollection)):
            if index is None:
                for para in paras._paras:  # deepcopy is in the McParameter add
                    self.add(para, update=update)
            else:
                for para in paras._paras[
                    ::-1
                ]:  # reverse order if index is given -> insert turns the order around again
                    self.add(para, index=index, update=update)
            return

        if isinstance(paras, McParameter):
            if paras.name in self.name:
                raise ParaExistsError(
                    f"Tried to set parameter {paras:s}, which was already defined."
                )
            else:
                if index is None:
                    self._paras.append(copy.deepcopy(paras))
                else:
                    self._paras.insert(index, copy.deepcopy(paras))

                if update:
                    self._values[paras.name] = paras.val_type(paras.value)  # type: ignore
        else:
            raise TypeError(
                "McParameterCollection accepts only McParameter or McParameterCollection!"
            )

    def __add__(self, other):
        """Allows appending of two collections by mc1 + mc2"""
        if isinstance(other, (McParameter, McParameterCollection)):
            mc_return = copy.deepcopy(self)
            mc_return.add(other)

            return mc_return
        else:
            return NotImplemented

    def __radd__(self, other):
        """Called when parameter + collection is used. Here we need to take care of the index!"""
        if isinstance(other, (McParameter, McParameterCollection)):
            mc_return = copy.deepcopy(self)
            mc_return.add(other, index=0)  # insert at start

            return mc_return
        else:
            return NotImplemented

    def eq_paras(self, other):
        """Compares the parameters in two McParameterCollections or subclasses"""
        str_diff_vars = ""
        for para in self.paras:
            try:
                if para.value != other.get(para.name).value:
                    str_diff_vars += f"{para:<12s}: {para:10.4e} || {other.get(para):10.4e}\n"
            except KeyError:
                str_diff_vars += f"The second modelcard does not have a {para:s} parameter!\n"

        # find parameters in other which are not in self!
        for para in other:
            if para.name not in self.name:
                str_diff_vars += f"The first modelcard does not have a {para:s} parameter!\n"

        if str_diff_vars:
            logging.info(str_diff_vars)
            return False

        return True

    def __eq__(self, other):
        """Allows comparing 2 model cards using mc1 == mc2"""
        if isinstance(other, McParameterCollection):
            # can only compare to other collections
            return self.eq_paras(other)

        return NotImplemented


class McParameterComposition(McParameterCollection):
    """Deprecated name for the mc parameter collection"""

    def __init__(
        self,
        __McParameterComposition__: Union[
            VersionInfo, str, float
        ] = "1.0.0",  # as until now there is only v1.0.0 around we have no issues here.
        **kwargs,
    ):
        warnings.warn(
            "McParameterComposition is deprecated. It was renamed to McParameterCollection to avoid confusion with the composition design pattern.\nMcParameterCompostion will be deleted in the next major release.",
            category=DeprecationWarning,
        )

        super().__init__(**kwargs)
