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
import logging
import copy
from typing import Dict, List, Mapping, Type, Optional, Union, Set
import numpy as np
from itertools import product
from DMT.core import create_md5_hash, specifiers, sub_specifiers, SpecifierStr, DataFrame, SweepDef


def get_sweepdef(
    data: DataFrame,
    inner_sweep_voltage: Optional[SpecifierStr] = None,
    outer_sweep_voltage: Optional[SpecifierStr] = None,
    decimals_potentials: int = 3,
):
    """Given a dataframe, one inner sweep_voltage and one outer sweep voltage, this method tries to create a SweepDefinition that can be used to re-simulate the data.

    Parameters
    ----------
    data : DataFrame
        Frame to extract the sweepdefs from
    inner_sweep_voltage : SpecifierStr | None, optional
        A specifier that determiens the inner sweep voltage, by default None
    outer_sweep_voltage : SpecifierStr | None, optional
        A specifier that determiens the inner outer voltage, by default None
    decimals_potentials : int, optional
        Round the potentials to x number of decimals, by default 3

    Returns
    -------
    sweepdef : [{}]
        A sweep definition that can be used to init a SweepDef.

    Raises
    ------
    IOError
        No forced potentials (or potentials at all) in the columns. Make sure all forced potentials in the columns are SpecifierStr!"
    IOError
        The supplied voltages do not define unambiguous sweep conditions for the data.
    NotImplementedError
        Either set both or no sweep specifier for now!
    NotImplementedError
        If both sweep voltages are set to currents

    """
    if not data.columns.is_unique:
        data = data.loc[:, ~data.columns.duplicated()]  # type: ignore

    if inner_sweep_voltage is None and outer_sweep_voltage is None:
        from_forced = False
        for col in data.columns:
            if sub_specifiers.FORCED in col:
                from_forced = True
                break  # found one -> do from forced

        potentials_forced = []  # list of forced voltages
        for col in data.columns:
            try:
                if (
                    (col.specifier == specifiers.VOLTAGE)
                    and len(col.nodes) == 1
                    and (not from_forced or (sub_specifiers.FORCED in col))
                ):  # forced voltages are needed to create sweepdef
                    potentials_forced.append(col)
            except AttributeError:  # can only analyze specifiers
                pass

        if not potentials_forced:
            raise IOError(
                "DMT->df_to_sweep: No forced potentials in the columns. Make sure all forced potentials in the columns are SpecifierStr!"
            )

        # find one potential with only one value and set it as reference potential!
        potential_common = ""
        for potential in sorted(
            potentials_forced, key=lambda x: x.nodes[0]
        ):  # sort to make sure everytime the same is found.
            if len(np.unique(np.round(data[potential].to_numpy(), decimals_potentials))) == 1:
                potential_common = potential  # use this one! Even if more than one would exist.
                break

        if not potential_common:  # no potential found
            # did not find anything :(
            raise IOError(
                "DMT -> df_to_sweep: The user supplied voltages do not define unambiguous sweep conditions for the transistor. No common reference potential was found."
            )

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

                data.ensure_specifier_column(voltage)
                values = np.unique(np.round(data[voltage].to_numpy(), decimals_potentials))
                count_ops[voltage] = len(values)

        for i_voltage, (voltage, _count) in enumerate(
            sorted(count_ops.items(), key=lambda kv: kv[1])[:-1]
        ):  # last of the sorted list is the one we don't need
            data.ensure_specifier_column(voltage)
            if i_voltage == 0:
                outer_sweep_voltage = voltage
            elif i_voltage == 1:
                inner_sweep_voltage = voltage
            else:
                raise OSError("only two stage voltages allowed :(")

    elif inner_sweep_voltage is None or outer_sweep_voltage is None:
        raise NotImplementedError(
            "DMT->get_sweepdef: Either set both or no sweep specifier for now!"
        )

    assert inner_sweep_voltage is not None
    assert outer_sweep_voltage is not None

    if specifiers.VOLTAGE in inner_sweep_voltage and specifiers.VOLTAGE in outer_sweep_voltage:
        # classical decision: Efficient short code vs cryptic. Not sure which is better here.
        # -> try general code: transform voltage definition into appropriate "coordinate" system, where the voltages become independent from each other.
        potential_one_inner = (
            specifiers.VOLTAGE + inner_sweep_voltage.nodes[0] + inner_sweep_voltage.sub_specifiers
        )
        potential_two_inner = (
            specifiers.VOLTAGE + inner_sweep_voltage.nodes[1] + inner_sweep_voltage.sub_specifiers
        )

        potential_one_outer = (
            specifiers.VOLTAGE + outer_sweep_voltage.nodes[0] + outer_sweep_voltage.sub_specifiers
        )
        potential_two_outer = (
            specifiers.VOLTAGE + outer_sweep_voltage.nodes[1] + outer_sweep_voltage.sub_specifiers
        )

        # find common potential between voltages and set it as reference potential
        common_potential = [
            potential
            for potential in [potential_one_inner, potential_two_inner]
            if potential in [potential_one_outer, potential_two_outer]
        ]
        if len(common_potential) != 1:
            raise IOError(
                "DMT -> Sweep -> get_sweep: the supplied voltages do not define unambiguous sweep conditions for the data."
            )

        # now we just need two sweeps and one reference potential. wuhu...
        reference_potential = common_potential[0]
        inner_sweep_potential = next(
            potential
            for potential in [potential_one_inner, potential_two_inner]
            if potential != reference_potential
        )
        outer_sweep_potential = next(
            potential
            for potential in [potential_one_outer, potential_two_outer]
            if potential != reference_potential
        )

        # find list values for the two swept potentials with respect to the new reference node.
        outer_sweep_potential_vals = (
            data[outer_sweep_potential].to_numpy() - data[reference_potential].to_numpy()
        )
        outer_sweep_potential_vals = np.round(
            outer_sweep_potential_vals, decimals=decimals_potentials
        )
        outer_sweep_potential_vals = np.unique(outer_sweep_potential_vals)

        inner_sweep_potential_vals = (
            data[inner_sweep_potential].to_numpy() - data[reference_potential].to_numpy()
        )
        inner_sweep_potential_vals = np.unique(inner_sweep_potential_vals)

        # the circuit only allows to sweep VB VC VE, which are forced due to the circuit topology
        sweepdef = [
            {
                "var_name": specifiers.VOLTAGE + reference_potential.nodes[0],
                "sweep_order": 1,
                "sweep_type": "CON",
                "value_def": [0],
            },
            {
                "var_name": specifiers.VOLTAGE + outer_sweep_potential.nodes[0],
                "sweep_order": 2,
                "sweep_type": "LIST",
                "value_def": outer_sweep_potential_vals,
            },
            {
                "var_name": specifiers.VOLTAGE + inner_sweep_potential.nodes[0],
                "sweep_order": 3,
                "sweep_type": "LIST",
                "value_def": inner_sweep_potential_vals,
            },
        ]
    else:
        if specifiers.CURRENT in inner_sweep_voltage and specifiers.CURRENT in outer_sweep_voltage:
            # two currents forced
            raise OSError("Only one forced current at the moment!")
        if specifiers.CURRENT in inner_sweep_voltage:
            # one current forced, one voltage
            inner_sweep_potential_vals = +data[inner_sweep_voltage].to_numpy()
            reference_potential = specifiers.VOLTAGE + outer_sweep_voltage.nodes[1]
            outer_sweep_potential_vals = data[outer_sweep_voltage].to_numpy()
            outer_sweep_potential_vals = np.unique(outer_sweep_potential_vals)
            sweepdef = [
                {
                    "var_name": reference_potential,
                    "sweep_order": 1,
                    "sweep_type": "CON",
                    "value_def": [0],
                },
                {
                    "var_name": specifiers.VOLTAGE + outer_sweep_voltage.nodes[0],
                    "sweep_order": 2,
                    "sweep_type": "CON",
                    "value_def": outer_sweep_potential_vals,
                },
                {
                    "var_name": inner_sweep_voltage,
                    "sweep_order": 3,
                    "sweep_type": "LIST",
                    "value_def": inner_sweep_potential_vals,
                },
            ]
        elif specifiers.CURRENT in outer_sweep_voltage:
            potential_one_inner = (
                specifiers.VOLTAGE
                + inner_sweep_voltage.nodes[0]
                + inner_sweep_voltage.sub_specifiers
            )
            potential_two_inner = (
                specifiers.VOLTAGE
                + inner_sweep_voltage.nodes[1]
                + inner_sweep_voltage.sub_specifiers
            )

            # find common potential between voltages and set it as reference potential
            common_potential = [potential_two_inner]

            # now we just need two sweeps and one reference potential. wuhu...
            reference_potential = common_potential[0]
            inner_sweep_potential = next(
                potential
                for potential in [potential_one_inner, potential_two_inner]
                if potential != reference_potential
            )

            outer_sweep_potential_vals = np.unique(data[outer_sweep_voltage].to_numpy())

            inner_sweep_potential_vals = (
                data[inner_sweep_potential].to_numpy() - data[reference_potential].to_numpy()
            )
            inner_sweep_potential_vals = np.unique(inner_sweep_potential_vals)

            # the circuit only allows to sweep VB VC VE, which are forced due to the circuit topology
            sweepdef = [
                {
                    "var_name": specifiers.VOLTAGE + reference_potential.nodes[0],
                    "sweep_order": 1,
                    "sweep_type": "CON",
                    "value_def": [0],
                },
                {
                    "var_name": outer_sweep_voltage,
                    "sweep_order": 2,
                    "sweep_type": "CON",
                    "value_def": outer_sweep_potential_vals,
                },
                {
                    "var_name": specifiers.VOLTAGE + inner_sweep_potential.nodes[0],
                    "sweep_order": 3,
                    "sweep_type": "LIST",
                    "value_def": inner_sweep_potential_vals,
                },
            ]
        else:
            raise NotImplementedError

    return sweepdef


