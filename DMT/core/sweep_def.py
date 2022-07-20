""" Basic description of a sweep in DMT.

Sweeps are the basic element that can be fed into simulators or be retrieved from simulations or measurements.
Features:

* Clear syntax and definition to create a well described simulation independent of the simulator interface.

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
from typing import Dict, List, Mapping, Type, Optional, Union, Tuple
import numpy as np
from DMT.core import (
    get_specifier_from_string,
    SpecifierStr,
)


class SweepDef(object):
    """One sweep definition

    Subclass this to introduce own sweep types. The methods which need to be overwritten are:

    * :meth:`~DMT.core.sweep.SweepDef._correct_sweep_type`
    * :meth:`~DMT.core.sweep.SweepDef.set_values`

    It is recommended try the super method and except the raised errors.

    Parameters
    ----------
    var_name : :class:`~DMT.core.naming.SpecifierStr`
        Name of the variable to sweep.
    sweep_type : str
        Which type of sweep is performed for this variable
    sweep_order : int, optional
        Position in the sweep.
    value_def : float, list or np.array, optional
        The needed variables depending on the sweep type.
    sync : :class:`~DMT.core.naming.SpecifierStr` or :class:`~DMT.core.sweep.SweepDef`, optional
        Synced 'slave' sweep.
    """

    def __init__(
        self,
        var_name: SpecifierStr,
        sweep_type: str,
        sweep_order: Optional[int] = None,
        value_def: Optional[Union[int, float, Tuple, List, np.array]] = None,
        master: Optional[SpecifierStr] = None,
        offset: Optional[Union[int, float, SpecifierStr]] = None,
        sync: Optional[Union[SpecifierStr, SweepDef]] = None,
    ):
        # needed names for repr
        self._attr_repr = [
            "var_name",
            "sweep_type",
            "sweep_order",
            "value_def",
            "master_var",
            "sync_var",
            "offset_var",
            "offset_value",
        ]

        self.var_name = get_specifier_from_string(var_name)
        if not isinstance(self.var_name, SpecifierStr):
            raise IOError(
                "DMT->Sweep: Automatic conversion from var_name string to SpecifierStr failed for the variable: "
                + var_name
                + "!\n Please provide the correct SpecifierStr manually. "
            )

        self._sweep_type = None
        self.sweep_type = sweep_type

        self.sweep_order = sweep_order

        # check if either value_def or master is given-----------
        if value_def is None and master is None:
            raise IOError(
                "DMT -> Sweep: You either forgot value_def or master in your sweepdef for the variable "
                + self.var_name
                + "."
            )

        self._master_var = None
        self._master_swd = None
        self.master = master

        self._sync_var = None
        self._sync_swd = None
        self.sync = sync

        if value_def is None:
            self.value_def = np.zeros((1,))
        else:
            self.value_def = value_def

        self._offset_var = None
        self._offset_swd = None
        self._offset_value = None
        self.offset = offset

        self.values = None
        self.set_values()

    @property
    def sweep_type(self):
        """Directly return the sweep type"""
        return self._sweep_type

    @sweep_type.setter
    def sweep_type(self, sweep_type_new):
        """Call the corrector. It can be overwritten by a inheriting class."""
        self._sweep_type = self._correct_sweep_type(sweep_type_new)

    def _correct_sweep_type(self, sweep_type_new):
        """Correct the sweep type string to allowed ones.

        Parameters
        ----------
        sweep_type_new : str

        Returns
        -------
        sweep_type : str

        Raises
        ------
        IOError
            If the sweep type is not known.
        """
        sweep_type_new = sweep_type_new.upper()
        # correct the sweep type
        if "LIN" in sweep_type_new:
            return "LIN"
        elif "LOG" in sweep_type_new:
            return "LOG"
        elif "CON" in sweep_type_new:
            return "CON"
        elif "SYNC" in sweep_type_new:
            return "SYNC"
        elif "LIST" in sweep_type_new:
            return "LIST"
        else:
            raise IOError(
                'DMT->Sweep: specified sweeptype:"' + sweep_type_new + '" is unknown to DMT.'
            )

    @property
    def master(self):
        """Master sweep definition, None if the master sweep is not set or not given."""
        return self._master_swd

    @property
    def master_var(self):
        """Getter of the master_var. This attribute has no setter! Use master itself for this!"""
        return self._master_var

    @master.setter
    def master(self, master_new):
        """Sets the master sweep and at the same time the master_var attribute to keep them consistant."""
        try:
            self._master_var = master_new.var_name
            self._master_swd = master_new
        except AttributeError:
            self._master_var = master_new
            self._master_swd = None

    @property
    def sync(self):
        """Sync sweep definition, None if there is no synced sweeped."""
        return self._sync_swd

    @property
    def sync_var(self):
        """Getter of the sync_var. This attribute has no setter! Use sync itself for this!"""
        return self._sync_swd

    @sync.setter
    def sync(self, sync_new):
        """Sets the sync sweep and at the same time the sync_var attribute to keep them consistant."""
        try:
            self._sync_var = sync_new.var_name
            self._sync_swd = sync_new
        except AttributeError:
            self._sync_var = sync_new
            self._sync_swd = None

    @property
    def offset(self):
        """Offset sweep definition. Can be None, float64 or a SweepDef"""
        return self._offset_swd

    @property
    def offset_var(self):
        """Getter of the offset_var. This attribute has no setter! Use offset itself for this! None, if offset is not a SweepDef."""
        return self._offset_var

    @property
    def offset_value(self):
        """Getter of the offset_valaue. This attribute has no setter! Use offset itself for this! None, if offset is a SweepDef."""
        return self._offset_value

    @offset.setter
    def offset(self, offset_new):
        """Sets the offset sweep and at the same time the offset_var attribute to keep them consistant."""
        self._offset_value = None
        try:
            self._offset_var = offset_new.var_name
            self._offset_swd = offset_new
        except AttributeError:
            if isinstance(offset_new, str):
                self._offset_var = offset_new
                self._offset_swd = None
            else:
                self._offset_var = None
                self._offset_value = offset_new
                self._offset_swd = offset_new

    def __repr__(self):
        return (
            "SweepDef ("
            + ", ".join(
                ["'{0:s}': {1}".format(attr, getattr(self, attr)) for attr in self._attr_repr]
            )
            + ")"
        )

    def set_values(self):
        """Sets self.values

        Raises
        ------
        OSError
            If the sweep type is not known.
        """
        if self.sweep_type == "LIN":
            self.values = np.linspace(
                self.value_def[0], self.value_def[1], self.value_def[2], dtype=np.float64
            )

        elif self.sweep_type == "CON":
            self.values = np.array(self.value_def, dtype=np.float64)
            if self.values.size > 1:
                raise IOError(
                    "DMT->SweepDef: Constant sweeps must have only one value in value_def!"
                )

        elif self.sweep_type == "LOG":
            self.values = np.logspace(
                self.value_def[0], self.value_def[1], self.value_def[2], dtype=np.float64
            )

        elif self.sweep_type == "LIST":
            self.values = np.array(self.value_def, dtype=np.float64)

        elif self.sweep_type == "SYNC":
            if self.master is None:  # master has not been replaced jet..
                return

            try:
                self.values = self.master.values + self.offset
            except TypeError:
                self.values = np.zeros((self.offset.values.size, self.master.values.size))
                for i_col in range(self.values.shape[0]):
                    self.values[i_col, :] = self.master.values + self.offset.values[i_col]
                self.values = np.concatenate(self.values)


class SweepDefConst(SweepDef):
    """Constant sweep definition

    Parameters
    ----------
    var_name : SpecifierStr
        Variable name
    value_def : Union[int, float]
        Value for the variable
    sweep_order : int, optional
        Position in the sweep.
    """

    def __init__(
        self,
        var_name: SpecifierStr,
        value_def: Union[int, float],
        sweep_order: Optional[int] = None,
    ):
        super().__init__(
            var_name=var_name,
            sweep_type="CON",
            sweep_order=sweep_order,
            value_def=value_def,
        )


class SweepDefLinear(SweepDef):
    """Linear sweep definition

    Parameters
    ----------
    var_name : SpecifierStr
        Variable name
    value_def : Union[int, float]
        Values for the linear sweepdef. Must have 3 Elements: np.linspace(self.value_def[0], self.value_def[1], self.value_def[2], dtype=np.float64)

    sweep_order : int, optional
        Position in the sweep.
    """

    def __init__(
        self,
        var_name: SpecifierStr,
        value_def: Union[Tuple, List, np.array],
        sweep_order: Optional[int] = None,
    ):
        super().__init__(
            var_name=var_name,
            sweep_type="LIN",
            sweep_order=sweep_order,
            value_def=value_def,
        )


class SweepDefLog(SweepDef):
    """Logarithmic sweep definition

    Parameters
    ----------
    var_name : SpecifierStr
        Variable name
    value_def : Union[int, float]
        Values for the logarithmic sweepdef. Must have 3 Elements: np.logspace(self.value_def[0], self.value_def[1], self.value_def[2], dtype=np.float64)

    sweep_order : int, optional
        Position in the sweep.
    """

    def __init__(
        self,
        var_name: SpecifierStr,
        value_def: Union[Tuple, List, np.array],
        sweep_order: Optional[int] = None,
    ):
        super().__init__(
            var_name=var_name,
            sweep_type="LOG",
            sweep_order=sweep_order,
            value_def=value_def,
        )


class SweepDefList(SweepDef):
    """List or table sweep definition

    Parameters
    ----------
    var_name : SpecifierStr
        Variable name
    value_def : Union[int, float]
        Values for the variable.

    sweep_order : int, optional
        Position in the sweep.
    """

    def __init__(
        self,
        var_name: SpecifierStr,
        value_def: Union[Tuple, List, np.array],
        sweep_order: Optional[int] = None,
    ):
        super().__init__(
            var_name=var_name,
            sweep_type="LIST",
            sweep_order=sweep_order,
            value_def=value_def,
        )


class SweepDefSync(SweepDef):
    """Synchronized sweep definition

    Parameters
    ----------
    var_name : SpecifierStr
        Variable name
    value_def : Union[int, float]
        Values for the variable.
    master : SpecifierStr
        Master sweep variable.
    offset : Union[int, float, SpecifierStr]
        Offset value for the sweeps or a variable name, which is sweeped in a different SweepDef.

    sweep_order : int, optional
        Position in the sweep.
    """

    def __init__(
        self,
        var_name: SpecifierStr,
        master: SpecifierStr,
        offset: Union[int, float, SpecifierStr],
        sweep_order: Optional[int] = None,
    ):
        super().__init__(
            var_name=var_name,
            sweep_type="SYNC",
            sweep_order=sweep_order,
            master=master,
            offset=offset,
        )
