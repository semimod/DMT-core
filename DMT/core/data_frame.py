""" data_frame module

Implements a extended pandas.DataFrame. It is based on the pandas.DataFrame and extended by many special methods that simplify working with electrical quantities.
This includes easy management of small signal parameter and other quantities which can be calculated from them.

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
import numpy as np
import re
import logging
import copy
from scipy.optimize import curve_fit
from DMT.exceptions import UnknownColumnError
from DMT.core import (
    specifiers_ss_para,
    get_specifier_from_string,
    specifiers,
    SpecifierStr,
    sub_specifiers,
    set_col_name,
    get_nodes,
    get_sub_specifiers,
    flatten,
    DataProcessor,
)
import pandas as pd

# pylint: disable = too-many-lines

# helper functions for Y Parameter smoothing
def fun_re(freq, a1, a2, a3):
    """Fit function for real Y Parameters normalized."""
    omega_sq = (2 * np.pi * freq) ** 2
    return (a1 + a2 * omega_sq) / (1 + a3 * omega_sq)


def fun_im(freq, a2, a3):
    """Fit function for imaginary Y Parameters normalized to omega."""
    omega = 2 * np.pi * freq
    omega_sq = omega**2
    return (a2) / (1 + a3 * omega_sq)


class Series(pd.Series):

    _metadata = ["processor"]

    @property
    def _constructor(self):
        return Series

    @property
    def _constructor_expanddim(self):
        return DataFrame


class DataFrame(DataProcessor, pd.DataFrame):
    """Two-dimensional size-mutable, potentially heterogeneous tabular data structure for electrical data with labeled axes (rows and columns).

    The primary DMT data structure. This class inherits from pandas.DataFrame and from the Mixin class DataProcessor.

    The inheritance from pandas is implemented according `to <http://pandas.pydata.org/pandas-docs/stable/extending.html#extending-subclassing-pandas>`.

    The inheritance from Mixin class DataProcessor is implemented according `to <http://www.qtrac.eu/pyagg.html>`.

    Note that pandas DataFrames are not always mutable and hence class methods that modify the DataFrame should be called like this::

        df = df.calc_ft()

    Methods
    -------
    convert_n_port_para(p_from='', p_to='', z0=float(50), ports=None)
        convert the small signal parameters of type p_from to small signal parameters of type p_to.
    cmplx2real()
        find all complex columns in self and split them up into one column for the real and one column for the complex part.
    real2cmplx()
        find all associated columns that contain real and imaginary parts and merge them into one column that holds complex numbers.
    clean_data(nodes, fallback=None, specifier_voltage=specifiers.VOLTAGE, specifier_current=specifiers.CURRENT, specifier_capacitance=specifiers.CAPACITANCE, specifier_frequency=specifiers.FREQUENCY, specifier_temperature=specifiers.TEMPERATURE)
        convert a DataFrame into the DMT format, e.g. use specifiers for the column names, drop unknown or unncessary columns and so on.
    clean_names( specifier_voltage=specifiers.VOLTAGE, specifier_current=specifiers.CURRENT, specifier_capacitance=specifiers.CAPACITANCE, specifiers_ss_parameter=specifiers.SPECIFIERS_SS_PARA)
        convert all column names into a nicer format.
    get_col_name(specifier, *nodes, sub_specifiers='')
        get the content of the column specified.y by the input to this method.
    ensure_specifier_column(specifier, *nodes, sub_specifiers=None, ports=None)
        make sure that the specifier specified by the arguments exists in the DataFrame.
    create_voltage(nodes, sub_specifiers=None)
        Try to create the voltage between nodes and save it into self.
    create_potential(nodes, sub_specifiers=None)
        Try to create the potential at node and save it into self.
    drop_all_voltages()
        Delete all voltages (but keep potentials).
    get_all_voltages()
        Return all voltages.
    parallel_norm(n_parallel, port_1, port_2)
        Normalize Currents and small signal parameters assuming that n_parallel devices have been measured.
    deembed_short(df_short, ports)
        perform a short deembeding of self with df_short.
    deembed_open(df_open, ports)
        perform an open deembeding of self with df_short.
    deembed(df_open, df_short, ports=None)
        perform open short deembeding of self with df_short and df_open.
    determine_mres()
        assume that self contains measurements of short structures. determine the metallization resistances using polyfits.
    deembed_DC(df_short_dc)
        perform DC deembeding of the currents in self, assuming that the metallization resistances can be calculated from df_short_dc.
    check_ss_cols(para)
        check if the small signal parameters para are existent in self.
    get_ss_para(para, port_1, *ports_n)
        return the small signal parameter in self.
    set_ss_para(para, para_values, port_1, *ports_n)
        set the small signal parameters para to self.
    strip_ss_para(keep='S')
        remove all small signal parameters except those specified by the keep argument.
    get_all_ss_para()
        return all small signal parameters in self.
    calc_ft(port_1, port_2)
        calculate ft using the spot frequency method.
    calc_fmax(port_1, port_2)
        calculate fmax from msg.
    calc_msg(port_1, port_2)
        calculate msg and save into self.
    calc_unilateral_gain(port_1, port_2)
        calculate u and save into self.
    calc_mag(port_1, port_2)
        calculate mag and save into self.
    calc_k(port_1, port_2)
        calculate k and save into self.
    calc_cbe()
        calculate cbe and save into self.
    calc_cbc()
        calculate cbc and save into self.
    calc_beta()
        calculate beta and save into self.
    calc_gm()
        calculate gm and save into self.
    """

    _metadata = ["processor"]
    processor = DataProcessor()

    @property
    def _constructor(self):
        DataFrame.processor = DataProcessor()
        return DataFrame

    @property
    def _constructor_sliced(self):
        Series.processor = DataProcessor()
        return Series

    def repeat_rows(self, count):
        """Repeats the DataFrame rows by the number count.

        Parameters
        ----------
        count : int
            Number of repeats per row.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe with repeated rows
        """
        data_new = []
        for row in self.itertuples(index=False, name=None):
            for _nr in range(count):
                data_new.append(row)

        df_new = DataFrame(columns=self.columns, data=data_new)

        return df_new

    def convert_n_port_para(self, p_from="", p_to="", z0=float(50), ports=None):
        """Convert between the small signal parameters S,Y,Z,T,A stored in self.

        Parameters
        ----------
        p_from  :  string
            String that specifies which parameters are already present in self.

        p_to    :  string
            String that specifies which parameters should be created in self.

        z0      : float()
            Reference impedance in ohms, default is float(50).

        ports   : [str], optional
            Name of the ports in correct order. Defaults to ['1', '2'], for a BJT in common-emitter this would be ['B', 'C'].

        Returns
        -------
        self       :  :class:`DMT.core.DataFrame`
            Dataframe that contains the p_to n_port parameters
        """
        if ports is None:
            ports = ["1", "2"]

        # find the number of ports from available columns in df
        para = self.get_ss_para(p_from, ports[0], *ports[1:])
        para_new = self.processor.convert_n_port_para(para, p_from, p_to)

        # save the new parameters into the df
        return self.set_ss_para(p_to, para_new, ports[0], *ports[1:])

    def cmplx2real(self):
        """Create real and imaginary columns from complex columns in DataFrame.

        Returns
        -------
        self       :  :class:`DMT.core.DataFrame`
            Dataframe that contains real and imag columns instead of cmplx columns.

        """
        # find complex variables
        cmplx_cols = []
        for column in self.columns:  # pylint: disable=not-an-iterable
            # this column contains an explicit real part
            if self[column].to_numpy().dtype in ["cmplx128", np.dtype("complex128")]:
                cmplx_cols.append(column)

        # delete unncessary variables
        for var in cmplx_cols:
            self["R:" + var] = np.real(self[var].to_numpy())
            self["I:" + var] = np.imag(self[var].to_numpy())
            self = self.drop(columns=[var])

        return self

    def real2cmplx(self):
        """Add real and imaginary columns in DataFrame to complex columns.

        Returns
        -------
        self :  :class:`DMT.core.DataFrame`
            Dataframe that contains cmplx columns instead of seperate real and imag columns.

        """
        # find complex variables
        cmplx_vars_old, cmplx_vars_speci = [], []
        for column in self.columns:  # pylint: disable=not-an-iterable
            # this column contains an explicit real part
            if "R:" in column:
                cmplx_vars_old.append(column[2:])
            if sub_specifiers.REAL in column:
                cmplx_vars_speci.append(column[:-5])

        # delete unnecessary variables
        # vairables in oldschool grammar
        for var in cmplx_vars_old:
            pd.options.mode.chained_assignment = None  # default='warn'
            self[var] = self["R:" + var].to_numpy() + 1j * self["I:" + var].to_numpy()
            self = self.drop(columns=["R:" + var])
            self = self.drop(columns=["I:" + var])

        # variables in specifier grammar
        for var in cmplx_vars_speci:
            pd.options.mode.chained_assignment = None  # default='warn'
            try:  # sometimes we have mixed AC specifiers (e.g. Y_CB, Y_CB|REAL but no Y_CB|IMAG), then this will fail. but it is ok.
                self[var] = (
                    self[var + sub_specifiers.REAL].to_numpy()
                    + 1j * self[var + sub_specifiers.IMAG].to_numpy()
                )
            except KeyError:
                pass
            try:
                self = self.drop(columns=[var + sub_specifiers.REAL])
            except KeyError:
                pass
            try:
                self = self.drop(columns=[var + sub_specifiers.IMAG])
            except KeyError:
                pass

        return self

    def clean_data(
        self,
        nodes,
        reference_node,
        fallback=None,
        ac_ports=None,
        specifier_voltage=specifiers.VOLTAGE,
        specifier_current=specifiers.CURRENT,
        specifier_capacitance=specifiers.CAPACITANCE,
        specifier_frequency=specifiers.FREQUENCY,
        specifier_temperature=specifiers.TEMPERATURE,
        warnings=True,
    ):
        """Clean DataFrame.  This is one of the most important methods and should be called on all imported data. This ensures data consistency within DMT!

        Clean a DataFrame. This means:

        * make sure all potentials and voltages of the dut are stored correctly
        * convert separate real and imaginary parts of complex numbers into a single cmplx128 number
        * assign a :class:`~DMT.core.specifiers.SpecifierStr` as column name if possible.

        If the nodes in the columns do not match with the nodes in the nodes parameter, the fallback dictionary is used to try and rename the nodes.


        Parameters
        ----------
        nodes  :  [str]
            List of strings with the node names.
        fallback  :  {string:string, specifier_frequency:'FREQ', specifier_temperature='TEMP'}
            A dict that can be used to remap nodes in the file to nodes parameter. The keys of this dict are
            node names that may be errorneous or duplicate in the DataFrame and the values are the actual correct node
            names, according to DMT specifiers. E.g. one may have a voltage V_C1 in the DataFrame, but it should actually be V_C. Then fallback={'C1':'C'}
            will save the day. So the key is the current column name and the value the desired column name.
            The specifier_frequency and specifier_temperature are set to this dictionary.
            If the value of a key in this dict is None, the column will be dropped.

        ac_ports : [str]
            List that specifies the connection of the AC ports. E.g. ['B','C'] for common emitter.
        specifier_voltage : str
            Specifier for the voltage, defaults to 'V'
        specifier_current : str
            Specifier for the voltage, defaults to 'I'
        specifier_capacitance : str
            Specifier for the voltage, defaults to 'C'
        specifier_frequency : str
            Specifier for the frequency, defaults to 'FREQ'
        specifier_temperature : str
            Specifier for the column names in the measurements. Can be used to identify variables which have different names in the measurements.
            Inside of DMT the given default names are assumed to be valid and hence they can be renamed using these specifiers.
            Voltages, currents and capacitances are renamed in :meth:`~DMT.core.data_frame.DataFrame.clean_names`,
            temperature and frequency are set as fallbacks for :meth:`~DMT.core.naming.get_nodes`, defaults to 'TEMP'

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains columns according to the DMT internal standard.

        Examples
        --------

        >>> df.columns
        ['V_BE','V_c','V_c_','I_B']
        >>> df.clean_data('B', 'E', {'c_':'C'})
        >>> df.columns
        ['V_B','V_E','V_C','I_B'] # the second V_c_ got deleted in this case

        Notes
        -----
        ..todo: fall also needs to be cast to upper()
        """
        # ensure cmplx variables
        self = self.real2cmplx()

        if fallback is None:
            fallback = {}

        # clean the notation
        self = self.clean_names(
            specifier_voltage=specifier_voltage,
            specifier_current=specifier_current,
            specifier_capacitance=specifier_capacitance,
            ignore=fallback.keys(),
        )

        if fallback is None:
            fallback = {}
        fallback[specifier_temperature] = specifiers.TEMPERATURE
        fallback[specifier_frequency] = specifiers.FREQUENCY

        # rename columns that are specified by fallback
        new_df = DataFrame()
        unknown_columns = []
        for col in self.columns:
            if col in fallback.keys():
                # the complete column name is in the fallback. So use it!
                if fallback[col] is None:
                    if warnings:
                        logging.warning(
                            "The column %s is dropped as it is in the fallback dictionary!", col
                        )
                    # drop it!
                elif fallback[col]:
                    if warnings:
                        logging.warning(
                            "The column %s is kept as %s according to the fallback dictionary!",
                            col,
                            fallback[col],
                        )
                    new_df[fallback[col]] = self[col]
                else:
                    if warnings:
                        logging.warning(
                            "The column %s is kept it was according to the fallback dictionary!",
                            col,
                        )
                    new_df[col] = self[col]

                continue

            if re.search(r"deemb", col, re.IGNORECASE):
                raise IOError(
                    "Found a possible already deembeded column. This column must be dropped for DMT! To do that add the following to the fallback: {{'{0:s}': None}}".format(
                        col
                    )
                )

            if col[0] in specifiers_ss_para:
                if "1" in fallback and "2" in fallback:  # already in fallback ?
                    pass
                try:
                    fallback["1"] = ac_ports[0]
                    fallback["2"] = ac_ports[1]
                except KeyError:
                    raise IOError(
                        "DMT->DataFrame->clean_data: The column"
                        + str(col[0])
                        + " was identified as a small-signal parameter but the ac_ports argument was not specified."
                    )

            elif col[0] not in "VIC":
                # only rename the names of values which can be identified
                new_df[col] = self[col]
                continue

            nodes_in_col = get_nodes(col, nodes, fallback=fallback)
            sub_specifiers_in_col = get_sub_specifiers(col)
            # if more than 3 nodes, something is weird and we dont do anything
            # if len(nodes_in_col)>2:
            #     # only rename the names of values which can be identified
            #     new_df[col] = self[col]
            #     continue
            if nodes_in_col is None:
                continue
            elif nodes_in_col:
                # new_column_name = col[0] + r'_' + ''.join(nodes_in_col)
                new_column_name = SpecifierStr(
                    col[0], *nodes_in_col, sub_specifiers=sub_specifiers_in_col
                )
                # self  =  self.rename(columns={ self.columns[i]:new_column_name })
                if new_column_name in new_df.columns:  # pylint: disable=unsupported-membership-test
                    raise IOError(
                        "Column is already in the dataframe. Maybe it should be deleted? (fallback: {"
                        + new_column_name
                        + " :None})"
                    )
                new_df[new_column_name] = self[col]
            else:
                unknown_columns.append(col)

        if len(unknown_columns) > 1:
            str_columns = ""
            for col in unknown_columns:
                str_columns += " " + str(col) + " "

            raise UnknownColumnError(
                "The columns "
                + str_columns
                + " is unknown to this DuT as the nodes can not be extracted! Either a fallback behavior or different DuT nodes for this column are needed."
            )

        self = new_df

        # convert voltages, potentials and maybe in the future to SpecifierStr
        to_rename = {}
        temp_nodes = nodes + [
            key for key, value in fallback.items() if value == ""
        ]  # for this case also the "keep"-nodes from the fallback are possible
        for column in self.columns:  # pylint: disable=not-an-iterable
            specifier_col = get_specifier_from_string(column, temp_nodes)
            to_rename[column] = specifier_col

        self = self.rename(index=str, columns=to_rename)

        # set reference potential
        self.create_potential([reference_node], reference_node)

        # find all existing potentials and voltages and clean their name
        potentials = []
        voltages = []
        for column in self.columns:
            try:
                if column.specifier == specifiers.VOLTAGE:
                    # decide wether this colum contains a potential or a voltage
                    if len(column.nodes) == 1:
                        potentials.append(column)
                    elif len(column.nodes) == 2:
                        voltages.append(column)
                    elif len(column.nodes) == 0:
                        logging.warning(
                            "DMT -> Data_manager: Encountered voltage %s that corresponds to an unkown node. Skipping.",
                            column,
                        )
                        continue
                    else:
                        raise OSError(
                            "error: found voltage with name "
                            + column
                            + " in .mdm file that contains more than two node names!"
                        )

            # only works with specifiers
            except AttributeError:
                pass

        # get the potentials (nodes are known at this point), voltages later if-needed
        # find missing potentials
        possible_potentials = [SpecifierStr(specifiers.VOLTAGE, node) for node in nodes]
        missing_potentials = [
            potential for potential in possible_potentials if potential not in potentials
        ]
        if len(missing_potentials) == 0 or len(potentials) == 0:
            return self  # probably no voltage specified...

        # try to create all potentials that can be deduced from the voltages:
        for potential in missing_potentials:
            # find voltage that contains the potential's node
            try:
                # sometimes voltages with sub_specifiers are present in the data. We don't use these voltages here.
                self.create_potential(potential.nodes, reference_node)
            except IOError:
                # sometimes it may be impossible to create the potentials this way.
                # Assume e.g. V_S is missing and we dont have any voltage that contains the S node
                # Then we will just live with a missing potential.
                continue

        # remove the voltages
        self = self.drop(columns=voltages)

        return self

    # pylint: disable=dangerous-default-value
    def clean_names(
        self,
        specifier_voltage: str = specifiers.VOLTAGE,
        specifier_current: str = specifiers.CURRENT,
        specifier_capacitance: str = specifiers.CAPACITANCE,
        specifiers_ss_parameter=specifiers_ss_para,
        ignore: list = None,
    ):
        r"""Clean column names of DataFrame.

        Clean the column names of DataFrame into the DMT standard:

        * Goal is to have all column names as a :class:`~DMT.core.specifiers.SpecifierStr`.
        * potentials and voltages start with 'V\_'
        * currents start with 'I\_'
        * capacitances start with 'C\_'

        Specifier for the column names in the measurements. Can be used to identify variables which have different names in the measurements.
        Inside of DMT the given default names are assumed to be valid and hence they can be renamed using these specifiers.


        Parameters
        ----------
        specifier_voltage : str, optional
            Indicator for voltages in the measurements, by default specifiers.VOLTAGE
        specifier_current : str, optional
            Indicator for currents in the measurements, by default specifiers.CURRENT
        specifier_capacitance : str, optional
            Indicator for capacitances in the measurements, by default specifiers.CAPACITANCE
        specifiers_ss_parameter : optional
            Small signal parameters in the measurements, by default specifiers_ss_para
        ignore : list, optional
            Columns in the measurements to ignore, by default None

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains columns with names according to the DMT internal standard.
        """
        if ignore is None:
            ignore = []

        for i, column in enumerate(self.columns):
            if column in ignore:
                continue

            column = column.upper()
            try:
                if not column[1] == ":":  # Not an real or imaginary part of something
                    if column.startswith(specifier_voltage):  # is this a potential or voltage?
                        if column[1] != "_":
                            column = "V_" + column[1:]
                        else:
                            column = "V" + column[1:]
                    elif column.startswith(specifier_current):  # is this a current
                        if column[1] != "_":
                            column = "I_" + column[1:]
                        else:
                            column = "I" + column[1:]
                    elif column.startswith(specifier_capacitance):  # is this a capacitance
                        if column[1] != "_":
                            column = "C_" + column[1:]
                        else:
                            column = "C" + column[1:]
                    elif re.search(r"[(]([0-9]+),([0-9]+)[)]", column):
                        if column[0] in specifiers_ss_parameter and column[1] == "(":
                            ports = re.search(r"[(]([0-9]+),([0-9]+)[)]", column)

                            column = SpecifierStr(column[0], *[ports.group(1), ports.group(2)])

                self = self.rename(
                    columns={self.columns[i]: column}
                )  # pylint: disable=unsubscriptable-object

            except IndexError:
                pass

        return self

    def get_col_name(self, specifier, *nodes, sub_specifiers=""):
        """Checks if a column with the given combination of specifier and nodes exists in the given dataframe using the DMT naming style.

        Parameters
        ----------
        specifier : str
            Ideally a specifier from :mod:`~DMT.core.specifiers`
        *nodes : str, optional
            Nodes for the column. Like 'B' for base or 'B', 'E' for base-emitter
        sub_specifiers : str, {'', :py:const:`DMT.core.sub_specifiers.PERIMETER`, :py:const:`DMT.core.sub_specifiers.AREA`}

        Returns
        -------
        str
            If the column exists the name is returned.

        Raises
        ------
        KeyError
            If the column does not exist.
        """
        col = set_col_name(specifier, *nodes, sub_specifiers=sub_specifiers)
        if str(col) in self.columns:  # pylint: disable=unsupported-membership-test
            return col

        raise KeyError("The column '" + str(col) + "' is missing in the given data frame.")

    def ensure_specifier_column(
        self,
        specifier,
        *nodes,
        sub_specifiers_to_ensure=None,
        ports=None,
        reference_node=None,
        debug=False,
        area=None,
        force=False,
    ):
        """Checks if a column with the specifier name exists in the dataframe, if not it tries to calculate it!

        Parameters
        ----------
        specifier : str
            Ideally a specifier from :mod:`~DMT.core.specifiers`
        *nodes : str, optional
            Nodes for the column. Like 'B' for base or 'B', 'E' for base-emitter
        sub_specifiers : str, {'', :py:const:`DMT.core.sub_specifiers.PERIMETER`, :py:const:`DMT.core.sub_specifiers.AREA`}
            Subscript of the specifier symbol to ensure.
        ports        : [str], optional
            Name of the ports, for a BJT in common-emitter this is ['B', 'C', ...] . Only needed to calculate AC-Quantities.
        reference_node : str, optional
            Name of the common reference node, for a BJT in common-emitter this is 'E' . Only needed to calculate potentials.
        debug : bool, False
            If True, debug info is printed.
        area : float, None
            Specific area used to calculate area specific quantities.
        force : Bool, False
            If true: re-calculate specifier, even if already existing.

        Raises
        ------
        KeyError
            If the column does not exist.
        """
        if not self.columns.is_unique:
            self = self.loc[:, ~self.columns.duplicated()]
        col = set_col_name(specifier, *nodes, sub_specifiers=sub_specifiers_to_ensure)
        if col in self.columns and not force:  # pylint: disable=unsupported-membership-test
            return

        specifier = col.specifier
        nodes = col.nodes
        sub_specifiers_in_col = col.sub_specifiers

        if (
            sub_specifiers.REAL.sub_specifiers[0] in sub_specifiers_in_col
        ):  # catch them here before we enter the switch case below. This way we do not need to care about this below.
            col_complex = set_col_name(
                specifier,
                *nodes,
                sub_specifiers=[
                    spec for spec in sub_specifiers_in_col if spec != sub_specifiers.REAL[1:]
                ],
            )
            self.ensure_specifier_column(col_complex, ports=ports)
            self[col] = np.real(self[col_complex].to_numpy())

        elif (
            sub_specifiers.IMAG.sub_specifiers[0] in sub_specifiers_in_col
        ):  # [1:] to cut off the | for a correct string compare
            col_complex = set_col_name(
                specifier,
                *nodes,
                sub_specifiers=[
                    spec for spec in sub_specifiers_in_col if spec != sub_specifiers.IMAG[1:]
                ],
            )
            self.ensure_specifier_column(col_complex, ports=ports)
            self[col] = np.imag(self[col_complex].to_numpy())
            return
        elif (
            sub_specifiers.MAG.sub_specifiers[0] in sub_specifiers_in_col
        ):  # [1:] to cut off the | for a correct string compare
            col_complex = set_col_name(
                specifier,
                *nodes,
                sub_specifiers=[
                    spec for spec in sub_specifiers_in_col if spec != sub_specifiers.MAG[1:]
                ],
            )
            self.ensure_specifier_column(col_complex, ports=ports)
            self[col] = np.abs(self[col_complex].to_numpy())

        elif (
            sub_specifiers.PHASE.sub_specifiers[0] in sub_specifiers_in_col
        ):  # [1:] to cut off the | for a correct string compare
            col_complex = set_col_name(
                specifier,
                *nodes,
                sub_specifiers=[
                    spec for spec in sub_specifiers_in_col if spec != sub_specifiers.PHASE[1:]
                ],
            )
            self.ensure_specifier_column(col_complex, ports=ports)
            self[col] = np.angle(self[col_complex].to_numpy())
            return

        if (specifier == specifiers.VOLTAGE) and (len(nodes) == 2):
            try:
                self = self.create_voltage(
                    nodes,
                    reference_node=reference_node,
                    voltage_sub_specifiers=sub_specifiers_in_col,
                )
            except IOError as err:
                raise KeyError(
                    "The voltage '"
                    + str(col)
                    + "' and the needed potentials are missing in the given data frame and can not be calculated."
                ) from err
        elif (specifier == specifiers.VOLTAGE) and (len(nodes) == 1):
            try:
                self = self.create_potential(
                    nodes, reference_node, voltage_sub_specifiers=sub_specifiers_in_col, debug=debug
                )
            except IOError as err:
                raise KeyError(
                    "The potential '"
                    + str(col)
                    + "' and the needed voltages are missing in the given data frame and can not be calculated."
                ) from err

        elif specifier == specifiers.CURRENT_DENSITY:
            if area is None:
                raise IOError(
                    "DMT -> DataFrame -> ensure_specifier_column: area not given, but tried to calcualte current DENSITY. Abort."
                )
            self.loc[:, specifiers.CURRENT_DENSITY + nodes[0]] = (
                self[specifiers.CURRENT + nodes[0]] / area
            )
        elif (specifier == specifiers.CAPACITANCE) and (len(nodes) == 2):
            if ports is None:
                raise IOError(
                    'DMT -> DataFrame -> ensure_specifier_column: Calculation of a capacitance requires the specification of the "ports" keyword argument.'
                )
            if any(
                sub_specifier_poa.sub_specifiers[0] in sub_specifiers_in_col
                for sub_specifier_poa in [
                    sub_specifiers.PERIMETER,
                    sub_specifiers.AREA,
                    sub_specifiers.CORNER,
                    sub_specifiers.LENGTH,
                    sub_specifiers.WIDTH,
                ]
            ):
                raise IOError(
                    "DMT -> DataFrame -> ensure_specifier_column: Can not calculate a PoA capacitance. This needs to be done by a XQ Step."
                )

            try:
                if nodes[0] == "B" and nodes[1] == "E":  # CBE
                    self = self.calc_cbe(port_1=ports[0], port_2=ports[1])
                elif nodes[0] == "C" and nodes[1] == "E":  # CCE
                    self = self.calc_cce(port_1=ports[0], port_2=ports[1])
                elif nodes[0] == "B" and nodes[1] == "C":  # CBC
                    self = self.calc_cbc(port_1=ports[0], port_2=ports[1])
                else:
                    raise KeyError("The " + "".join(nodes) + " capacitance can not be calculated.")
            except IOError as err:
                raise KeyError(
                    "The " + "".join(nodes) + " capacitance could not be calculated."
                ) from err

        elif specifier == specifiers.TRANSIT_FREQUENCY:
            try:
                self = self.calc_ft(ports[0], ports[1])
            except IOError as err:
                raise KeyError(
                    "The transit frequency is missing in the given data frame and can not be calculated."
                ) from err
            except TypeError as err:
                raise IOError(
                    "The ac ports are not given, but transit frequency is beeing requested. Abort."
                ) from err

        elif specifier == specifiers.MAXIMUM_OSCILLATION_FREQUENCY:
            try:
                self = self.calc_fmax(ports[0], ports[1])
            except IOError as err:
                raise KeyError(
                    "Fmax is missing in the given data frame and can not be calculated."
                ) from err

        elif specifier == specifiers.MAXIMUM_AVAILABLE_GAIN:
            try:
                self = self.calc_mag(ports[0], ports[1])
            except IOError as err:
                raise KeyError(
                    "MAG is missing in the given data frame and can not be calculated."
                ) from err

        elif specifier == specifiers.MAXIMUM_STABLE_GAIN:
            try:
                self = self.calc_msg(ports[0], ports[1])
            except IOError as err:
                raise KeyError(
                    "MSG is missing in the given data frame and can not be calculated."
                ) from err

        elif specifier == specifiers.UNILATERAL_GAIN:
            try:
                self = self.calc_unilateral_gain(ports[0], ports[1])
            except IOError as err:
                raise KeyError(
                    "U is missing in the given data frame and can not be calculated."
                ) from err

        elif specifier == specifiers.TRANSIT_TIME:
            try:
                self.ensure_specifier_column(specifiers.TRANSIT_FREQUENCY, ports=ports)
                self[specifiers.TRANSIT_TIME] = 1 / (2 * np.pi * self[specifiers.TRANSIT_FREQUENCY])
            except IOError as err:
                raise KeyError(
                    "The transit time is missing in the given data frame and can not be calculated."
                ) from err
        elif specifier == specifiers.DC_CURRENT_AMPLIFICATION:
            try:
                self = self.calc_beta()
            except IOError as err:
                raise KeyError(
                    "The dc current amplification beta is missing in the given data frame and can not be calculated."
                ) from err
        elif specifier == specifiers.TRANSCONDUCTANCE:
            try:
                self = self.calc_gm()
            except IOError as err:
                raise KeyError(
                    "The transconductance is missing in the given data frame and can not be calculated."
                ) from err
        elif specifier in specifiers_ss_para:
            try:  # try tog et from S paras
                self = self.convert_n_port_para(p_from="S", p_to=specifier, ports=ports)
            except IOError as err:  # try to get from Y paras
                try:
                    self = self.convert_n_port_para(p_from="Y", p_to=specifier, ports=ports)
                except:
                    raise KeyError(
                        "The conversion from the S- and Y-Parameters to the small signal "
                        + specifier
                        + "-Parameters is missing.\n If possible add the conversion in the data processor!"
                    ) from err
            except KeyError as err:
                if ports is None:
                    raise KeyError(
                        "The small signal parameters "
                        + specifier
                        + "- and the S-Parameters are missing in the DataFrame.",
                        "Did you forget to pass the ports as ports=['B', 'C'] ?",
                    ) from err
                else:
                    raise KeyError(
                        "The small signal parameters "
                        + specifier
                        + "- and the S-Parameters are missing in the DataFrame."
                    ) from err

        else:
            raise KeyError(
                "The column '"
                + str(col)
                + "' is missing in the given data frame and no calculation for this column is implemented."
            )
        if not self.columns.is_unique:
            self = self.loc[:, ~self.columns.duplicated()]

    def create_voltage(self, nodes, voltage_sub_specifiers=None, reference_node=None):
        """Try to create col from existing data in dataframe df.

        Parameters
        ----------
        nodes  :  [node]
            List containing the nodes present in self or just directly list of nodes.
        sub_specifiers : [str]
            The sub specifier that shall be valid for the voltage to be created by this method.
        reference_node : str
            Reference node of the potentials, defaults to 'E'

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DMT.Dataframe with new dataframe, if successfull
        """
        if len(nodes) != 2:
            raise IOError(
                "DMT -> Data_manager: Tried to create column voltage but could not identify suitable potentials."
            )

        # create specifier for the new voltage
        col = set_col_name(specifiers.VOLTAGE, *nodes, sub_specifiers=voltage_sub_specifiers)

        # init specifiers for the potentials
        potential_0 = SpecifierStr(
            specifiers.VOLTAGE, nodes[0], sub_specifiers=voltage_sub_specifiers
        )
        potential_1 = SpecifierStr(
            specifiers.VOLTAGE, nodes[1], sub_specifiers=voltage_sub_specifiers
        )

        # ensure the existence of potentials
        self.ensure_specifier_column(potential_0, reference_node=reference_node)
        self.ensure_specifier_column(potential_1, reference_node=reference_node)

        # I think the setting with Copy Warning is broken here...
        pd.options.mode.chained_assignment = None  # default='warn'
        # calculate new column (voltage)
        self[col] = self[potential_0].to_numpy() - self[potential_1].to_numpy()
        pd.options.mode.chained_assignment = "warn"
        return self

    def get_all_voltages(self):
        """returns all voltages in the data frame.

        Returns
        -------
        list
            List containing all voltages present in self.columns as specifiers.
        """
        # iterate over columns and find voltages
        voltages = []
        for column in self.columns:  # pylint: disable=not-an-iterable
            try:
                if (column.specifier == specifiers.VOLTAGE) and (len(column.nodes) == 2):
                    voltages.append(column)
            except AttributeError:
                pass

        return voltages

    def get_all_potentials(self):
        """
        Returns
        -------
        list
            List containing all voltages present in self.columns as specifiers.
        """
        # iterate over columns and find voltages
        potentials = []
        for column in self.columns:  # pylint: disable=not-an-iterable
            try:
                if (column.specifier == specifiers.VOLTAGE) and (len(column.nodes) == 1):
                    potentials.append(column)
            except AttributeError:
                pass

        return potentials

    def get_all_nodes(self):
        """Gives a set of all nodes in voltages of a given df.

        Returns
        -------
        set
            Set containing all nodes of a given device.
        """
        # iterate over columns and find nodes
        nodes = set()
        for voltage in self.columns:  # pylint: disable=not-an-iterable
            if voltage.specifier == specifiers.VOLTAGE:
                if voltage.sub_specifiers == []:
                    nodes.update(set(voltage.nodes))
                else:
                    nodes.update(
                        set([node + str(voltage.sub_specifiers) for node in voltage.nodes])
                    )

        return nodes

    def create_potential(self, nodes, reference_node, voltage_sub_specifiers=None, debug=False):
        """Try to create col from existing data in dataframe df.

        Parameters
        ----------
        nodes  :  [node]
            List containing the nodes present in self or just directly list of nodes.
        reference_node : str
            Name of the reference node.
        voltage_sub_specifiers : [str]
            The sub specifier that shall be valid for the voltage to be created by this method.
        debug : bool, False
            If True, print out debugging information

        Returns
        -------
        df  : :class:`DMT.core.DataFrame`
            DMT.Dataframe with new dataframe, if successfull

        Raises
        ------
        IOError
            If it is not possible to create the potential
        """
        # init specifiers for the potentials
        potential = SpecifierStr(
            specifiers.VOLTAGE, nodes[0], sub_specifiers=voltage_sub_specifiers
        )

        try:
            reference_potential = SpecifierStr(
                specifiers.VOLTAGE, reference_node, sub_specifiers=voltage_sub_specifiers
            )
        except TypeError as err:
            raise IOError("DMT->data_frame: No or incompatible reference_node were given.") from err

        if reference_potential not in self.columns:  # pylint: disable=unsupported-membership-test
            potentials = self.get_all_potentials()
            # try create potential by faking different reference potential
            for potential in potentials:
                try:
                    self.create_potential(
                        [reference_node],
                        potential.nodes[0],
                        voltage_sub_specifiers=voltage_sub_specifiers,
                    )
                except IOError as err:
                    if (
                        "DMT->data_frame: Potentials and voltages are uncoupled -> can not create potential."
                        in err.args
                    ):
                        continue
                    else:
                        raise

            # is it set now?
            if reference_potential in self.columns:  # pylint: disable=unsupported-membership-test
                # it is set now -> shift all potentials so that the reference is 0
                if any(self[reference_potential]):
                    for potential_to_shift in self.get_all_potentials():
                        if (
                            potential_to_shift != reference_potential
                        ):  # this is the last one to shift...
                            self[potential_to_shift] = (
                                self[potential_to_shift] - self[reference_potential]
                            )

                    # now all potentials are relativ to the new reference....
                    self[reference_potential] = 0
            else:
                # all other potentials are independent of the reference or no potential is set -> create new reference as ground
                self[reference_potential] = 0

            # it can happen, that the potential is calculated as intermediate result...
            if potential in self.columns:  # pylint: disable=unsupported-membership-test
                return self

        if nodes[0] == reference_node:
            return self

        # is there a connection between all potentials and all voltages?
        voltages = self.get_all_voltages()
        nodes_in_potentials = [pot.nodes[0] for pot in self.get_all_potentials()]
        nodes_in_voltages = flatten([volt.nodes for volt in voltages])
        if not any(
            [node_in_voltages in nodes_in_potentials for node_in_voltages in nodes_in_voltages]
        ):
            raise IOError(
                "DMT->data_frame: Potentials and voltages are uncoupled -> can not create potential."
            )

        # is there a direct voltage?
        for voltage in voltages:
            potentials_in_voltage = [
                SpecifierStr(specifiers.VOLTAGE, node, sub_specifiers=voltage.sub_specifiers)
                for node in voltage.nodes
            ]
            if potential in potentials_in_voltage:
                for other_potential in [
                    SpecifierStr(specifiers.VOLTAGE, node, sub_specifiers=voltage.sub_specifiers)
                    for node in voltage.nodes
                    if node != nodes[0]
                ]:
                    # try to find a direct voltage from a other potential first
                    if (
                        other_potential in self.columns
                    ):  # pylint: disable=unsupported-membership-test
                        if nodes[0] == potentials_in_voltage[0].nodes[0]:
                            if debug:
                                print(
                                    "during setting of potential " + nodes[0] + " -> set potential"
                                )
                                print(
                                    str(potential)
                                    + " = "
                                    + str(voltage)
                                    + "+"
                                    + str(other_potential)
                                )
                            self[potential] = self[voltage] + self[other_potential]
                            break
                        else:
                            if debug:
                                print(
                                    "during setting of potential " + nodes[0] + " -> set potential"
                                )
                                print(
                                    str(potential)
                                    + " = "
                                    + str(other_potential)
                                    + "-"
                                    + str(voltage)
                                )
                            self[potential] = self[other_potential] - self[voltage]
                            break

        # did we reach our goal ?
        if potential in self.columns:  # pylint: disable=unsupported-membership-test
            return self

        # create other intermediate potential first and try again
        for voltage in voltages:
            potentials_in_voltage = [
                SpecifierStr(specifiers.VOLTAGE, node, sub_specifiers=voltage.sub_specifiers)
                for node in voltage.nodes
            ]
            if potential in potentials_in_voltage:
                other_potential = next(
                    SpecifierStr(specifiers.VOLTAGE, node, sub_specifiers=voltage.sub_specifiers)
                    for node in voltage.nodes
                    if node != nodes[0]
                )
                if (
                    other_potential not in self.columns
                ):  # pylint: disable=unsupported-membership-test
                    if debug:
                        print(
                            "during setting of potential "
                            + nodes[0]
                            + " -> will create "
                            + str(other_potential)
                        )
                    self.create_potential(
                        other_potential.nodes,
                        reference_node,
                        voltage_sub_specifiers=voltage_sub_specifiers,
                        debug=debug,
                    )

                    if nodes[0] == potentials_in_voltage[0].nodes[0]:
                        if debug:
                            print("during setting of potential " + nodes[0] + " -> set potential")
                            print(
                                str(potential) + " = " + str(voltage) + "+" + str(other_potential)
                            )
                        self[potential] = self[voltage] + self[other_potential]
                        break
                    else:
                        if debug:
                            print("during setting of potential " + nodes[0] + " -> set potential")
                            print(
                                str(potential) + " = " + str(other_potential) + "-" + str(voltage)
                            )
                        self[potential] = self[other_potential] - self[voltage]
                        break

        return self

    def drop_all_voltages(self):
        """Drops all found voltages (but ignores potentials)

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DMT.Dataframe with new dataframe, if successfull
        """
        to_drop = []
        # pylint: disable = not-an-iterable
        for col in self.columns:
            try:
                if col.specifier == specifiers.VOLTAGE and len(col.nodes) == 2:
                    to_drop.append(col)
            except AttributeError:  # if it is not a specifier we cant do anything
                pass

        return self.drop(labels=to_drop, axis=1)

    def parallel_norm(self, n_parallel, port_1, port_2):
        """Normalize the data in df with regard to the number of devices in parallel.

        This method normalizes S-parameters and currents with regard to the number
        of devices of the same geometry connected in parallel.

        Parameters
        ----------
        n_parallel    : int
            number of parallel devices
        port_1        : str
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : str
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DataFrame containing the normalized S parameters and currents.
        """
        # normalization of S parameters and deletion of all other parameters
        try:
            s_para_values = self.get_ss_para("S", port_1, port_2)
            s_para_values = DataFrame.processor.parallel_norm(s_para_values, n_parallel)
            self = self.set_ss_para("S", s_para_values, port_1, port_2)
        except StopIteration:
            pass

        # pylint: disable = not-an-iterable
        for col in self.columns:
            if specifiers.CURRENT in col:
                self[col] = self[col] / n_parallel

        return self

    def deembed_short(self, df_short, ports, times=1):
        """Deembed the measured data in df from the measured data in df_short.

        This method deembeds the measured small signal parameters in df using the measured small signal parameters in df_short.

        Parameters
        ----------
        df_short    :  :class:`DMT.core.DataFrame`
            df containing the S parameters of a short dummy.
        ports       :  [str]
            List of port names. Should be the same for the device and the open and short.  Usually this would be ['1', '2']. For a BJT in common emitter, should be ['B', 'C', ...]
        times       : int
            The number of times the short has to be removed.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DataFrame containing the de-embedded S parameters.
        """
        s_para_values = self.get_ss_para("S", *ports)
        s_para_short_values = df_short.get_ss_para("S", *ports)

        freq_short = df_short[specifiers.FREQUENCY]
        freq_self = self[specifiers.FREQUENCY]
        freq_self_unique = np.unique(freq_self)
        freq_short_unique = np.unique(freq_short)

        if np.all(freq_self_unique == freq_short_unique):  # frequencies match exactly
            s_para_values = DataFrame.processor.deembed_short(
                s_para_values, s_para_short_values, times=times
            )
        elif len(freq_short_unique) > len(
            freq_self_unique
        ):  # try to throw away frequencies in short
            indices_to_delete = [
                i for i, _freq in enumerate(freq_short_unique) if not _freq in freq_self_unique
            ]
            s_para_short_values = np.delete(s_para_short_values, indices_to_delete, 0)
            s_para_values = DataFrame.processor.deembed_short(
                s_para_values, s_para_short_values, times=times
            )

        # set the de-embedded parameters and remove un-necessary small signal parameters
        self = self.set_ss_para("S", s_para_values, *ports)
        self = self.strip_ss_para()
        return self

    def deembed_open(self, df_open, ports, times=1):
        """Deembed the measured data in df from the measured data in df_open.

        This method deembeds the masured small signal parameters in df using the measured small signal parameters in df_open.

        Parameters
        ----------
        df_open     :  :class:`DMT.core.DataFrame`
            df containgin the measured open structure.

        ports       :  [str]
            List of port names. Should be the same for the device and the open and short.
            Usually this would be ['1', '2']. For a BJT in common emitter, should be ['B', 'C', ...]
        times       :  int
            Numer of times the open has to be removed.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DataFrame containing the de-embedded S parameters.

        """
        try:
            s_para_values = self.get_ss_para("S", *ports)
            s_para_open_values = df_open.get_ss_para("S", *ports)

            freq_open = df_open[specifiers.FREQUENCY]
            freq_self = self[specifiers.FREQUENCY]
            freq_self_unique = np.unique(freq_self)
            freq_open_unique = np.unique(freq_open)

            if np.all(freq_self_unique == freq_open_unique):  # frequencies match exactly
                s_para_values = DataFrame.processor.deembed_open(
                    s_para_values, s_para_open_values, times=times
                )
            elif len(freq_open_unique) > len(
                freq_self_unique
            ):  # try to throw away frequencies in open
                indices_to_delete = [
                    i for i, _freq in enumerate(freq_open_unique) if not _freq in freq_self_unique
                ]
                s_para_open_values = np.delete(s_para_open_values, indices_to_delete, 0)
                s_para_values = DataFrame.processor.deembed_open(
                    s_para_values, s_para_open_values, times=times
                )

            else:
                raise IOError(
                    "DMT.core.DataFrame:Something went wrong during deembeeding. Maybe frequencies do not match."
                )
        except ValueError:
            raise ValueError

        # set values and throw away unnecessary parameters
        self = self.set_ss_para("S", s_para_values, *ports)
        self = self.strip_ss_para()
        return self

    def deembed(self, df_open, df_short, ports=None, ndevices=1, ndevices_open=1, ndevices_short=1):
        """Deembed the measured data in df from the measured data in df_open and df_short.

        This method deembeds the masured small signal parameters in df using the measured small signal parameters of one dummy open and one dummy short structure.

        Parameters
        ----------
        df_open     :  :class:`DMT.core.DataFrame`
            df containgin the measured open structure.

        df_short    :  :class:`DMT.core.DataFrame`
            df containing the measured short structure.

        ports       :  [str]
            List of port names. Should be the same for the device and the open and short.
            Defaults to ['1', '2']. For a BJT in common emitter, should be ['B', 'C', ...]

        ndevices : int
            Number of parallel devices to be deembedded.
        ndevices_open : int
            Number of parallel devices of the open structure.
        ndevices_short : int
            Number of parallel devices of the short structure.

        Returns
        -------
          :class:`DMT.core.DataFrame`
            DataFrame containing the de-embedded S parameters.

        Notes
        -----
        ..todo: make this method remember df_open and df_short.
        """
        # pr = cProfile.Profile()
        # pr.enable()
        if ports is None:
            ports = ["1", "2"]

        # short and open only onces de-embedded, this makes no sense:
        # if ndevices_open != ndevices_short:
        #     raise IOError(
        #         "DMT -> DataFrame -> deembed: The number of open and short devices must be exactly equal."
        #     )
        # if ndevices < ndevices_short:
        #     raise IOError(
        #         "DMT -> DataFrame -> deembed: The number of parallel devices is smaller then the number of shorts. Not implemented."
        #     )

        # find out how many "times" the deembedding structure needs to be deembedded
        times = ndevices / ndevices_short
        times = float(1)
        if not times.is_integer():
            raise IOError(
                "DMT -> DataFrame -> deembed: The number of devices divided by the number of parallel deembedding structures is not an integer."
            )

        try:
            # create a new object, else the df_short will deembed itself with every call of this method!
            df_short_deem = copy.deepcopy(df_short)
            self = self.deembed_open(df_open, ports, times=times)
            df_short_deem = df_short_deem.deembed_open(df_open, ports)
            self = self.deembed_short(df_short_deem, ports, times=times)
        except ValueError:
            raise ValueError
        # pr.disable()
        # pr.print_stats(sort='cumtime')
        return self

    def determine_mres(self, forced_current=False):
        """Determine the external restistances caused by the metallization.

        Parameters
        ----------
        forced_current : bool, optional


        Returns
        -------
        dict
            A dict of resistances Rb,m, Rc,m, and Re,m.

        """

        if forced_current:

            try:

                df_RC = self.loc[np.isclose(self[specifiers.CURRENT + "B"], 0.0, atol=1e-6)]
                df_RB = self.loc[np.isclose(self[specifiers.CURRENT + "C"], 0.0, atol=1e-6)]
            except KeyError:
                raise IOError

            mres = {}

            re2 = np.polyfit(df_RB["I_B"], df_RB["V_C"], 1)[0]
            re1 = np.polyfit(df_RC["I_C"], df_RC["V_B"], 1)[0]

            re = (re1 + re2) / 2
            de = np.abs(re1 - re2)

            print(
                f"rem disagreement is {de} Ohm. Using average {re} Ohm with uncertantiy {de / (200 * re)}%"
            )

            rc = np.polyfit(df_RC["I_C"], df_RC["V_C"], 1)[0] - re
            rb = np.polyfit(df_RB["I_B"], df_RB["V_B"], 1)[0] - re

            return {"R_CM": rc, "R_BM": rb, "R_EM": re}
        else:
            try:
                df_RCE_RBE = self.loc[
                    np.isclose(
                        self[specifiers.VOLTAGE + "C"], self[specifiers.VOLTAGE + "E"], atol=1e-4
                    )
                ]
                df_RBC = self.loc[
                    np.isclose(
                        self[specifiers.VOLTAGE + "B"], self[specifiers.VOLTAGE + "E"], atol=1e-4
                    )
                ]
            except KeyError:
                raise IOError

            mres = {}

            mres = DataFrame.processor.calc_RBC_RBE(mres, df_RCE_RBE)
            mres = DataFrame.processor.calc_RCE(mres, df_RBC)

            mres = DataFrame.processor.convert_mres(mres)

            return mres

    def deembed_DC(self, mres=None, df_short_dc=None, forced_current=False):
        """Deembed the measured DC data in df from external metallization resistances.

        Determine the metallization resistances and substract their impact from the measured voltages.

        Parameters
        ----------
        mres : dict
        df_short_dc : :class:`DMT.core.DataFrame`
            df containing the dc-measured short structure.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DataFrame containing the de-embedded DC-voltages.

        """

        if mres is None:
            mres = df_short_dc.determine_mres(forced_current=forced_current)

        return DataFrame.processor.deembed_mres(self, mres)

    def check_ss_cols(self, para):
        """Check the existence of the small signal parameters para cols.

        Parameters
        ----------
        para : string
            Small signal parameter whose existence shall be checked.

        Raises
        ------
        IOError
            Raised if the ss parameters para are not present in self.columns.

        """
        for col in self.columns:  # pylint: disable=not-an-iterable
            try:
                if col.specifier == para:
                    return True
            except AttributeError:
                if col[0:2] == para + "_":  # we should no allow this :(
                    return True

        return False

    def get_ss_para(self, para, port_1, *ports_n):
        """Return an array of the small signal (ss) parameters para in df.

        Parameters
        ----------
        para            :  string
            Name of the parameter to be returned
        port_1          : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        *port_n         : string
            Further nodes in order to build up a higher order matrix.

        Returns
        -------
        np.ndarray()
            Numpy array containing the values of the ss parameter para with shape [n_freq,n_port_in,n_port_out].
        """
        # check existence of the paras
        para_desired = para
        try:
            para_avail = [
                ss_para
                for ss_para in [para] + [speci for speci in specifiers_ss_para]
                if self.check_ss_cols(ss_para)
            ]
            if len(para_avail) == 0:
                raise StopIteration
            elif len(para_avail) == 1:
                para_avail = para_avail[0]
            else:
                if para_desired in para_avail:
                    para_avail = para_desired
                else:
                    para_avail = para_avail[0]
        except StopIteration:
            logging.warning("Warning: DMT->DataFrame: No SS-Parameters were found in DataFrame.")
            raise StopIteration

        list_ports = [port_1]
        columns = self.columns
        for node in ports_n:
            # check if full set of this parameter is here for this node
            col_0 = set_col_name(para_avail.upper(), port_1, node)
            col_1 = set_col_name(para_avail.upper(), node, port_1)
            col_2 = set_col_name(para_avail.upper(), node, node)

            # did not check for node[i], node[j] on purpose, because node[j] may be not part of the full set..
            if (
                col_0 in columns and col_1 in columns and col_2 in columns
            ):  # pylint: disable=unsupported-membership-test
                list_ports.append(node)

        # get the existing parameters from df and put them into a numpy array
        try:
            n_freq = len(self[specifiers.FREQUENCY])
        except KeyError:
            raise IOError("DMT -> data_frame -> get_ss_para: no column FREQ in data frame.")

        n_port = len(list_ports)

        para_values = np.zeros((n_freq, n_port, n_port), dtype=np.complex128)
        for i in range(n_port):
            for j in range(n_port):
                para_values[:, i, j] = self.loc[
                    :, SpecifierStr(para_avail.upper(), list_ports[i], list_ports[j])
                ]

        # we found some parameters, however not the desired ones. Try converting
        if para_avail != para_desired:
            para_values = self.processor.convert_n_port_para(
                para_values, p_from=str(para_avail), p_to=str(para_desired)
            )

        return para_values

    def set_ss_para(self, para, para_values, port_1, *ports_n):
        """Create or update the columns corresponding to small signal (ss) parameters para in df using the values in para_values.

        Parameters
        ----------
        para          :  string
            Name of the parameter to be set.
        para_values   :  np.array()
            Array that holds the values of the ss parameter with shape [n_freq,n_port,n_port].
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        *port_n       : string
            Further nodes in order to build up a higher order matrix.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            DataFrame that contains the columns for the ss parameter para with values according to para_values.

        """
        n_port = para_values.shape[1]
        list_nodes = [port_1] + list(ports_n)
        for i in range(n_port):
            for j in range(n_port):
                para_str = SpecifierStr(para, list_nodes[i], list_nodes[j])
                self[para_str] = para_values[:, i, j]

        return self

    def strip_ss_para(self, keep="S"):
        """Throw away all but keep small signal parameters.

        Parameters
        ----------
        keep  :  string
            Default='S'. SS Para that shall be kept.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            The initial DataFrame without all ss parameters except keep.
        """
        ss_paras = self.get_all_ss_para()
        drop = []
        for para in ss_paras:
            if para.specifier != keep:
                drop.append(para)

        return self.drop(columns=drop)

    def get_all_ss_para(self):
        """Return a list of strings of all small signal parameters (ss) in df.

        Returns
        -------
        [str]
            List of strings of the ss parameter columns in self.
        """
        ss_paras = []
        for col in self.columns:  # pylint: disable=not-an-iterable
            try:
                if col.specifier in specifiers_ss_para:
                    ss_paras.append(col)
            except AttributeError:
                pass

        return ss_paras

    def calc_ft(self, port_1, port_2):
        """Calculates the transit frequency FT using the spot frequency method.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains F_T.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self.loc[:, specifiers.TRANSIT_FREQUENCY] = self.processor.calc_ft(
            self.loc[:, specifiers.FREQUENCY], s_para_values, "S"
        )
        return self

    def calc_tfit2(self, port_1, port_2):
        """Calculates the transit frequency FT using the spot frequency method.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains F_T.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self.loc[:, specifiers.TRANSIT_TIME] = self.processor.calc_tfit2(
            self[specifiers.FREQUENCY], s_para_values, "S"
        )
        return self

    def calc_tfit(self, tfit_kind: int, ports):
        port1 = ports[0]
        port2 = ports[1]
        if tfit_kind == 1:
            return self.calc_tfit1(port1, port2)
        elif tfit_kind == 2:
            return self.calc_tfit2(port1, port2)
        elif tfit_kind == 3:
            self.ensure_specifier_column(specifiers.TRANSIT_TIME, ports=ports)
            return self

    def calc_tfit1(self, port_1, port_2):
        """Calculates the transit frequency FT using the spot frequency method.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains F_T.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self.loc[:, specifiers.TRANSIT_TIME] = self.processor.calc_tfit1(
            self[specifiers.FREQUENCY], s_para_values, "S"
        )
        return self

    def calc_fmax(self, port_1, port_2):
        """Calculates the maximum frequency of oscillation FMAX.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains F_MAX.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self[specifiers.MAXIMUM_OSCILLATION_FREQUENCY] = self.processor.calc_fmax(
            self[specifiers.FREQUENCY], s_para_values, "S"
        )
        return self

    def calc_msg(self, port_1, port_2):
        """Calculates the maximum stable gain MSG.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains MSG.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self["MSG"] = self.processor.calc_msg(self["FREQ"], s_para_values, "S")
        return self

    def calc_unilateral_gain(self, port_1, port_2):
        """Calculates the unilateral gain `GU <https://www2.eecs.berkeley.edu/Pubs/TechRpts/2016/EECS-2016-15.pdf>`_ .

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
         :class:`DMT.core.DataFrame`
            Dataframe that contains GU.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self["GU"] = self.processor.calc_unilateral_gain(self["FREQ"], s_para_values, "S")
        return self

    def calc_mag(self, port_1, port_2):
        """Calculates the maximum available gain MAG.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains MAG.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self["MAG"] = self.processor.calc_mag(self["FREQ"], s_para_values, "S")
        return self

    def calc_k(self, port_1, port_2):
        """Calculates the k-factor K.

        Parameters
        ----------
        port_1        : string
            Name of the nodes of the port 1, for a BJT in common-emitter this is 'B'.
        port_2        : string
            Name of the nodes of the port 2, for a BJT in common-emitter this is 'C'.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains K.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        self["K"] = self.processor.calc_k(self["FREQ"], s_para_values, "S")
        return self

    def calc_cbe(self, port_1="B", port_2="C"):
        """Calculates the base-emitter junction capacitance CBE assuming PI equivalent circuit and common emitter configuration.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains CBE.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        pd.options.mode.chained_assignment = (
            None  # default='warn' , Markus: This should not warn here.
        )
        if port_1 == "B" and port_2 == "C":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_shunt_port_1(self["FREQ"], s_para_values, "S")
        elif port_1 == "C" and port_2 == "B":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_shunt_port_2(self["FREQ"], s_para_values, "S")
        elif port_1 == "B" and port_2 == "E":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_series_thru(self["FREQ"], s_para_values, "S")
        elif port_1 == "E" and port_2 == "B":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_series_thru(self["FREQ"], s_para_values, "S")
        elif port_1 == "E" and port_2 == "C":  # common base
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_shunt_port_1(self["FREQ"], s_para_values, "S")
        elif port_1 == "E" and port_2 == "C":  # common base
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_shunt_port_2(self["FREQ"], s_para_values, "S")
        elif port_1 == "C" and port_2 == "E":  # common base
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "E")
            ] = self.processor.calc_cap_shunt_port_1(self["FREQ"], s_para_values, "S")
        else:
            raise NotImplementedError(
                "DMT -> DataFrame -> calc_cbe: transistor configuration not implemented."
            )

        pd.options.mode.chained_assignment = "warn"
        return self

    def calc_cce(self, port_1="B", port_2="C"):
        """Calculates the collector-emitter junction capacitance CCE, assuming PI equivalent circuit and common emitter configuration with base at port 1.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains CCE.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        pd.options.mode.chained_assignment = (
            None  # default='warn' , Markus: This should not warn here.
        )
        self[set_col_name(specifiers.CAPACITANCE, "C", "E")] = self.processor.calc_cap_shunt_port_2(
            self["FREQ"], s_para_values, "S"
        )
        pd.options.mode.chained_assignment = "warn"
        return self

    def calc_cbc(self, port_1="B", port_2="C"):
        """Calculates the base-collector junction capacitance CBC.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains CBE.
        """
        # get values
        s_para_values = self.get_ss_para("S", port_1, port_2)

        # put values in col of self
        if port_1 == "B" and port_2 == "C":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "C")
            ] = self.processor.calc_cap_series_thru(self["FREQ"], s_para_values, "S")
        elif port_1 == "C" and port_2 == "B":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "C")
            ] = self.processor.calc_cap_series_thru(self["FREQ"], s_para_values, "S")
        elif port_1 == "B" and port_2 == "E":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "C")
            ] = self.processor.calc_cap_shunt_port_1(self["FREQ"], s_para_values, "S")
        elif port_1 == "E" and port_2 == "B":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "C")
            ] = self.processor.calc_cap_shunt_port_2(self["FREQ"], s_para_values, "S")
        elif port_1 == "C" and port_2 == "E":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "C")
            ] = self.processor.calc_cap_shunt_port_1(self["FREQ"], s_para_values, "S")
        elif port_1 == "E" and port_2 == "C":
            self[
                set_col_name(specifiers.CAPACITANCE, "B", "C")
            ] = self.processor.calc_cap_shunt_port_2(self["FREQ"], s_para_values, "S")
        else:
            raise NotImplementedError(
                "DMT -> DataFrame -> calc_cbe: transistor configuration not implemented."
            )
        return self

    def calc_beta(self):
        """Calculates the DC current gain of a bipolar transistor

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains the DC current amplficiation I_C/I_B
        """
        # put values in col of self
        col_ic = set_col_name(specifiers.CURRENT, "C")
        col_ib = set_col_name(specifiers.CURRENT, "B")
        self[specifiers.DC_CURRENT_AMPLIFICATION] = self.processor.calc_beta(
            self[col_ic], self[col_ib]
        )
        return self

    def calc_gm(self):
        """Calculates the DC transconductance of a BJT.

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains the TRANSCONDUCTANCE
        """
        col_ic = specifiers.CURRENT + "C"
        col_vc_forced = specifiers.VOLTAGE + "C" + sub_specifiers.FORCED
        col_vb_forced = specifiers.VOLTAGE + "B" + sub_specifiers.FORCED
        col_vbe = specifiers.VOLTAGE + ["B", "E"]

        # get voltages
        self.ensure_specifier_column(col_vbe)
        self.ensure_specifier_column(col_ic)

        # if possible also pass vbc forced
        try:
            self.ensure_specifier_column(col_vc_forced)
            self.ensure_specifier_column(col_vb_forced)
            try:
                self.loc[:, specifiers.TRANSCONDUCTANCE] = self.processor.calc_gm(
                    self[col_ic].to_numpy(),
                    self[col_vbe].to_numpy(),
                    vc_forced=self[col_vc_forced].to_numpy(),
                    vb_forced=self[col_vb_forced].to_numpy(),
                )
            except ValueError:
                pass
        except KeyError:
            self.loc[:, specifiers.TRANSCONDUCTANCE] = self.processor.calc_gm(
                self[col_ic].to_numpy(), self[col_vbe].to_numpy()
            )

        return self

    def smooth_SS_para(self, ports, fmin):
        """Smooth the Small signal parameters in self and return a new dataframe.

        Method from:
        B. Saha et al.,
        "Reliable Technology Evaluation of SiGe HBTs and MOSFETs: fMAX Estimation From Measured Data,"
        in IEEE Electron Device Letters, vol. 42, no. 1, pp. 14-17, Jan. 2021, doi: 10.1109/LED.2020.3040891.
        to calculate fmax
        It is assumed that the frequency is strictly increasing for every DC operating point in the DataFrame,
        as is usually the case for measurement data-

        Parameters
        ----------
        ports : [str]
            The AC ports of the device
        fmin : float
            Minimum frequency to consider for smoothing

        Returns
        -------
        :class:`DMT.core.DataFrame`
            Dataframe that contains the smoothed Y Parameters
        """
        # make sure we have all Y parameters available
        for port1 in ports:
            for port2 in ports:
                for kind in [sub_specifiers.REAL, sub_specifiers.IMAG]:
                    self.ensure_specifier_column(
                        specifiers_ss_para.SS_PARA_Y + port1 + port2 + kind,
                        ports=["B", "C"],
                    )

        # assume this is real measurement data: freq is strictly increasing and we can just always get next N_FREQ values
        freq = np.unique(self[specifiers.FREQUENCY].to_numpy())
        n_freq = len(freq)
        n_rows = len(self.index)
        n_slices = int(n_rows / n_freq)

        df_new = copy.deepcopy(self)
        # remove all small signal parameters in df_new and prepare new columns
        df_new = df_new.strip_ss_para(keep="S")
        df_new = df_new.strip_ss_para(keep="Y")
        for port1 in ports:
            for port2 in ports:
                for kind in [sub_specifiers.REAL, sub_specifiers.IMAG]:
                    y_para = specifiers_ss_para.SS_PARA_Y + port1 + port2 + kind
                    df_new[y_para] = 0

        # actual smoothing
        for port1 in ports:
            for port2 in ports:
                for kind in [sub_specifiers.REAL, sub_specifiers.IMAG]:
                    y_para = specifiers_ss_para.SS_PARA_Y + port1 + port2 + kind
                    for i in range(n_slices):
                        i_low = n_freq * i
                        i_upp = n_freq * (i + 1)

                        freq_i = self.iloc[i_low:i_upp][specifiers.FREQUENCY].to_numpy()
                        indices = freq_i > fmin

                        y_raw = self.iloc[i_low:i_upp][y_para].to_numpy()

                        freq_i_lim = self.iloc[i_low:i_upp][specifiers.FREQUENCY].to_numpy()[
                            indices
                        ]
                        y_raw_lim = y_raw[indices]

                        if kind == sub_specifiers.REAL:
                            fun = fun_re
                            norm = 1
                            norm_lim = 1
                        else:
                            fun = fun_im
                            norm_lim = 2 * np.pi * freq_i_lim
                            norm = 2 * np.pi * freq_i

                        popt, _pcov = curve_fit(fun, np.log10(freq_i_lim), y_raw_lim / norm_lim)
                        y_fitted_lim = fun(np.log10(freq_i_lim), *popt)

                        df_new.iloc[i_low:i_upp, df_new.columns.get_loc(y_para)] = (
                            fun(np.log10(freq_i), *popt) * norm
                        )

        # merge real and complex part, remove afterwards
        for port1 in ["B", "C"]:
            for port2 in ["B", "C"]:
                y_para = specifiers_ss_para.SS_PARA_Y + port1 + port2
                y_para_re = specifiers_ss_para.SS_PARA_Y + port1 + port2 + sub_specifiers.REAL
                y_para_im = specifiers_ss_para.SS_PARA_Y + port1 + port2 + sub_specifiers.IMAG
                df_new[y_para] = df_new[y_para_re] + 1j * df_new[y_para_im]
                df_new.drop(columns=[y_para_im, y_para_re])

        return df_new

    def iter_unique_col(self, column, decimals=5):
        """Allows iteration over the unique values and their slices of a column

        Parameters
        ----------
        column : :class:`DMT.core.SpecifierStr` or str
            Column name to iterate over
        decimals : int, optional
            Rounding precision for the unique, None to turn off, by default 5

        Returns
        -------
        :class:`DMT.core.data_frame.IterUniqueRoundColumn`
            Iterator over all unique values of this column

        Examples
        --------
        We want to replace:

        >>> for vbc in np.unique(np.round(df[col_vbc], decimals=5)):
                data = df[np.isclose(df[col_vbc], atol=1e-5)]
                ... # user action

        with

        >>> for index, vbc, data in df.iter_unique_col(col_vbc, decimals=5):
                ... # user action

        """
        return IterUniqueRoundColumn(self, column, decimals=decimals)


class IterUniqueRoundColumn(object):
    """Iterator to iterate over rounded unique values of a column

    Parameters
    ----------
    dataframe : :class:`DMT.core.Dataframe`
        DMT (or parandas) dataframe with data including the column to iterate over.
    column : :class:`DMT.core.SpecifierStr` or str
        Column name to iterate over
    decimals : int, optional
        Rounding precision for the unique, None to turn off, by default 5

    """

    def __init__(self, dataframe, column, decimals=5):
        self.index = 0  # start at 0
        self.dataframe = dataframe
        self.column = column

        if decimals is None:
            self.val_unique = np.unique(dataframe[column])
            self.atol = None
        else:
            self.val_unique = np.unique(np.round(dataframe[column], decimals=decimals))
            self.atol = 5 * np.float_power(10, -(decimals + 1))

    def __len__(self):
        """Convenience to so len(iterator) can be used.

        Returns
        -------
        int
            Length of the uniqued values
        """
        return len(self.val_unique)

    def __iter__(self):
        """Here self is returned -> this class itself is an iterator.

        Returns
        -------
        :class:`DMT.core.data_frame.IterUniqueRoundColumn`
            Iterator over all unique values of this column
        """
        return self

    def __next__(self):
        """This routine is magic and sets the iteration behavior.

        Returns
        -------
        int
            Index of current iteration
        float
            Value of the uniqued column
        :class:`DMT.core.Dataframe`
            Slice of the dataframe with the value

        Raises
        ------
        StopIteration
            As soon as all values are iterated
        """
        if self.index == len(self):
            # end reached
            raise StopIteration

        val = self.val_unique[self.index]

        if self.atol is None:
            dataframe = self.dataframe[self.dataframe[self.column] == val]
        else:
            dataframe = self.dataframe[np.isclose(self.dataframe[self.column], val, atol=self.atol)]

        self.index += 1
        return self.index - 1, val, dataframe
