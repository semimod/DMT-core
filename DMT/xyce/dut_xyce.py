""" The interface to the Xyce circuit simulator from Sandia
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
import copy
import logging
import re
import subprocess
import warnings
import numpy as np
import pandas as pd
import time
from pathlib import Path

from DMT.config import DATA_CONFIG
from DMT.core import (
    DutCircuit,
    DutType,
    McParameterCollection,
    MCard,
    Sweep,
    SweepDef,
    specifiers,
    sub_specifiers,
    SpecifierStr,
    DataFrame,
    create_md5_hash,
    constants,
    print_progress_bar,
)
from DMT.core.circuit import (
    Circuit,
    RESISTANCE,
    INDUCTANCE,
    CAPACITANCE,
    VOLTAGE,
    CURRENT,
    SHORT,
    HICUML2_HBT,
    SGP_BJT,
)
from DMT.exceptions import SimulationUnsuccessful, SimulationFail


class DutXyce(DutCircuit):
    """Class to interface the Xyce circuit simulator"""

    def __init__(
        self,
        database_dir,
        dut_type,
        input_circuit,
        name="xyce_",
        simulator_command=None,
        simulator_arguments=None,
        simulator_options=None,
        build_xyce_plugin_command="buildxyceplugin",
        **kwargs,
    ):
        if simulator_command is None:
            simulator_command = DATA_CONFIG["commands"]["XYCE"]

        default_options = {}
        if simulator_options is not None:
            default_options.update(simulator_options)
        simulator_options = default_options

        if simulator_arguments is None:
            simulator_arguments = []

        self.build_xyce_plugin_command = build_xyce_plugin_command
        self._va_plugins_to_compile = []

        super().__init__(
            database_dir,
            name,
            dut_type,
            input_circuit,
            simulator_command=simulator_command,
            simulator_options=simulator_options,
            simulator_arguments=simulator_arguments,
            inp_name="xyce_circuit.cir",
            **kwargs,
        )

        if self.simulate_on_server:
            raise NotImplementedError(
                "Running Xyce on a Server is not implemented at the moment.",
                "It could work for non-VA Duts, but needs testing.",
                "Verilog Xyce does not work for sure.",
            )

    def create_inp_header(self, inp_circuit):
        """Creates the input header of the given circuit description and returns it.

        Parameters
        ----------
        input : DMT.core.Circuit or DMT.core.MCard
            If a MCard is given, the circuit is created from it.

        Returns
        -------
        netlist : str
        """
        va_from_model_build_in = False
        if isinstance(inp_circuit, MCard) or isinstance(inp_circuit, McParameterCollection):
            # save the modelcard, in case it was set inderectly via the input header!
            self._modelcard = copy.deepcopy(inp_circuit)
            # get the circuit for netlist generation

            ## DIRTY MARKUS FIX NETLIST VARIABLES ##############
            ## now fixed directly in the default circuit
            ####################################################

            # in case a standard circuit is used, this is the real input circuit
            self._inp_circuit = inp_circuit.get_circuit(**self.get_circuit_arguments)  # type: ignore
            if (
                "use_build_in" in self.get_circuit_arguments
                and self.get_circuit_arguments["use_build_in"]
            ):
                va_from_model_build_in = True
        elif isinstance(inp_circuit, Circuit):
            self._modelcard = None
            self._inp_circuit = copy.deepcopy(inp_circuit)
        else:
            raise OSError(
                "For Xyce circuits netlist generation is only possible from object of class DMT.classes.Circuit. Passed "
                + str(inp_circuit)
                + "."
            )

        str_netlist = (
            "DMT Xyce simulation\n"
            # "simulator1Options options "
            # + self._convert_dict_to_inp_line(self.simulator_options)
            # + "\n\n"
        )

        # is a modelcard inside the netlist?
        list_va_files = list()
        for element in self._inp_circuit.netlist:
            try:
                list_va_files.append(element.parameters.va_codes)
            except AttributeError:
                # element does not have a va_file.
                pass

        if not va_from_model_build_in:
            # load va file plugins and mark missing ones -> they are compiled later:
            va_plugins = []
            self._va_plugins_to_compile = []  # reset the plugins
            for vafile in list_va_files:
                if vafile is None:
                    continue

                if self._copy_va_files:
                    self._list_va_file_contents.append(vafile)

                # hash file content
                va_hash = vafile.get_tree_hash()
                # check if plugin is already compiled and in the folder
                path_va_hash = self.sim_dir / "xyce_plugins" / (va_hash + ".so")

                if not path_va_hash.is_file():
                    # if not: add to "to_compile"
                    self._va_plugins_to_compile.append((path_va_hash, vafile))

                va_plugins.append(path_va_hash)

            # add to simulator arguments
            if va_plugins:
                try:
                    i_plugin = self.sim_args.index("-plugin")
                    self.sim_args[i_plugin + 1] = ",".join(str(va_path) for va_path in va_plugins)
                except ValueError:
                    self.sim_args.append("-plugin")
                    self.sim_args.append(",".join(str(va_path) for va_path in va_plugins))

        str_netlist += "\n* Netlist\n"

        # add elements:
        for index, element in enumerate(self._inp_circuit.netlist):
            if isinstance(element, str):
                if not "include" in element:
                    str_netlist += ".PARAM " + element + "\n"
                else:
                    raise NotImplementedError("Need a test case for this ?!?")
                    str_netlist += element + "\n"

            else:
                str_netlist = str_netlist + self._convert_CircuitElement_netlist(element, index)

        logging.info("Successfully created input header of dut %s!", self.name)
        logging.debug("Content:\n%s", str_netlist)

        return str_netlist

    def _convert_CircuitElement_netlist(self, circuit_element, index):
        """Transforms a :class:`~DMT.classes.circuit.CircuitElement` into a string fitting for ADS.

        Parameters
        ----------
        circuit_element : :class:`DMT.core.CircuitElement`
            CircuitElement to transform
        index : int
            Counting index of the element -> to count the different models and stuff and make sure they are different

        Returns
        -------
        str
            Netlist line
        """
        converter = {
            RESISTANCE: "R",
            CAPACITANCE: "C",
            INDUCTANCE: "I",
        }

        if circuit_element.element_type == SHORT:
            return (
                "R"
                + circuit_element.name
                + " "
                + " ".join(circuit_element.contact_nodes)
                + " R=0 \n"
            )
        elif circuit_element.element_type == VOLTAGE:
            # CircuitElement( VOLTAGE, 'V_B', ['n_BX', '0'], parameters=[('Vdc','V_B'), ('Vac','1')])
            dc = next(para for para in circuit_element.parameters if para[0] == "Vdc")[1]
            try:
                float_dc = float(dc)
                parameters = "DC " + dc + " V"
            except ValueError:
                # if dc contaíns a string -> it is a parameter and hence no unit needed but braces...
                parameters = "DC {" + dc + "}"
            try:
                ac = next(para for para in circuit_element.parameters if para[0] == "Vac")[1]
                try:
                    float_ac = float(ac)
                    ac = ac + "V"
                except ValueError:
                    # if dc contaíns a string -> it is a parameter and hence no unit needed but braces...
                    ac = "{" + ac + "}"
                phase = str(np.rad2deg(0))  # just to remember this
                parameters += " AC " + ac + " " + phase
            except StopIteration:
                pass
            return (
                "V"
                + circuit_element.name
                + " "
                + " ".join(circuit_element.contact_nodes)
                + " "
                + parameters
                + " \n"
            )
        elif circuit_element.element_type == CURRENT:
            # CircuitElement( CURRENT, 'ISB', ['0', 'n_BX'], parameters=[('Idc','IB'), ('Iac','1')])

            dc = next(para for para in circuit_element.parameters if para[0] == "Idc")[1]
            parameters = "DC " + dc + "V"
            try:
                ac = next(para for para in circuit_element.parameters if para[0] == "Iac")[1]
                phase = str(np.rad2deg(0))  # just to remember this
                parameters += " AC " + ac + "V " + phase
            except StopIteration:
                pass

            return (
                "I"
                + circuit_element.name
                + " "
                + " ".join(circuit_element.contact_nodes)
                + " "
                + parameters
                + " \n"
            )
        elif circuit_element.element_type == HICUML2_HBT:
            # a model with the parameters
            # the model name
            model_name = circuit_element.parameters.default_subckt_name + "_{:d}".format(index)

            # the instance
            str_netlist = (
                "Q"
                + circuit_element.name
                + " "
                + " ".join(circuit_element.contact_nodes)
                + " "
                + model_name
                + "\n"
            )

            # and now the model with the parameters
            str_netlist += ".MODEL " + model_name + " NPN ( LEVEL=234"
            for para in circuit_element.parameters.iter_alphabetical():
                if not para.name.startswith("_"):  # do not use parameters that start with _
                    if para.val_type == int:
                        str_netlist += " {0:s} = {0:d}".format(para)
                    else:
                        str_netlist += " {0:s} = {0:10.10e}".format(para)

            return str_netlist + " )\n"
        elif circuit_element.element_type == SGP_BJT:
            # a model with the parameters
            # the model name
            model_name = circuit_element.parameters.default_subckt_name + "_{:d}".format(index)

            # the instance
            str_netlist = (
                "Q"
                + circuit_element.name
                + " "
                + " ".join(circuit_element.contact_nodes)
                + " "
                + model_name
                + "\n"
            )

            # and now the model with the parameters
            str_netlist += ".MODEL " + model_name + " NPN ( LEVEL=1"
            for para in circuit_element.parameters.iter_alphabetical():
                if not para.name.startswith("_"):  # do not use parameters that start with _
                    if para.val_type == int:
                        str_netlist += " {0:s} = {0:d}".format(para)
                    else:
                        str_netlist += " {0:s} = {0:10.10e}".format(para)

            return str_netlist + " )\n"
        else:
            try:
                # resistors, capacitors and inductors
                str_netlist = (
                    converter[circuit_element.element_type]
                    + circuit_element.name
                    + " "
                    + " ".join(circuit_element.contact_nodes)
                    + " "
                )
                for para, value in circuit_element.parameters:
                    str_netlist += para.upper() + "=" + value + " "

                return str_netlist + " \n"

            except KeyError:
                # special devices like the transistor
                model_name = circuit_element.parameters.default_subckt_name + "_{:d}".format(index)
                str_netlist = (
                    "Y"
                    + circuit_element.element_type
                    + " "
                    + circuit_element.name
                    + " "
                    + " ".join(circuit_element.contact_nodes)
                    + " "
                    + model_name
                    + "\n"
                )
                # this try-except works only if the parameters are a DMT modelcard
                str_temp = ".MODEL " + model_name + " " + circuit_element.element_type
                try:
                    for para in circuit_element.parameters.iter_alphabetical():
                        if not para.name.startswith("_"):  # do not use parameters that start with _
                            if para.val_type == int:
                                str_temp += " {0:s} = {0:d}".format(para)
                            else:
                                str_temp += " {0:s} = {0:10.10e}".format(para)
                except AttributeError:
                    for para, value in circuit_element.parameters:
                        str_temp += " " + para + "=" + value

            return str_netlist + str_temp + "\n"

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
        # first make copy of sweep, ensuring that the actual sweep object is not changed
        tmp_sweep = copy.deepcopy(sweep)
        # sweepdefs = copy.deepcopy(tmp_sweep.sweepdef)

        # compile plugins if needed and also add to arguments
        if self._va_plugins_to_compile:
            print_progress_bar(
                0, len(self._va_plugins_to_compile), prefix="Compiling Xyce plugins", length=50
            )
            processes = []
            for path_plugin, vafile in self._va_plugins_to_compile:
                # write to location
                vafile.rename_root(path_plugin.with_suffix(".va").name)
                # does it exist now ? (can happen if two different duts are used...)
                if path_plugin.is_file():
                    continue
                vafile.write_files(path_plugin.parent)

                # call "buildxyceplugin.sh"
                log_file = open(path_plugin.parent / (path_plugin.stem + "_compile.log"), "w")
                processes.append(
                    subprocess.Popen(
                        [
                            self.build_xyce_plugin_command,
                            "-o",
                            path_plugin.stem,
                            vafile.root,
                            ".",
                        ],
                        shell=False,
                        cwd=path_plugin.parent,
                        stderr=subprocess.STDOUT,
                        stdout=log_file,
                    )
                )

            time_start = time.time()
            time_out = True
            while time.time() - time_start < 60:
                finished = 0
                for i_p, process in enumerate(processes[:]):
                    returncode = process.poll()
                    if returncode is None:
                        time.sleep(0.1)
                    else:
                        if (
                            returncode == 0
                            or returncode != 0
                            # and returncode != 134
                            # and returncode != 139
                            # and returncode != 1
                        ):
                            print_progress_bar(
                                finished,
                                len(self._va_plugins_to_compile),
                                prefix="Compiling Xyce plugins",
                                length=50,
                            )
                            logpath = Path(process.args[3][:-3] + "_compile.log")
                            del processes[i_p]
                            finished += 1
                        else:
                            logpath = Path(process.args[3][:-3] + "_compile.log")
                            raise OSError(
                                "The plugin was not compiled successfull! Check the log in ",
                                str(logpath),
                                "content:",
                                logpath.with_name("buildxyceplugin.log").read_text(),
                            )

                if not processes:
                    time_out = False
                    break

            if time_out:
                raise OSError("The plugin was not compiled in time!")

            print("\n")  # new line after the progress bar

        self._va_plugins_to_compile = []

        # temperature and AC sweepdefs
        i_swd_temperature = None
        swd_ac = None
        for i_swd, swd in enumerate(tmp_sweep.sweepdef):
            if swd.var_name == specifiers.TEMPERATURE:
                if i_swd_temperature is None:
                    i_swd_temperature = i_swd
                else:
                    raise OSError("For Xyce only one temperature sweep is possible in one file!")
            elif swd.var_name == specifiers.FREQUENCY:
                if swd_ac is None:
                    swd_ac = tmp_sweep.sweepdef.pop(i_swd)
                else:
                    raise OSError("For Xyce only one AC simulation is possible in one file!")

        # get the header and add the simulation controllers
        str_netlist = self.inp_header + "\n"

        # noise ?
        if "noise" in tmp_sweep.outputdef:
            tmp_sweep.outputdef = [out_var for out_var in sweep.outputdef if out_var != "noise"]
            noise = True
            raise NotImplementedError(
                "For Xyce noise simulations are not implemented. Either implement it, pay Mario or use ADS."
            )
        else:
            noise = False

        # simulations
        # add a table with all voltages, frequencies and even temperature Oo
        outputdef = copy.deepcopy(tmp_sweep.outputdef)
        tmp_sweep.outputdef = []

        # ac forward and backward ?
        str_ac_switch = ""
        if swd_ac is not None:
            if "ac_switch" in str_netlist:
                tmp_sweep.sweepdef.append(
                    SweepDef(SpecifierStr("ac_switch"), "LIST", sweep_order=1000, value_def=[0, 1])
                )  # just use a very high sweep order to make sure it is the last one...
                str_ac_switch = " ac_switch"

        # remove columns which are not in the netlist
        tmp_sweep = tmp_sweep.set_values()
        df_def = tmp_sweep.create_df()
        for col in copy.deepcopy(df_def.columns):
            if col == specifiers.TEMPERATURE:
                df_def[col] = df_def[col] - constants.P_CELSIUS0  # convert to celsius
            elif str(col) not in str_netlist:
                df_def.drop(columns=col, inplace=True)

        str_netlist += "* Table of operation points and temperatures: \n"
        simulations = df_def.to_string(header=True, index=False)
        lines_simulations = simulations.split("\n")
        for i_line, line in enumerate(lines_simulations):
            lines_simulations[i_line] = "+ " + line
        simulations = "\n".join(lines_simulations)

        str_netlist += ".DATA TAB_SIMS\n" + simulations + "\n.ENDDATA\n\n"

        # DC operation point
        str_netlist += "* step through ops simulation\n"
        str_netlist += ".STEP DATA=TAB_SIMS\n"
        str_netlist += "* DC OP simulation\n"
        str_netlist += ".OP \n"
        # print the DC outputs
        str_netlist += "* DC OP output definition\n"
        str_netlist += (
            ".PRINT AC_IC FORMAT=CSV FILE=DC.csv TEMP V(*) I(*)" + str_ac_switch + " \n"
        )  # TODO add outputdef ?!?

        # AC simulation
        if swd_ac is not None:
            str_netlist += "* AC simulation\n"
            str_netlist += ".AC DATA=TAB_FREQUENCIES \n"
            str_netlist += ".DATA TAB_FREQUENCIES \n"
            str_netlist += "+ FREQ \n"
            str_netlist += "+ " + " ".join(f"{val:.6g}" for val in swd_ac.values) + " \n"
            str_netlist += ".ENDDATA \n"
            str_netlist += "* AC output definition\n"
            str_netlist += ".PRINT AC FORMAT=CSV FILE=AC.csv V(*) I(*) \n"  # TODO add outputdef ?!?
        else:
            raise NotImplementedError("Untested")

        # end simulation and log it
        str_netlist += "\n.END\n"

        logging.info("Added bias sweep to input header.")
        logging.debug("\n%s", str_netlist)

        return str_netlist

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

        # check log file
        sim_log = sim_folder / "sim.log"

        log_content = sim_log.read_text()

        if "MSG_ERROR" in log_content:
            raise SimulationUnsuccessful(
                "Xyce simulation in the folder " + str(sim_folder) + " failed."
            )

        if "MSG_FATAL" in log_content:
            raise SimulationUnsuccessful(
                "Xyce simulation in the folder " + str(sim_folder) + " failed."
            )

    def import_output_data(self, sweep, delete_sim_results=False, key=None):
        """Read the output files that have been produced while simulating sweep and attach them to self.db.

        Parameters
        ----------
        sweep  :  :class:`DMT.core.sweep.Sweep`
            Sweep that has been simulated for the desired output files.
        delete_sim_results : {False, True}, optional
            If True, the simulation folder is deleted after reading.

        Raises
        ------
        NotImplementedError
            If the Dut is not a simulatable dut.
        IOError
            If the given sweep can not be read.
        """
        if isinstance(sweep, Sweep):
            # get sweep folder
            sim_folder = self.get_sim_folder(sweep)

            # find .raw file
            filepaths = list(sim_folder.glob("*.csv"))
            key = self.join_key(self.get_sweep_key(sweep), "iv")
        else:
            filepaths = [
                Path(sweep),
            ]
            sim_folder = filepaths[0].parent
            if key is None:
                warnings.warn("DMT->DutXyce->import_output_data: Added a df with the key None!")

        df = self._import_xyce_results(*filepaths)

        self.data[key] = df

        if isinstance(sweep, Sweep):
            logging.info(
                "Read the Xyce simulation output data of the sweep %s. \nThe simulation folder is %s",
                sweep.name,
                sim_folder,
            )

            sim_log = sim_folder / "sim.log"
            log_content = sim_log.read_text()
            search_obj_time = re.search(
                r"Total Simulation Solvers Run Time: ([\d*?\.\d*?]) seconds",
                log_content,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if search_obj_time:
                logging.info("Simulation time: %s.", search_obj_time.group(1))

            if delete_sim_results:
                self.delete_sim_results(sweep)
        else:
            logging.info(
                "Read the Xyce simulation output data of the from the file %s.", filepaths[0]
            )

    def _import_xyce_results(self, *filepaths):
        """Reads the filepaths (must be CSVs), converts them and joins them together to one DMT.DataFrame

        Parameters
        ----------
        filenames : os.Pathlike
            Paths to the *.csv files.
        """
        col_ac_switch = SpecifierStr("AC_SWITCH")
        df_main = None

        for filepath in filepaths:
            df = pd.read_csv(filepath)
            df.__class__ = DataFrame  # cast it

            # convert column names to specifiers
            to_drop = []  # drop after iteration!
            columns = {}
            for i_col, col in enumerate(df.columns):
                if col.startswith("V("):  # is this a potential
                    node = col[4:-1]  # example: V(N_E_FORCED) -> E_FORCED
                    if "FORCED" in node:
                        col = (
                            specifiers.VOLTAGE + node[0:-7] + sub_specifiers.FORCED
                        )  # example: E_FORCED -> E
                    else:
                        col = specifiers.VOLTAGE + node
                elif col.startswith("I("):  # current
                    device = col[2:-1]
                    if device.startswith("R"):
                        col = specifiers.CURRENT + device[3:]
                    else:
                        col = specifiers.CURRENT + device
                elif col.startswith("Re("):  # real part of something
                    # Y parameters and also dV/dV (what to do with those ?!?)
                    if col[3] == "V":
                        node = col[7:-2]  # example: Re(V(N_B_FORCED)) -> B_FORCED
                        if "FORCED" in node:
                            col = (
                                specifiers.VOLTAGE
                                + node[0:-7]
                                + sub_specifiers.FORCED
                                + sub_specifiers.AC
                                + sub_specifiers.REAL
                            )  # example: E_FORCED -> E
                        else:
                            col = (
                                specifiers.VOLTAGE + node + sub_specifiers.AC + sub_specifiers.REAL
                            )
                    elif col[3] == "I":
                        device = col[5:-2]
                        if device.startswith("R"):
                            col = specifiers.SS_PARA_Y + device[3:] + sub_specifiers.REAL
                        else:
                            col = specifiers.SS_PARA_Y + device + sub_specifiers.REAL
                    else:
                        raise NotImplementedError("What is this??")
                elif col.startswith("Im("):  # imaginary part of something
                    # Y parameters and also dV/dV (what to do with those ?!?)
                    if col[3] == "V":
                        node = col[7:-2]  # example: Re(V(N_B_FORCED)) -> B_FORCED
                        if "FORCED" in node:
                            col = (
                                specifiers.VOLTAGE
                                + node[0:-7]
                                + sub_specifiers.FORCED
                                + sub_specifiers.AC
                                + sub_specifiers.IMAG
                            )  # example: E_FORCED -> E
                        else:
                            col = (
                                specifiers.VOLTAGE + node + sub_specifiers.AC + sub_specifiers.IMAG
                            )
                    elif col[3] == "I":
                        device = col[5:-2]
                        if device.startswith("R"):
                            col = specifiers.SS_PARA_Y + device[3:] + sub_specifiers.IMAG
                        else:
                            col = specifiers.SS_PARA_Y + device + sub_specifiers.IMAG
                    else:
                        raise NotImplementedError("What is this??")
                elif col == specifiers.TIME:
                    if np.any(df[col]):
                        col = specifiers.TIME
                    else:  # it is 0 for all rows in a AC_OP STEP simulation
                        to_drop.append(col)
                elif col == specifiers.FREQUENCY:
                    col = specifiers.FREQUENCY
                elif col == specifiers.TEMPERATURE:
                    col = specifiers.TEMPERATURE
                elif col == col_ac_switch:
                    col = col_ac_switch
                else:
                    raise NotImplementedError("Implement the correct specifier!")

                columns[df.columns[i_col]] = col  # pylint: disable=unsubscriptable-object

            df.drop(columns=to_drop, inplace=True)

            df = df.rename(columns=columns)

            # join the real and imaginary to values
            for i_col, col in enumerate(df.columns):
                try:
                    if sub_specifiers.REAL.sub_specifiers[0] in col.sub_specifiers:
                        col_complex = SpecifierStr(col.specifier) + col.nodes
                        for sub_spec in col.sub_specifiers:
                            if sub_spec != sub_specifiers.REAL.sub_specifiers[0]:
                                col_complex += sub_spec
                        col_imag = col_complex + sub_specifiers.IMAG
                        df[col_complex] = df[col] + 1j * df[col_imag]
                        df.drop(columns=[col, col_imag], inplace=True)
                except AttributeError:
                    # should not happen since all columns should be specifiers right now
                    raise  # but if it happens just comment the exception (if no time to fix!)

            # add the columns to df_main
            if df_main is None:
                df_main = df
            else:
                df_ac = None
                df_dc = None
                if (
                    specifiers.FREQUENCY in df.columns
                    and specifiers.FREQUENCY not in df_main.columns
                ):
                    df_dc = df_main
                    df_ac = df
                elif (
                    specifiers.FREQUENCY not in df.columns
                    and specifiers.FREQUENCY in df_main.columns
                ):
                    df_dc = df
                    df_ac = df_main
                else:
                    raise IOError("Join with main depending on content :/")

                # repeat each line in df_dc by number of frequencies
                len_frequencies = np.unique(df_ac[specifiers.FREQUENCY].to_numpy()).size
                df_main = df_dc.repeat_rows(len_frequencies)
                df_main = df_main.join(df_ac)

        if col_ac_switch in df_main.columns:

            # get all AC columns, except frequency and ac_switch
            cols_ac_old = [
                col for col in df_ac.columns if col not in [specifiers.FREQUENCY, col_ac_switch]
            ]

            #  the AC columns to account for forward and backward simulation
            if self.dut_type.is_subtype(DutType.flag_bjt):
                ports = ["B", "C"]
            elif self.dut_type.is_subtype(DutType.flag_mos):
                ports = ["G", "D"]
            else:
                raise NotImplementedError("DutType not known!")
            cols_ac_forward = []
            cols_ac_backward = []
            for col_old in cols_ac_old:
                cols_ac_forward.append(
                    SpecifierStr(col_old.specifier)
                    + [*col_old.nodes, ports[0]]
                    + col_old.sub_specifiers
                )
                cols_ac_backward.append(
                    SpecifierStr(col_old.specifier)
                    + [*col_old.nodes, ports[1]]
                    + col_old.sub_specifiers
                )
            # get the DC columns
            cols_dc = [col for col in df_dc.columns if col not in [col_ac_switch]]

            # find the row pairs with same forced dc, temp and frequency
            cols_filter = [
                col
                for col in cols_dc
                if sub_specifiers.FORCED.sub_specifiers[0] in col.sub_specifiers
            ]
            cols_filter.append(specifiers.TEMPERATURE)
            cols_filter.append(specifiers.FREQUENCY)

            row_pairs = set()
            for i_row, row in df_main.iterrows():
                sub_data = df_main
                for col_filter in cols_filter:
                    sub_data = sub_data[np.isclose(sub_data[col_filter], row[col_filter])]

                # now there should be exactly 2 rows left
                if len(sub_data) == 2:
                    row_pairs |= {(*sub_data.index.to_list(),)}
                else:
                    raise IOError("More than 2 rows for one 'AC_SWITCH' ?!?")

            # make a new dataframe
            df_main_new = DataFrame(
                columns=cols_dc + [specifiers.FREQUENCY] + cols_ac_forward + cols_ac_backward,
                dtype=np.complex64,
            )
            # join the rows, drop the old rows and save the new row in the dataframe
            for i_row_1, i_row_2 in row_pairs:
                series_dc = df_main.loc[i_row_1, cols_dc]

                if df_main.at[i_row_1, col_ac_switch]:
                    series_ac_forward = df_main.loc[i_row_2, cols_ac_old]
                    series_ac_backward = df_main.loc[i_row_1, cols_ac_old]
                elif df_main.at[i_row_2, col_ac_switch]:
                    series_ac_forward = df_main.loc[i_row_1, cols_ac_old]
                    series_ac_backward = df_main.loc[i_row_2, cols_ac_old]
                else:
                    raise IOError("Did not find forward and backward simulation")

                series_ac_forward.rename(dict(zip(cols_ac_old, cols_ac_forward)), inplace=True)
                series_ac_backward.rename(dict(zip(cols_ac_old, cols_ac_backward)), inplace=True)

                # do not forget the frequency
                series_ac_forward[specifiers.FREQUENCY] = df_main.loc[i_row_1, specifiers.FREQUENCY]

                # add the new row to the new dataframe
                df_main_new = pd.concat(
                    [
                        df_main_new,
                        pd.concat([series_dc, series_ac_forward, series_ac_backward]).to_frame().T,
                    ],
                    axis="index",
                    ignore_index=True,
                )

            df_main = df_main_new.sort_values(by=cols_filter)

        # unit converts!
        if specifiers.TEMPERATURE in df_main.columns:
            df_main[specifiers.TEMPERATURE] = (
                df_main[specifiers.TEMPERATURE] + constants.P_CELSIUS0
            )  # in DMT everything in Kelvin -.-

        return df_main
