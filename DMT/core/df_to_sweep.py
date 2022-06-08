""" Converter routine to create a sweep definition from a given DataFrame
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
from typing import Type, Optional
import warnings
import numpy as np

from DMT.core import Sweep, specifiers, sub_specifiers, DataFrame, SweepDef


def df_to_sweep(
    df_to_convert: DataFrame,
    temperature: float = 300.0,
    name: Optional[str] = None,
    from_forced: bool = True,
    SweepDefClass: Type = SweepDef,
    decimals_potentials: int = 3,
):
    """Create a sweepdefinition which simulates the same forced values as the given measurement data frame.

    For the moment only voltage sweeps...

    Parameters
    ----------
    df_to_convert : :class:`~DMT.core.data_frame.DataFrame`
        DataFrame with voltages which define the sweep.
    temperature : float, optional
        Temperature of the measurement in Kelvin, defaults to 300.0
    name : str, optional
        Name of the sweep to create. If None, automatic generation of a name is tried.
    from_forced : {True, False}, optional
        If True, the forced voltages are used to create the sweepdef.
    SweepDefClass : :class:`~DMT.core.sweep.SweepDef`
        SweepDef class for the sweep to create from
    decimals_potentials : int
        Round the potentials to this x decimals, defaults to 3

    Returns
    -------
    :class:`~DMT.core.sweep.Sweep`
    """
    warnings.warn(
        "df_to_sweep is deprecated and will be removed in the next major release.\nUse Sweep.get_sweep in future.\n",
        category=DeprecationWarning,
    )

    vars_other = {
        specifiers.TEMPERATURE: temperature
    }  # temperature is usually in the dut.data key and not in the df. Additionally it is always constant ?!?
    def_output = []
    potentials_forced = []  # list of forced voltages
    for col in df_to_convert.columns:
        try:
            if col.specifier not in [
                specifiers.VOLTAGE,
                specifiers.FREQUENCY,
            ]:  # all columns except voltages and frequency are outputs
                def_output.append(col)
            if (
                (col.specifier == specifiers.VOLTAGE)
                and len(col.nodes) == 1
                and (not from_forced or (sub_specifiers.FORCED in col))
            ):  # forced voltages are needed to create sweepdef
                potentials_forced.append(col)
        except AttributeError:  # can only analyze specifiers
            def_output.append(col)

    if not potentials_forced:
        raise IOError(
            "DMT->df_to_sweep: No forced potentials in the columns. Make sure all forced potentials in the columns are SpecifierStr!"
        )

    # find one potential with only one value and set it as reference potential!
    potential_common = ""
    for potential in sorted(
        potentials_forced, key=lambda x: x.nodes[0]
    ):  # sort to make sure everytime the same is found.
        if len(np.unique(np.round(df_to_convert[potential].to_numpy(), decimals_potentials))) == 1:
            potential_common = potential  # use this one! Even if more than one would exist.
            break

    if not potential_common:  # no potential found
        # did not find anything :(
        raise IOError(
            "DMT -> df_to_sweep: The user supplied voltages do not define unambiguous sweep conditions for the transistor. No common reference potential was found."
        )

    def_sweep = [
        {"var_name": potential_common, "sweep_order": 0, "sweep_type": "CON", "value_def": [0]},
    ]  # 0 because the other Sweepdefs are added as voltages.
    sweep_order = 1

    # now we need all sweep potentials with regard to one reference potential or other synced sweeps.
    potentials_sweep = [
        potential for potential in set(potentials_forced) if potential != potential_common
    ]

    # find order of sweeps including V_BC sweeps... (innermost, ..., outermost)
    count_ops = {}
    for potential in sorted(potentials_sweep, key=lambda x: x.nodes[0]):
        # against all other:
        for potential_other in sorted(potentials_forced, key=lambda x: x.nodes[0]):
            if potential_other == potential:
                continue  # not against self

            if from_forced:
                if potential_other + potential.nodes[0] + sub_specifiers.FORCED in count_ops:
                    continue  # not V_BC and V_CB, only one of those..

                voltage = potential + potential_other.nodes[0] + sub_specifiers.FORCED
            else:
                if potential_other + potential.nodes[0] in count_ops:
                    continue  # not V_BC and V_CB, only one of those..

                voltage = potential + potential_other.nodes[0]

            df_to_convert.ensure_specifier_column(voltage)
            values = np.unique(np.round(df_to_convert[voltage].to_numpy(), decimals_potentials))
            count_ops[voltage] = len(values)

    for i_voltage, (voltage, _count) in enumerate(
        sorted(count_ops.items(), key=lambda kv: kv[1])[:-1]
    ):  # last of the sorted list is the one we don't need
        df_to_convert.ensure_specifier_column(voltage)
        values = np.unique(np.round(df_to_convert[voltage].to_numpy(), decimals_potentials))

        if voltage.nodes[1] == potential_common.nodes[0]:  # convert to potential if possible
            if from_forced:
                potential = specifiers.VOLTAGE + voltage.nodes[0] + sub_specifiers.FORCED
            else:
                potential = specifiers.VOLTAGE + voltage.nodes[0]

            def_sweep.append(
                {
                    "var_name": potential,
                    "sweep_order": sweep_order,
                    "sweep_type": "LIST",
                    "value_def": values,
                }
            )
        else:  # sweep a voltage is more difficult
            # nodes in all other voltages:
            other_nodes = ""
            for voltage_other, _count in sorted(count_ops.items(), key=lambda kv: kv[1])[
                i_voltage + 1 : -1
            ]:
                other_nodes += "".join(voltage_other.nodes)

            potential = specifiers.VOLTAGE + "C"  # per default a BC sweep
            potential_master = specifiers.VOLTAGE + "B"
            for node_master in voltage.nodes:
                if node_master in other_nodes:
                    if from_forced:
                        potential_master = specifiers.VOLTAGE + node_master + sub_specifiers.FORCED
                        node_other = next(node for node in voltage.nodes if node != node_master)
                        potential = specifiers.VOLTAGE + node_other + sub_specifiers.FORCED
                    else:
                        potential_master = specifiers.VOLTAGE + node_master
                        node_other = next(node for node in voltage.nodes if node != node_master)
                        potential = specifiers.VOLTAGE + node_other

            voltage_offset = potential + potential_master.nodes[0]

            if voltage != voltage_offset:  # order of nodes reversed
                values = np.round(-values, decimals_potentials)  # invert voltage

            def_sweep.append(
                {
                    "var_name": voltage_offset,
                    "sweep_order": sweep_order,
                    "sweep_type": "LIST",
                    "value_def": values,
                }
            )

            # find sweep_order of potential_master
            sweep_order_master = 0
            for i_voltage_master, (voltage_master, _count) in enumerate(
                sorted(count_ops.items(), key=lambda kv: kv[1])[:-1]
            ):
                if (
                    voltage_master.nodes[1] == potential_common.nodes[0]
                ):  # convert to potential if possible
                    if voltage_master.nodes[0] == potential_master.nodes[0]:
                        sweep_order_master = i_voltage_master + 1  # plus 1 bc 1st swd is root
                        break

            def_sweep.append(
                {
                    "var_name": potential,
                    "sweep_order": sweep_order_master,
                    "sweep_type": "SYNC",
                    "master": potential_master,
                    "offset": voltage_offset,
                }
            )

        sweep_order += 1

    ### grab definition for the frequency, if possible
    if specifiers.FREQUENCY in df_to_convert.columns:
        freq = np.unique(
            np.round(df_to_convert[specifiers.FREQUENCY].to_numpy(), decimals_potentials)
        )
        def_sweep.append(
            {
                "var_name": specifiers.FREQUENCY,
                "sweep_order": sweep_order,
                "sweep_type": "LIST",
                "value_def": freq,
            },
        )
        is_ac = True
    else:
        is_ac = False

    ### Name
    if name is None:
        # generate a (good) name
        if is_ac:
            name = "AC"
        else:
            name = "DC"

    return Sweep(
        name,
        sweepdef=def_sweep,
        othervar=vars_other,
        outputdef=def_output,
        SweepDefClass=SweepDefClass,
    )
