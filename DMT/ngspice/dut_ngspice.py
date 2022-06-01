r""" Manages simulations with NGSpice.

A DuT can be supplied using the input_circuit parameter. This parameter can be:

* :class:`~DMT.classes.inp_circuit.InpCircuit`
* String with path to a netlist of a circuit
* String with the netlist of a circuit
* List with paths to netlists or strings with netlists, these will be combined using copy-paste into the netlist to simulate.

DutAds allows loads from other files. In order to keep the Hash-System the content of these loaded files are added to the DuTs hash. Loades can be:

* :py:attr:`.list_append` : Absolute path to a load file. The file will be loaded using the absolute path at the begin of the netlist.
* :py:attr:`.list_import` : Absolute or relative path files will be copied into the simulation folder and also loaded at the begin of the netlist.

This can be used for Verilog files. The correct load of ADS is determined by file ending.

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
from typing import Union
import os
import logging
import copy
import re
import numpy as np

from DMT.config import COMMANDS
from DMT.core import (
    DutCircuit,
    Circuit,
    MCard,
    constants,
    DataFrame,
    specifiers,
    sub_specifiers,
    McParameterCollection,
)
from DMT.core.circuit import SGP_BJT, VOLTAGE, CURRENT, HICUML2_HBT, SHORT, DIODE

from DMT.exceptions import SimulationUnsuccessful


class DutNgspice(DutCircuit):
    """Class description and methods

    Parameters
    ----------
    database_dir    : string
        This is the directory were the DUT will create its database.
    name      :  string
        Prefix for the database
    dut_type   : :class:`~DMT.core.dut_type.DutType`
        Type of the DUT.
    nodes     : string
        Strings with comma separated node names of DUT. If nodes is None, nodes will be requested from Dut_type class.
    input_circuit : str, list[str] or :class:`~DMT.classes.circuit.Circuit`
    copy_va_files : {False, True}
        If True, all given VA-files are copied to the simulation directory and compiled there. If False, the VA-Files have to be given as a global path.
    """

    def __init__(
        self,
        database_dir,
        dut_type,
        input_circuit,
        name="ngspice_",
        simulator_options=None,
        simulator_command=None,
        simulator_arguments=None,
        initial_conditions={},
        **kwargs,
    ):
        if simulator_command is None:
            simulator_command = COMMANDS["NGSPICE"]

        if simulator_arguments is None:
            simulator_arguments = ["-r raw.raw", "-b "]

        default_options = {
            # 'KEEPOPINFO':None
        }
        if simulator_options is not None:
            default_options.update(simulator_options)

        simulator_options = default_options

        self.initial_conditions = initial_conditions

        # set temperature to find it easily later!
        # simulator_options['Temp'] = r'{TEMP}'

        super().__init__(
            database_dir,
            name,
            dut_type,
            input_circuit,
            simulator_command=simulator_command,
            simulator_options=simulator_options,
            simulator_arguments=simulator_arguments,
            inp_name="ngspice_circuit.ckt",
            **kwargs,
        )

    def create_inp_header(self, inp_circuit: Union[MCard, McParameterCollection, Circuit]):
        """Creates the input header of the given circuit description and returns it.

        Parameters
        ----------
        input : MCard or Circuit
            If a HICUM modelcard is given, a common emitter Circuit is created from it.

        Returns
        -------
        netlist : str
        """
        if isinstance(inp_circuit, MCard) or isinstance(inp_circuit, McParameterCollection):
            # save the modelcard, in case it was set inderectly via the input header!
            self._modelcard = copy.deepcopy(inp_circuit)
            # generate inp_circuit for netlist generation
            inp_circuit = inp_circuit.get_circuit(**self.get_circuit_arguments)  # type: ignore
            # in case a standard circuit is used, this is the real input circuit
            self._inp_circuit = inp_circuit
        elif isinstance(inp_circuit, Circuit):
            self._modelcard = None
            self._inp_circuit = copy.deepcopy(inp_circuit)
        else:
            raise OSError(
                "For ADS circuits netlist generation is only possible from object of class DMT.classes.Circuit"
            )

        str_netlist = "DMT generated netlist\n"
        str_netlist += ".Options " + self._convert_dict_to_inp_line(self.simulator_options) + "\n"

        # is a modelcard inside the netlist?
        list_va_files = []
        for element in inp_circuit.netlist:
            try:
                if (
                    isinstance(inp_circuit, MCard)
                    or isinstance(inp_circuit, McParameterCollection)
                    and element.parameters.va_file is not None
                ):
                    list_va_files.append(element.parameters.va_file)
            except AttributeError:
                pass

        # load va files:
        for va_file in list_va_files:
            if self._copy_va_files:
                self._list_va_file_contents.append(va_file)
            else:
                raise NotImplementedError("Absolute path of VA-File for NGSpice...")
                if os.path.isfile(va_file):
                    # file is relative to current cwd -> transform to absolute path
                    va_file = os.path.abspath(va_file)
                # else: file must be relative to simulation cwd -> nothing to do! Possible error is raised in simulation...

        str_netlist += "\n* Netlist\n"

        # add elements:
        for element in inp_circuit.netlist:
            if isinstance(element, str):
                pass
                # str_netlist += element + '\n'
            else:
                str_netlist += self._convert_CircuitElement_netlist(element)

        logging.info("Successfully created input header of dut %s!", self.name)
        logging.debug("Content:\n%s", str_netlist)

        return str_netlist

    def make_input(self, sweep):
        """Creates the sweep definition for the given sweep

        Parameters
        ----------
        sweep : Sweep

        Returns
        -------
        str
            header with added bias definitions
        """
        # copy va files?
        # sim_folder = self.get_sim_folder(sweep)
        # for (va_file, va_file_content) in self._list_va_file_contents:
        #     with open(os.path.join(sim_folder, va_file), 'w') as my_va_file:
        #         my_va_file.write(va_file_content)

        # first make copy of sweep, ensuring that the actual sweep object is not changed
        tmp_sweep = copy.deepcopy(sweep)
        tmp_sweep = tmp_sweep.set_values()
        sweepdefs = copy.deepcopy(tmp_sweep.sweepdef)

        # find all voltage sources
        voltage_sources, current_sources = [], []
        for element in self._inp_circuit.netlist:
            try:
                if element.element_type == "V_Source":
                    voltage_sources.append(element)
                elif element.element_type == "I_Source":
                    current_sources.append(element)
            except AttributeError:
                pass

        # temperature sweepdef
        index_temp_swd = [index for index, swd in enumerate(sweepdefs) if swd.var_name == "TEMP"]
        if len(index_temp_swd) > 1:
            raise OSError("For NGSPICE only one temperature sweep is possible in one file!")
        elif len(index_temp_swd) == 1:
            index_temp_swd = index_temp_swd[0]
        else:
            index_temp_swd = None

        if index_temp_swd is None:
            # add temperature from othervar
            str_netlist = self.inp_header + "\n.temp {:10.10e}\n".format(
                sweep.othervar["TEMP"] - constants.P_CELSIUS0
            )
        elif index_temp_swd != 0:
            # sorry :(, could be possible as soon as temperature sweeps are implemented. See add_temperature_sweep
            raise NotImplementedError("For ADS a temperature sweep has to be the outermost sweep!")
        else:
            # add the correct temperature sweep and remove it from sweepdefs
            str_netlist = self.inp_header + self.add_temperature_sweep(sweepdefs[0])
            del sweepdefs[0]

        # output def
        # TODO: dirty fix to debug ngspice..
        # this is really messy...
        # device_out = [
        #     "temp",
        #     "m",
        #     "vbe",
        #     "vbc",
        #     "vce",
        #     "vsc",
        #     "vbbp",
        #     "ic",
        #     "ib",
        #     "ie",
        #     "iavl",
        #     "is",
        #     "ibei",
        #     "ibci",
        #     "it",
        #     "vbiei",
        #     "vbpbi",
        #     "vbici",
        #     "vciei",
        #     "rcx_t",
        #     "re_t",
        #     "rbi",
        #     "rb",
        #     "betadc",
        #     "gmi",
        #     "gms",
        #     "rpii",
        #     "rpix",
        #     "rmui",
        #     "rmux",
        #     "roi",
        #     "cpii",
        #     "cpix",
        #     "cmui",
        #     "cmux",
        #     "ccs",
        #     "betaac",
        #     "crbi",
        #     "tf",
        #     "ft",
        #     "ick",
        #     "p",
        #     "tk",
        #     "dtsh",
        # ]
        # str_netlist += ".save all " + " ".join(["@Q_Q_H[{:s}]".format(out) for out in device_out])

        # ngspice control statement
        str_netlist += "\n\n.control\n"

        # output settings
        str_netlist += (
            "set filetype=ascii\n"
            + "set appendwrite\n"
            + "set wr_vecnames\n"
            + "set wr_singlescale\n"
        )

        df = tmp_sweep.create_df()
        ac = True
        if not specifiers.FREQUENCY in df.columns:
            ac = False

        # from ngspice manual
        # .ac dec nd fstart fstop-
        # .ac oct no fstart fstop
        # .ac lin np fstart fstop

        # find the AC sweep definition
        if ac:
            for swd in sweepdefs:
                ac_statements = []
                if swd.var_name == specifiers.FREQUENCY:
                    swd_type = swd.sweep_type
                    swd_value_def = swd.value_def
                    nfreq = swd_value_def[-1]
                    if swd_type == "LOG":
                        ac_statements.append(
                            "ac dec {0:2.0f} {1:2.5e} {2:2.5e} \n".format(
                                nfreq, 10 ** swd_value_def[0], 10 ** swd_value_def[1]
                            )
                        )
                    elif swd_type == "CON":
                        ac_statements.append(
                            "ac dec 1 {0:2.5e} {0:2.5e} \n".format(swd_value_def[0])
                        )
                    elif swd_type == "LIN":
                        ac_statements.append(
                            "ac lin {0:2.0f} {1:2.5e} {2:2.5e} \n".format(
                                nfreq, swd_value_def[0], swd_value_def[1]
                            )
                        )
                    elif swd_type == "LIST":
                        for val in swd_value_def:
                            ac_statements.append("ac dec 1 {0:2.5e} {0:2.5e} \n".format(val))
                    else:
                        raise NotImplementedError

            # remove all but one frequency from DF. We can then laer put the "ac_statement" behind every DC point.
            freqs = df[specifiers.FREQUENCY]
            df = df[df[specifiers.FREQUENCY] == freqs[0]]
        # # #try to cast the analysis into a dc sweep ... convergence -> need to iterate over DMT sweepdef
        # if not ac:
        #     n_lin = 0
        #     n_con = 0
        #     for swd in sweepdefs:
        #         if swd.sweep_type == 'CON':
        #             n_con += 1
        #         elif swd.sweep_type == 'LIN':
        #             n_lin += 1
        #         else:
        #             continue

        #     if n_lin == 1:
        #         #only one linear sweep and no AC ... cast to ngspice sweep
        #         sweepvar = None
        #         for col in df.columns:
        #             if 'V_' in col:
        #                 vals = df[col].to_numpy()
        #                 if len(np.unique(vals)) == 1:
        #                     continue
        #                 else:
        #                     if all(np.diff(vals)==np.diff(vals)[0]):
        #                         sweepvar = col

        # so we have VOLTAGE sources and CURRENT sources and Frequency for every operating point.
        for _index, row in df.iterrows():
            for voltage_source in voltage_sources:
                voltage_name = voltage_source.name
                try:
                    voltage = row[voltage_name]
                except KeyError:
                    voltage = 0
                str_netlist += "alter V_" + str(voltage_name) + " = " + str(voltage) + "\n"

            for current_source in current_sources:
                current_name = current_source.name.replace("S", "_")
                try:
                    current = row[current_name]
                except KeyError:
                    current = 0
                str_netlist += "alter I_" + str(current_name) + " = " + str(current) + "\n"

            # DC operating point analysis
            # str_netlist += 'load\n' #try to find previous analysis results
            str_netlist += "op\n"
            # dc output statement

            # #write to output
            str_netlist += "wrdata output_ngspice_dc.ngspice all\n"

            # #if we also need ac, lets go
            if ac:
                # set all ac magnitudes to zero
                for voltage_source in voltage_sources:
                    str_netlist += "alter V_" + voltage_source.name + " ac=0\n"

                # turn on one voltage source at a time and save the results of ac analysis
                for ac_statement in ac_statements:
                    # turn on source

                    # ac analysis statement
                    # ngspice ac format: dec n_points f_start f_stop
                    # dmt sweep format : log_10(fstart) log_10(fstop) n_points
                    for voltage_source in voltage_sources:
                        str_netlist += "alter V_" + voltage_source.name + " ac=1\n"
                        str_netlist += ac_statement
                        # ac output statement -> move to end?
                        str_netlist += (
                            "wrdata output_ngspice_ac_"
                            + voltage_source.name
                            + ".ngspice alli allv\n"
                        )

                        # turn off source
                        str_netlist += "alter V_" + voltage_source.name + " ac=0\n"

                    str_netlist += "unset wr_vecnames\n"

            str_netlist += "unset wr_vecnames\n"

        str_netlist += ".endc\n" + ".end\n"

        logging.info("Added sweepdefs to input header.")
        logging.debug("\n%s", str_netlist)
        return str_netlist

    def add_temperature_sweep(self, temp_def):
        """Adds the given temperature sweep to self.inp_header and returns it!

        At the moment only constant temperature is supported!

        Parameters
        ----------
        temp_def : float or dict
            If a single float is given, a constant temperature equal to it will be used.
            For a dict, a temperature sweep is added.
        """
        if isinstance(temp_def, (float, int)):
            # single temperature
            raise NotImplementedError

        return self._inp_header

    def import_output_data(self, sweep):
        """Read the output files that have been produced while simulating sweep and attach them to self.db.

        This is done by reading and resorting the binary output file from ADS.

        Parameters
        ----------
        sweep  :  :class:`DMT.core.sweep.Sweep`
            Sweep that has been simulated for the desired output files.
        """
        # get sweep folder
        sim_folder = self.get_sim_folder(sweep)

        # find .ngspice file
        for my_file in os.listdir(sim_folder):
            filename = os.fsdecode(my_file)
            if filename.endswith(".ngspice"):
                break

        # find .ngspice file
        dfs = []
        for root, _dors, files in os.walk(sim_folder):  # . filter
            for my_file in files:
                filename = my_file
                if filename.endswith(".ngspice"):
                    dfs.append(self.read_ngspice(os.path.join(root, filename)))

        dfs = [self.clean_df(df) for df in dfs]
        dfs[0] = self.join(dfs)

        key = self.join_key(self.get_sweep_key(sweep), "iv")
        self.data[key] = dfs[0]
        logging.info(
            "Read the NGSpice simulation output data of the sweep %s. \nThe simulation folder is %s",
            sweep.name,
            sim_folder,
        )

        sim_log = os.path.join(sim_folder, "sim.log")
        with open(sim_log) as my_log:
            log_content = my_log.read()
        search_obj_time = re.search(
            r"User time(.+?)Total stopwatch time", log_content, flags=re.IGNORECASE | re.DOTALL
        )
        if search_obj_time:
            logging.info("Simulation times: %s.", search_obj_time.group(1))

    def read_ngspice(self, filename):
        """read the ngspice output file"""
        # open file
        with open(filename) as my_file:
            list_lines = my_file.readlines()

        # this seems to be printed for verilog modules... probably bracnh currents, however node is missing?
        list_lines[0] = list_lines[0].replace("#no info", "#no_info")

        # get column names
        list_lines = [line.strip() for line in list_lines]
        split_header = list_lines[0].split()
        is_ac = False
        if "frequency" in split_header:
            is_ac = True  # this ia an ac simulation

        # put all numeric values in large array and fill row by row taking n_data chunks
        # this omits the issue with line breaks produced e.g. by DEVICE
        list_lines = " ".join(list_lines[1:])
        list_lines = list_lines.split()
        list_lines = np.array([float(i) for i in list_lines])
        n_col = float(len(split_header))
        n_row = float(len(list_lines) / n_col)

        # check if n_row is an integer
        if n_row.is_integer():
            n_row = int(n_row)
        else:
            raise IOError(
                "DMT -> Data_reader: Encountered a weird number of rows in "
                + filename
                + ". Contact Markus Mueller."
            )

        # check if n_col is an integer
        if n_col.is_integer():
            n_col = int(n_col)
        else:
            raise IOError(
                "DMT -> Data_reader: Encountered a weird number of cols in "
                + filename
                + ". Contact Markus Mueller."
            )

        # need to cast real valued stuff to complex...headache
        if is_ac:
            # cast values to complex...simpler later
            n_col = int((n_col - 1) / 2 + 1)
            list_lines_cmplx = np.zeros(n_row * n_col, dtype=np.complex128)
            index_cmplx = 0  # index to list_lines_cmplx
            index_real = 0  # index to list_lines
            for n in range(n_row):
                for i in range(n_col):
                    if i == 0:
                        list_lines_cmplx[index_cmplx] = list_lines[index_real]
                        index_real += 1
                    else:
                        list_lines_cmplx[index_cmplx] = (
                            list_lines[index_real] + 1j * list_lines[index_real + 1]
                        )
                        index_real += 2

                    index_cmplx += 1

            if index_cmplx != len(list_lines_cmplx):
                raise IOError("DMT -> NGSPICE: error during ac import.")

            list_lines = list_lines_cmplx

            # now cast split_header
            new_header = []
            new_header.append(split_header[0])
            for n in range(n_col - 1):
                new_header.append(split_header[1 + n * 2])

            split_header = new_header

        # fill the data into the 2-dimensional array data_raw
        data_raw = np.empty([n_row, n_col], dtype=np.complex128)
        for i in range(n_row):
            data_raw[i, :] = list_lines[n_col * i : n_col * (i + 1)]

        # initalize pd.Dataframe() and return it
        return DataFrame(data_raw, columns=split_header)

    def clean_df(self, df):
        """From the df as read directly from ngspice, create a df that has DMT specifiers and is suitable for modeling."""
        df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate columns
        cols = df.columns
        nodes = [col[2:].upper() for col in cols if col[0:2] == "n_"]

        is_ac = False
        if "frequency" in cols:
            is_ac = True

        new_df = DataFrame()
        op_vars = []
        for col in cols:
            col_raw = col.upper()
            if "#BRANCH" in col_raw:  # current that we should save
                col_raw = col_raw.replace("#BRANCH", "")
                node = next(node for node in nodes if node in col_raw)
                new_df[specifiers.CURRENT + node] = -df[col]  # we want the other current direction
            elif col_raw[0:2] == "N_":  # found a node, will take the voltage
                node = col_raw[2:]
                if "_FORCED" in node:
                    new_df[
                        specifiers.VOLTAGE + node.replace("_FORCED", "") + sub_specifiers.FORCED
                    ] = df[col]
                else:
                    new_df[specifiers.VOLTAGE + node] = df[col]
            elif col_raw == "FREQUENCY":
                new_df[specifiers.FREQUENCY] = np.real(df["frequency"].to_numpy())

            # add opvars
            regexp = r"\[(.*)\]"
            m = re.search(regexp, col_raw)
            if m:
                op_var = m.groups()[0]
                new_df[op_var] = np.real(df[col].to_numpy())
                op_vars.append(op_var)

        # dirty: add the Y Parameters
        if is_ac:
            # step one: find which port is begin excited
            ac_voltage = None
            node_excited = None
            for node in self.nodes:
                excitement = new_df[specifiers.VOLTAGE + node].to_numpy()
                if (
                    np.mean(excitement) > 0.95
                ):  # very dirty but should work...lol better use filename
                    ac_voltage = excitement
                    node_excited = node
                    new_df.drop(axis=1, columns=specifiers.VOLTAGE + node, inplace=True)
                    break

            # delete the AC voltages, because why would anyone need them.
            for node in self.nodes:
                try:
                    new_df.drop(axis=1, columns=specifiers.VOLTAGE + node, inplace=True)

                except KeyError:
                    pass
                try:
                    new_df.drop(
                        axis=1,
                        columns=specifiers.VOLTAGE + node + sub_specifiers.FORCED,
                        inplace=True,
                    )
                except KeyError:
                    pass

            # step2: now calculate the y parameters Y(X,node)
            for node_2 in self.nodes:
                try:
                    ac_current = new_df.drop(axis=1, columns=specifiers.CURRENT + node_2).to_numpy()
                    ac_current = new_df[specifiers.CURRENT + node_2].to_numpy()
                    new_df.drop(axis=1, columns=specifiers.CURRENT + node_2, inplace=True)
                except KeyError:
                    continue

                try:
                    y_para = specifiers.SS_PARA_Y + node_2 + node_excited
                    new_df[y_para] = ac_current / ac_voltage
                except TypeError:
                    raise IOError("What went wrong here? We do not know.")

        fallback_dict = {}
        for op_var in op_vars:
            fallback_dict[op_var] = op_var
        return new_df.clean_data(
            nodes,
            self.reference_node,
            ac_ports=self.ac_ports,
            fallback=fallback_dict,
            warnings=False,
        )

    def validate_simulation_successful(self, sweep):
        """Checks if the simulation of the given sweep was successful.

        Parameters
        ----------
        sweep  :  :class:`DMT.core.sweep.Sweep`
            Sweep that has been simulated.

        Raises
        ------
        NotImplementedError
            If the Dut is not a simulatable dut.
        SimulationUnsuccessful
            If the simulation output is not valid.
        FileNotFoundError
            If the sim log file does not exist.
        """
        # get sweep folder
        sim_folder = self.get_sim_folder(sweep)

        # find log file
        sim_log = os.path.join(sim_folder, "sim.log")

        with open(sim_log) as my_log:
            log_content = my_log.read()

        if "error" in log_content:
            print("DMT - NGSPICE: Simulation failed! An error was found in the simulation log!")
            logging.debug("Log content:\n%s", log_content)
            raise SimulationUnsuccessful(
                "NGSPICE Simulation of the sweep "
                + sweep.name
                + " with the hash "
                + sweep.get_hash()
                + " failed! An error was found!"
            )

        # need to find something similar for ngspice
        # if not seach_obj_end:
        #     print("DMT - DutAds: Simulation failed! The simulation log file is not complete!")
        #     logging.debug("Log content:\n%s", log_content)
        #     raise SimulationUnsuccessful('ADS Simulation of the sweep ' + sweep.name + ' with the hash ' + sweep.get_hash() + ' failed! The simulation log file is not complete!')

        # find .ngspice file
        for my_file in os.listdir(sim_folder):
            filename = os.fsdecode(my_file)
            if filename.endswith(".ngspice"):
                break

        if not filename.endswith(".ngspice"):
            print(
                "DMT - DutNgspice: Simulation failed! The simulation result .raw file was not found!"
            )
            logging.debug("Log content:\n%s", log_content)
            raise SimulationUnsuccessful(
                "NGSPICE Simulation of the sweep "
                + sweep.name
                + " with the hash "
                + sweep.get_hash()
                + " failed! The simulation result raw file was not found!"
            )

    def _convert_dict_to_inp_line(self, dict_key_para):
        """Converts dictionary into a line for a ADS input file.

        Transforms a dictionary with

        | dict[key1] = value1
        | dict[key2] = value2

        into a line with "key1=value1 key2=value2 ". Correctly converts strings, iteratables, bools and numbers.

        Parameters
        ----------
        dict_key_para : dict

        Returns
        -------
        str
            Line to add into input file
        """
        str_return = ""

        for (key, param) in dict_key_para.items():
            if isinstance(param, str):
                str_add = key + "=" + param + " "
            elif isinstance(param, (list, tuple)):
                str_add = key + "=" + " ".join([str(nr) for nr in param]) + " "
            elif isinstance(param, bool):
                str_add = "yes" if param else "no"
                str_add = key + "=" + str_add
            elif param is None:
                str_add = key + " "
            else:
                str_add = key + "=" + str(param) + " "

            str_return = str_return + str_add

        return str_return

    def _convert_CircuitElement_netlist(self, circuit_element):
        """Transforms a :class:`~DMT.classes.circuit.CircuitElement` into a string fitting for NGspice.

        Parameters
        ----------
        circuit_element
            CircuitElement to transform

        Returns
        -------
        str
            Netlist line
        """
        # if len(circuit_element.name) != 3:
        #     raise OSError(
        #         "To enable data_reader.read_ADS_bin, all element names have to be 3 characters long. Given was: "
        #         + circuit_element.name
        #     )

        # map dmt circuit element_type to ngspice element types
        # only those that differ between DMT definiton and NGspice definition are listed here
        element_types = {
            VOLTAGE: "V",
            CURRENT: "I",
            "hicumL2va": "Q",
            HICUML2_HBT: "Q",
            SGP_BJT: "Q",
            "bjtn": "Q",
        }
        if circuit_element.element_type in element_types.keys():
            element_type = element_types[circuit_element.element_type]
        elif circuit_element.element_type == SHORT:
            element_type = "V"
            circuit_element.name = "V_" + circuit_element.name.replace("I", "V")
            circuit_element.parameters = [("dc", str(0)), ("ac", str(0))]
            circuit_element.contact_nodes = (
                circuit_element.contact_nodes[1],
                circuit_element.contact_nodes[0],
            )
        else:
            element_type = circuit_element.element_type

        str_netlist = f"{element_type}_{circuit_element.name} " + " ".join(
            circuit_element.contact_nodes
        )
        if circuit_element.parameters is not None:
            if isinstance(circuit_element.parameters, MCard):
                str_temp = "+ "

                if circuit_element.element_type in ["hicumL2va", HICUML2_HBT]:
                    mcard = circuit_element.parameters
                    str_instance_parameters = ""
                    str_model_parameters = ""
                    str_type = "NPN"
                    for para in sorted(mcard.paras, key=lambda x: (x.group, x.name)):
                        if para.name == "type":
                            str_type = "NPN" if (para.value == 1) else "PNP"
                        elif para.name in [
                            "dt",
                        ]:  # here all instance parameters
                            str_instance_parameters += "{0:s}={0:10.10e} ".format(para)
                        else:  # here all model parameters
                            str_model_parameters += "{0:s}={0:10.10e} ".format(para)

                    for (key, val) in self.initial_conditions.items():
                        # dirty to allow debugging ngspice
                        str_model_parameters += "{0:s}={1:10.10e} ".format(key, val)
                    str_temp = (
                        f"hicum_va {str_instance_parameters}\n"  # we should count here somehow the models
                        + f".model hicum_va {str_type} level=8\n"
                        + f"+ {str_model_parameters}"
                    )
                elif circuit_element.element_type in [SGP_BJT, "bjtn"]:
                    mcard = circuit_element.parameters
                    str_instance_parameters = ""
                    str_model_parameters = ""
                    str_type = "NPN"
                    for para in sorted(mcard.paras, key=lambda x: (x.group, x.name)):
                        if para.name == "type":
                            str_type = "NPN" if (para.value == 1) else "PNP"
                        elif para.name in []:  # here all instance parameters
                            str_instance_parameters += "{0:s}={0:10.10e} ".format(para)
                        else:  # here all model parameters
                            str_model_parameters += "{0:s}={0:10.10e} ".format(para)

                    for (key, val) in self.initial_conditions.items():
                        # dirty to allow debugging ngspice
                        str_model_parameters += "{0:s}={1:10.10e} ".format(key, val)
                    str_temp = (
                        f"QMOD {str_instance_parameters}\n"  # we should count here somehow the models
                        + f".model QMOD {str_type} level=1\n"
                        + f"+ {str_model_parameters}"
                    )
                elif circuit_element.element_type in [DIODE]:
                    mcard = circuit_element.parameters
                    str_instance_parameters = ""
                    str_model_parameters = ""
                    str_type = "NPN"
                    additional_str = ""
                    for para in sorted(mcard.paras, key=lambda x: (x.group, x.name)):
                        if para.name == "osdi":
                            if para - value == 1:
                                additional_str = " osdi " + circuit_element.name
                        str_model_parameters += "{0:s}={0:10.10e} ".format(para)

                    str_temp = f"\n.model dmod {additional_str} d( {str_model_parameters} )"  # we should count here somehow the models
                else:
                    raise NotImplementedError(
                        f"The element type {circuit_element.element_type} is not implemented for ngspice.",
                        "Check the ngspice manual if this type needs special treatment and implement it accordingly.",
                    )
            else:
                str_temp = []
                for (para, value) in circuit_element.parameters:
                    if para in ["C", "R", "L"]:  # rename according to ngspice manual
                        str_temp.append(value)
                    elif para in ["Vdc", "Vac"] and not isinstance(
                        value, float
                    ):  # just leave voltages from lines, as ngpsice directly changes the sources and not the parameters
                        pass
                    else:
                        str_temp.append(para + "=" + value)

                str_temp = " ".join(str_temp)

                # find sim paras
                sim_paras = ""
                for (para, value) in circuit_element.parameters:
                    try:
                        float(value)
                    except ValueError:
                        sim_paras = sim_paras + value + "=0 "

                if sim_paras != "":
                    sim_paras = "\n.param " + sim_paras

                str_temp = str_temp + "".join(sim_paras)

            # catch ngspice keywords
            str_temp = str_temp.replace(" L=", "")
            str_temp = str_temp.replace("Vdc=", "dc ")
            str_temp = str_temp.replace("Idc=", "dc ")
            str_temp = str_temp.replace("Vac=", "ac ")
            str_temp = str_temp.replace("Iac=", "ac ")
        else:
            str_temp = ""

        str_netlist = str_netlist.replace("IS", "I_")
        return str_netlist + " " + str_temp + "\n"

    def join(self, dfs):
        """Join DC and AC dataframes into one dataframe"""
        dfs_ac = [df for df in dfs if "FREQ" in df.columns]
        df_dc = next(df for df in dfs if not "FREQ" in df.columns)
        if not dfs_ac:
            return df_dc

        # first find all frequencies and see if they match
        freqs = [df[specifiers.FREQUENCY].to_numpy() for df in dfs_ac]
        for freq in freqs:
            if (freq == freqs[0]).all():
                continue
            else:
                raise IOError("DMT -> NGspice: frequencies of AC simulation data do not match.")

        # join the ac dataframes into one ac dataframe dfs_ac[0]
        for df in dfs_ac[1:]:
            for col in df.columns:
                if not col in dfs_ac[0].columns:
                    vals = df[col].to_numpy()
                    dfs_ac[0][col] = vals

        # join the dc data to the ac data
        n_freq = len(np.unique(freqs[0]))
        for col in df_dc.columns:
            # if not col in dfs_ac[0].columns:
            vals = df_dc[col].to_numpy()
            vals = np.repeat(vals, n_freq)
            dfs_ac[0][col] = vals

        return dfs_ac[0]