class Sweep(object):
    r"""Creates a sweep.

    The following parameters need to be specified in the sweepdef or othervar parameter for every DUT, else an error is raised:

    * :py:const:`~DMT.core.specifiers.TEMPERATURE`: device or simulation temperature

    Parameters
    ----------
    name : str
        Name of the sweep.
        Prefix for the simulation folder for this sweep. Just for visuals, sometimes 'VBC0' is nice.

    sweepdef : List[Dict[str, Unknown] | SweepDef], optional
        Definition of a sweep. The following keys MUST be specified for each subsweep: 'var_name','sweep_type'.
        Depending on the sweep type additional keys must be specified:

        * 'LIN' : The value for the key 'value_def' is an array [start, end, nsteps].
          The values are linearly spaced with nsteps from start to end.
        * 'LOG' : The value for the key 'value_def' is an array [start, end, nsteps].
          The values are logarithmically spaced with nsteps from 10^start to 10^end.
        * 'CON' : The value for the key 'value_def' is an array [val] or single number.
        * 'SYNC': The value for the key 'master' is a 'string' with the value of the key 'var_name' of the master sweep.
          Additionally an 'offset' to the master sweep can be specified.

        Also note that Sweep() can only sweep potentials, voltages are only swept indirectly. This is a willfull design decision.
        Ideally the 'var_name' is a :class:`~DMT.core.naming.SpecifierStr`, but :meth:`~DMT.core.naming.get_specifier_from_string`
        is called on the variable name anyway. So if a unique conversion exists var_name can be a string.

        If the key 'sweep_order' is not explicitly specified, it is given by the sweep definitions position in the list with increasing order.
        Examples::

            sweepdef = [
                {'var_name':specifiers.VOLTAGE+'B', 'sweep_order':1, 'sweep_type':'LIN', 'value_def':[0,1,11]},
                {'var_name':specifiers.VOLTAGE+'C', 'sweep_order':2, 'sweep_type':'CON', 'value_def':[1]},
                {'var_name':specifiers.VOLTAGE+'E', 'sweep_order':3, 'sweep_type':'CON' , 'value_def':[0]}
            ]

            sweepdef = [ #this is equivalent to above sweepdef, now 'sweeporder' corresponds to the dict's position in the list.
                {'var_name':specifiers.VOLTAGE+'B', 'sweep_type':'LIN', 'value_def':[0,1,11]},
                {'var_name':specifiers.VOLTAGE+'C', 'sweep_type':'CON', 'value_def':[1]},
                {'var_name':specifiers.VOLTAGE+'E', 'sweep_type':'CON', 'value_def':[0]}
            ]
            sweepdef = [
                {'var_name':specifiers.VOLTAGE+'B', 'sweep_order':1, 'sweep_type':'LIN' , 'value_def':[0,1,11]},
                {'var_name':specifiers.VOLTAGE+'C', 'sweep_order':1, 'sweep_type':'SYNC', 'master':specifiers.VOLTAGE+'B', 'offset':0.1}
                {'var_name':specifiers.VOLTAGE+'E', 'sweep_order':2, 'sweep_type':'CON' , 'value_def':[0]}
            ]

    outputdef  : List[str] or Set[str] , optional
        A list of the variables that shall be computed. Example: [specifiers.CURRENT+'C',specifiers.CURRENT+'B']

    othervar   : Dict[str, float], optional
        A dict whose 'key':'value' pairs specify variables that do not need to be included in the sweepdef parameter as they should be constants.
        Example: {:py:const:`~DMT.core.specifiers.TEMPERATURE`:300,'w':10}

    SweepDefClass : Type, optional
        From this class the sweep def objects are created and the SweepDefClass checks the sweep type.
        The user can supply subclasses of :class:`~DMT.core.sweep.SweepDef` here to allow custom sweep types.

    Methods
    -------
    check_sweep()
        Checks the sweep for correctness with regards to its definition and logical consistency. Also takes care of the master - sync logic.

    get_hash()
        Returns a hash corresponding to a Sweep object.

    create_df()
        Returns an prepared :class:`~DMT.core.DataFrame` with all columns from the sweep definitions and output variables. The sweep definition columns are already prefilled.

    set_values()
        Fills all the values inside the sweepdef object list.

    get_temperature()
        Returns the reference temperature of the sweep to simulate. Mostly used for key generation.

    Attributes
    ----------
    sweepdef  : List[SweepDef]
        Defines the sweep including variables, sweeptypes and sweeporders.

    outputdef  : List[str]
        Defines which quantities need to be calculated.

    othervar   : Dict[str, float]
        Optional variables.

    name       : string
        The sweep will be saved as name + hash using this string.
    """

    def __init__(
        self,
        name: str,
        sweepdef: Optional[List[Union[SweepDef, Mapping[str, object]]]] = None,
        outputdef: Optional[
            Union[List[Union[SpecifierStr, str]], Set[Union[SpecifierStr, str]]]
        ] = None,
        othervar: Optional[Mapping[str, float]] = None,
        SweepDefClass: Type = SweepDef,
    ):
        self.name = name
        self.df = None

        if SweepDefClass is None:
            SweepDefClass = SweepDef
        self.SweepDefClass = SweepDefClass

        self._sweepdef = []
        if sweepdef is not None:
            self.sweepdef = sweepdef

        # variables that need to be calculated by the simulator
        self._outputdef = []
        if outputdef is not None:
            self.outputdef = outputdef

        self._othervar = {}
        if othervar is not None:
            self.othervar = othervar

        if self._sweepdef != []:
            self.check_sweep()

    @property
    def sweepdef(self):
        """Get the sweepdef

        Returns
        -------
        List[SweepDef]
            Saved sweepdef
        """
        return self._sweepdef

    @sweepdef.setter
    def sweepdef(self, sweepdef_new: Optional[List[Union[SweepDef, Mapping[str, object]]]]):
        """New sweepdef

        Parameters
        ----------
        sweepdef_new : Optional[List[Union[SweepDef, Mapping[str, object]]]]
            Sweepdef to set
        """
        self._sweepdef = []
        for swd in sweepdef_new:
            if isinstance(swd, self.SweepDefClass):
                self._sweepdef.append(copy.deepcopy(swd))
            else:
                self._sweepdef.append(self.SweepDefClass(**swd))

    @property
    def othervar(self):
        return self._othervar

    @othervar.setter
    def othervar(self, othervar_new):
        if isinstance(othervar_new, dict):
            # optional variables such as temperature
            # copy to be save
            # sort to save some repeatings
            self._othervar = dict(
                sorted(copy.deepcopy(othervar_new).items(), key=lambda ele: ele[0])
            )
        else:
            raise IOError(
                "sweep.othervar must to be a dict. Example: {",
                "TEMP:300,",
                "w:10,",
                "l:0.25}",
            )

    @property
    def outputdef(self):
        return self._outputdef

    @outputdef.setter
    def outputdef(self, outputdef_new):
        if isinstance(outputdef_new, (list, set)):
            # cast and copy to be save
            # sort to save some repeatings
            self._outputdef = sorted(list(copy.deepcopy(outputdef_new)))
        else:
            raise IOError("sweep.outputdef must to be a list or a set.")

    def create_df(self):
        """Fill the dataframe according to the sweepdefinition

        Returns
        -------
        :class:`DMT.core.DataFrame`
            A pandas dataframe object that corresponds to the specified sweep. Values that need to be calculated are filled with numpy.nan .
        """

        # check and clean sweep---------------------------------------------------------------------------
        self.check_sweep()

        # create concrete values for each sweepvariable---------------------------------------------------
        self.set_values()

        # add the concrete sweep values into the df -------------------------------------------------------
        columns = []
        values_per_subsweep = []
        for subsweep in self.sweepdef:
            if not subsweep.sweep_type == "SYNC":
                columns.append(subsweep.var_name)
                values_per_subsweep.append(list(subsweep.values))

        # sweepdefs are a tree...
        # use itertools product to generate all possible combinations in the correct order
        # https://docs.python.org/3.6/library/itertools.html#itertools.product
        values = product(*values_per_subsweep)
        self.df = DataFrame(values, columns=columns)

        # do we have a synced variable? If yes, also generate this column
        for subsweep in self.sweepdef:
            if subsweep.sweep_type == "SYNC":
                n = (
                    self.df.shape[0] / subsweep.values.size
                )  # number of times this array is repeated in the final sweep

                if n == 1:
                    self.df[subsweep.var_name] = subsweep.values
                else:
                    self.df[subsweep.var_name] = np.repeat(subsweep.values, int(n))

        # add the output variables and fill them with Nans-------------------------------------------------
        for output in self.outputdef:
            if not output in self.df.columns:
                self.df[output] = np.NaN

        # add the optional variables and fill them---------------------------------------------------------
        for key, value in self.othervar.items():
            self.df[key] = value

        logging.info(
            "---------------------------------------------\nCreated a data frame with %d elements:\n%s \n---------------------------------------------",
            self.df.shape[0],
            self.df,
        )

        return self.df

    def check_sweep(self):
        """Checks a sweep for correctness.

        check_sweep() has the following features:

        - checks the specified sweep type and converts it to a non-misunderstandable format.
        - corrects the sweep_order
        - sets offset for SYNC
        - checks if non-optional variables are specified
        - corrects the variable names according to DMT format

        Returns
        -------
        :class:`DMT.core.Sweep`
            corrected and checked Sweep object.
        """

        # correct sweeporder------------------------------------
        if any([swd.sweep_order is None for swd in self.sweepdef]):
            # no extra ordering given, set it automatically
            # also set some stuff of synced sweeps here
            sweep_order = 1
            for i_swd, swd in enumerate(self.sweepdef):
                if swd.sweep_type != "SYNC":  # first all non synced
                    self.sweepdef[i_swd].sweep_order = sweep_order
                    sweep_order += 1

            for i_swd, swd in enumerate(self.sweepdef):
                if swd.sweep_type == "SYNC":  # now the synced
                    # we now are sure, that the master sweep order is set.
                    # search for master sweepdef
                    try:
                        self.sweepdef[i_swd].sweep_order = next(
                            swd_.sweep_order
                            for swd_ in self.sweepdef
                            if swd_.var_name == swd.master_var
                        )
                    except StopIteration as err:
                        raise IOError(
                            "DMT -> Sweep: Master sweep does not exist. Check your sweepdef!."
                        ) from err

        # if one sweep_order is missing, the error is risen here: Compare None to int is not defined!
        self.sweepdef = sorted(self.sweepdef, key=lambda swd: swd.sweep_order)

        # synced sweepdef stuff:
        for i_swd, swd in enumerate(self.sweepdef):
            if (
                swd.sweep_type == "SYNC" and swd.master is None
            ):  # if it was done already, swd.master is set
                # search for master sweepdef
                try:
                    self.sweepdef[i_swd].master = next(
                        swd_ for swd_ in self.sweepdef if swd_.var_name == swd.master_var
                    )
                except StopIteration as err:
                    raise IOError(
                        "DMT -> Sweep: Master sweep does not exist. Check your sweepdef!."
                    ) from err

                # tell the master that it has a synced sweepdef
                self.sweepdef[i_swd].master.sync = swd

                # if it uses a variable as offset find the sweepdef for this!
                if swd.offset_var is not None:
                    self.sweepdef[i_swd].offset = next(
                        swd_ for swd_ in self.sweepdef if swd_.var_name == swd.offset_var
                    )

        # check if non-optional variables are specified
        if specifiers.TEMPERATURE not in self.othervar:
            if specifiers.TEMPERATURE not in [element.var_name for element in self.sweepdef]:
                raise IOError(
                    "Non optional variable TEMP is not specified. TEMP is the temperature of the transistor."
                )

        # make sure that every variable is only once in in sweepdef and also othervar
        vars_all = [element.var_name for element in self.sweepdef] + list(self.othervar.keys())
        if len(vars_all) != len(set(vars_all)):
            raise IOError(
                "The Variable TEMP is specified more than once, this is forbidden for DMT. TEMP is the temperature of the transistor."
            )

    def get_temperature(self):
        """Returns the temperature of the sweep as a string. Use this to set the key of a dut.

        Returns
        -------
        str
            - Single temperature: "Txxx.xxK"
            - List of temperatures: "T(xxx.xx,yyy.yy,...)K"
            - Range of temperatures: "T[xxx.xx-sss.ss-yyy.yy]K", s is the step
        """
        if specifiers.TEMPERATURE in self.othervar:  # would be the easieast...
            return "T{0:.2f}K".format(self.othervar[specifiers.TEMPERATURE])

        # search sweep for temperature
        for swd in self.sweepdef:
            if swd.var_name == specifiers.TEMPERATURE:
                if swd.sweep_type == "CON":
                    return "T{0:.2f}K".format(swd.value_def[0])
                elif swd.sweep_type == "LIN":
                    return "T[{0:.2f}-{2:.2f}-{1:.2f}]K".format(*swd.value_def)
                elif swd.sweep_type == "LIST":
                    return "T(" + ",".join(["{0:.2f}".format(val) for val in swd.value_def]) + ")K"
                else:
                    raise NotImplementedError(
                        "The temperature of a sweep of type "
                        + swd.sweep_type
                        + " can not be converted into a valid key part until now."
                    )

    def get_hash(self):
        """Returns a hash for this sweep.

        Returns
        -------
        str
            MD5 hash that corresponds to this sweep.
        """
        sweep_string = " ".join([str(self.sweepdef), str(self.outputdef), str(self.othervar)])
        return create_md5_hash(sweep_string)

    def set_values(self):
        """Set the values of sweep according to the DMT definition."""
        for subsweep in self.sweepdef:
            subsweep.set_values()

        return self

    def __eq__(self, other):
        """Comparing two sweeps"""
        try:
            return self.get_hash() == other.get_hash()
        except AttributeError:
            return NotImplemented

    @classmethod
    def get_sweep_from_dataframe(
        cls,
        data: DataFrame,
        temperature: Optional[float] = None,
        name: str = "sweep",
        outputdef: Optional[List[str]] = None,
        othervar: Optional[Dict[str, float]] = None,
        SweepDefClass: Type = SweepDef,
        decimals_potentials: int = 3,
        **kwargs
    ):
        """Create a Sweep from a DataFrame

        Parameters
        ----------
        data : DataFrame
            data to create a Sweep from.
        temperature : float | None, optional
            Temperature in Kelvin, if not given it must be part of othervar, by default None
        name : str, optional
            Name of the sweep to create, by default "sweep"
        outputdef : List[str] | None, optional
            outputdef of the new Sweep, by default None
        othervar : Dict[str, float] | None, optional
            othervar of the new Sweep, by default None
        SweepDefClass : Type, optional
            SweepDefClass for the new sweepdefs, by default SweepDef
        decimals_potentials : int, optional
            Round to x number of decimals for potentials and frequencies, by default 3

        Returns
        -------
        Sweep
            Created sweep from the dataframe
        """
        if othervar is None:
            othervar = {}
        if temperature is not None:
            othervar[specifiers.TEMPERATURE] = temperature

        if outputdef is None:
            outputdef = []

        sweepdefs = get_sweepdef(data, decimals_potentials=decimals_potentials, **kwargs)

        ### grab definition for the frequency, if possible
        if specifiers.FREQUENCY in data.columns:
            freq = np.unique(np.round(data[specifiers.FREQUENCY].to_numpy(), decimals_potentials))
            sweepdefs.append(
                {
                    "var_name": specifiers.FREQUENCY,
                    "sweep_order": len(sweepdefs) + 1,
                    "sweep_type": "LIST",
                    "value_def": freq,
                },
            )

        return cls(
            name,
            sweepdef=sweepdefs,
            outputdef=outputdef,
            othervar=othervar,
            SweepDefClass=SweepDefClass,
        )
