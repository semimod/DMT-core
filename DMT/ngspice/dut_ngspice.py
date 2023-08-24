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
from typing import Union
import os
import logging
import copy
import re
import numpy as np
import pandas as pd
import subprocess
from pathlib import Path
from typing import List, Dict, Type

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

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
    SweepDef,
    Technology,
)
from DMT.core.circuit import (
    SGP_BJT,
    VOLTAGE,
    CURRENT,
    HICUML2_HBT,
    SHORT,
    DIODE,
    SUBCIRCUIT,
)

from DMT.exceptions import SimulationUnsuccessful

SEMVER_DUTNGSPICE_CURRENT = VersionInfo(major=1, minor=0)


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
    va_maps : [DMT.core.VAFileMap]
        Verilog-A file mapping that contains any additional Verilog-A files needed for this DutCircuit.
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
        command_openvaf=COMMANDS["OPENVAF"],
        copy_va_files=False,
        inp_name="ngspice_circuit.ckt",
        va_maps=[],
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
        self.devices_op_vars = []
        self._osdi_imports = []
        self.command_openvaf = command_openvaf
        self.va_maps = va_maps

        super().__init__(
            database_dir,
            name,
            dut_type,
            input_circuit,
            simulator_command=simulator_command,
            simulator_options=simulator_options,
            simulator_arguments=simulator_arguments,
            inp_name=inp_name,
            copy_va_files=copy_va_files,
            **kwargs,
        )

    def info_json(self, **_kwargs) -> Dict:
        """Returns a dict with serializeable content for the json file to create.

        The topmost dict MUST have only one key: The string casted class name.
        Inside the parameters are:

            * A version key,
            * all extra parameters of DutNgspice compared to DutCircuit and
            * the info_json of DutCircuit.

        Returns
        -------
        dict
            str(DutNgspice): serialized content
        """

        return {
            str(DutNgspice): {
                "__DutNgspice__": str(SEMVER_DUTNGSPICE_CURRENT),
                "parent": super(DutNgspice, self).info_json(**_kwargs),
                "initial_conditions": self.initial_conditions,
                "devices_op_vars": self.devices_op_vars,
                "_osdi_imports": [str(osdi) for osdi in self._osdi_imports],
                "command_openvaf": self.command_openvaf,
            }
        }

    @classmethod
    def from_json(
        cls,
        json_content: Dict,
        classes_technology: List[Type[Technology]],
        subclass_kwargs: Dict = None,
    ) -> "DutNgspice":
        """Static class method. Loads a DutNgspice object from a json or pickle file with full path save_dir.

        Calls the from_json method of DutView with all dictionary inside the "parent" keyword. Afterwards the additional parameters are set correctly.

        Parameters
        ----------
        json_content  :  dict
            Readed dictionary from a saved json DutNgspice.
        classes_technology : List[Type[Technology]]
            All possible technologies this loaded DutNgspice can have. One will be choosen according to the serialized technology loaded from the file.
        subclass_kwargs : Dict, optional
            Additional kwargs necessary to create the concrete subclassed DutView.

        Returns
        -------
        DutNgspice
            Loaded object.
        """
        if json_content["__DutNgspice__"] != SEMVER_DUTNGSPICE_CURRENT:
            raise NotImplementedError(
                "DMT.DutNgspice: Unknown version of DutNgspice to load!"
            )

        dut_view = super().from_json(
            json_content["parent"], classes_technology, subclass_kwargs=subclass_kwargs
        )
        dut_view.initial_conditions = json_content["initial_conditions"]
        dut_view.devices_op_vars = json_content["devices_op_vars"]
        dut_view._osdi_imports = [Path(osdi) for osdi in json_content["_osdi_imports"]]
        dut_view.command_openvaf = json_content["command_openvaf"]

        return dut_view

    def create_inp_header(
        self, inp_circuit: Union[MCard, McParameterCollection, Circuit]
    ):
        """Creates the input header of the given circuit description and returns it.

        Parameters
        ----------
        input : MCard or Circuit
            If a HICUM modelcard is given, a common emitter Circuit is created from it.

        Returns
        -------
        netlist : str
        """
        use_osdi = bool(self.command_openvaf)  # False if None/null

        if isinstance(inp_circuit, MCard) or isinstance(
            inp_circuit, McParameterCollection
        ):
            # save the modelcard, in case it was set inderectly via the input header!
            self._modelcard = copy.deepcopy(inp_circuit)
            # generate inp_circuit for netlist generation
            self._inp_circuit = inp_circuit.get_circuit(**self.get_circuit_arguments)  # type: ignore
            if (
                "use_build_in" in self.get_circuit_arguments
                and self.get_circuit_arguments["use_build_in"]
            ):
                use_osdi = False
            # in case a standard circuit is used, this is the real input circuit
        elif isinstance(inp_circuit, Circuit):
            self._modelcard = None
            self._inp_circuit = copy.deepcopy(inp_circuit)

            self.list_copy += inp_circuit.lib_files
        else:
            raise OSError(
                "For ngspice circuits netlist generation is only possible from object of class DMT.core.MCard or DMT.core.Circuit"
            )

        self.devices_op_vars = []
        str_netlist = "DMT generated netlist\n"
        str_netlist += (
            ".Options " + self._convert_dict_to_inp_line(self.simulator_options) + "\n"
        )

        if use_osdi:
            # is a modelcard inside the netlist?
            list_va_files = list()
            for element in self._inp_circuit.netlist:
                try:
                    list_va_files.append(element.parameters.va_codes)
                except AttributeError:
                    # element does not have a va_file.
                    pass

            list_va_files += self._inp_circuit.verilog_maps

            # pre_osdi strings
            self._osdi_imports = []
            for vafile in list_va_files:
                if vafile is None:
                    continue

                self._list_va_file_contents.append(vafile)

                if self._copy_va_files:
                    # always add the relative path to va -> compile and use relative import in netlist
                    self._osdi_imports.append(vafile.root)
                else:
                    # check if compiled file is already there and if yes, directly add ".osdi", else add ".va"

                    va_hash = vafile.get_tree_hash()  # hash file content
                    # check if plugin is already compiled and in the folder
                    path_va = self.sim_dir / "VA_codes" / va_hash / vafile.root
                    path_osdi = path_va.with_suffix(".osdi")

                    if path_osdi.is_file():
                        self._osdi_imports.append(path_osdi)
                    else:
                        # if not: add to "to_compile"
                        self._osdi_imports.append(path_va)

        self._osdi_imports = list(set(self._osdi_imports))  # unique...
        str_netlist += "\n* Netlist\n"

        # add elements:
        for index, element in enumerate(self._inp_circuit.netlist):
            if isinstance(element, str):
                # pass
                if re.match(r"^[\w_]+=", element):
                    # filters Variables -> ngspice does not need those
                    continue

                str_netlist += element + "\n"
            else:
                str_netlist += self._convert_CircuitElement_netlist(element, index)

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
        index_temp_swd = [
            index for index, swd in enumerate(sweepdefs) if swd.var_name == "TEMP"
        ]
        if len(index_temp_swd) > 1:
            raise OSError(
                "For NGSPICE only one temperature sweep is possible in one file!"
            )
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
            raise NotImplementedError(
                "For ADS a temperature sweep has to be the outermost sweep!"
            )
        else:
            # add the correct temperature sweep and remove it from sweepdefs
            str_netlist = self.inp_header + self.add_temperature_sweep(sweepdefs[0])
            del sweepdefs[0]

        # ngspice control statement
        str_netlist += "\n\n.control\n"

        # add pre_osdi
        if self._osdi_imports:
            print("\nPreparing OSDI Sources if needed.\n")

        for osdi in self._osdi_imports:
            try:
                if osdi.suffix != ".osdi":
                    # compile needed ? Could be compiled by a "parallel" simulation
                    if not osdi.with_suffix(".osdi").is_file():
                        process = subprocess.run(
                            [self.command_openvaf, osdi.name],
                            shell=False,
                            cwd=osdi.parent,
                        )
                        if process.returncode != 0:
                            raise OSError(
                                "DMT.DutNgspice: Run of OpenVAF failed!",
                                f"The file to compile was {osdi}",
                            )
                    osdi = osdi.with_suffix(".osdi")

                # import from common "VA_codes" folder
                str_netlist += f"pre_osdi {osdi}\n"
            except AttributeError:
                # import from relative location
                # compile always needed
                process = subprocess.run(
                    [self.command_openvaf, osdi],
                    shell=False,
                    cwd=self.get_sim_folder(sweep),
                )
                if process.returncode != 0:
                    raise OSError(
                        "DMT.DutNgspice: Run of OpenVAF failed!",
                        f"The file to compile was {osdi} in {self.get_sim_folder(sweep)}",
                    )

                osdi = Path(osdi).with_suffix(".osdi")

                # relative import
                str_netlist += f"pre_osdi {osdi.name}\n"

        # output def
        str_netlist += "\nsave alli allv "
        str_dc_output = ""
        if tmp_sweep.outputdef:
            if "OpVar" in tmp_sweep.outputdef:
                str_dc_output += " ".join(self.devices_op_vars) + " "
                tmp_sweep.outputdef.remove("OpVar")

            # TODO find better way to use outputdef for ngspice
            # current way does not work...
            # str_dc_output += " ".join(tmp_sweep.outputdef)
        str_netlist += str_dc_output

        # output settings
        str_netlist += (
            "\n\nset filetype=ascii\n"
            + "set appendwrite\n"
            + "set wr_vecnames\n"
            + "set wr_singlescale\n"
        )

        df = tmp_sweep.create_df()

        # for AC use a table and only linear sweeps since:
        # from ngspice manual ONLY lin can have only 1 freqency

        # find the AC sweep definition
        ac_statements = []
        for swd in sweepdefs:
            if swd.var_name == specifiers.FREQUENCY:
                if swd.sweep_type == "LIN":  # TODO: more nice
                    ac_statements.append(
                        f"ac lin {swd.value_def[2]:g} {swd.value_def[0]:g} {swd.value_def[1]:g}\n"
                    )
                else:
                    for freq in swd.values:
                        ac_statements.append(f"ac lin 1 {freq:g} {freq:g}\n")

        if ac_statements:
            # remove all but one frequency from DF. We later put the "ac_statement" behind every DC point.
            freqs = df[specifiers.FREQUENCY]
            df = df[df[specifiers.FREQUENCY] == freqs[0]]
        else:
            df[specifiers.FREQUENCY] = 1e9  # default frequency...
            ac_statements.append("ac lin 1 1e9 1e9 \n")

        try:
            # currently only 1 transient sweepdef per ngspice simulation (?)
            swd_tran = next(swd for swd in sweepdefs if swd.var_name == specifiers.TIME)
            if (
                len(list(swd for swd in sweepdefs if swd.var_name == specifiers.TIME))
                > 1
            ):
                raise IOError(
                    "Currently only one transient sweepdef per sweep in DutNgspice"
                )
            if len(swd_tran.value_def) > 1:
                raise IOError(
                    "Currently only one transient simulation per sweep in DutNgspice"
                )

            # remove all but one time point from DF. We later let ngspice make the transient at every DC point.
            time = df[specifiers.TIME]
            df = df[df[specifiers.TIME] == time[0]]
            df = df.drop(specifiers.TIME, axis=1)

            # add transient signal to the correct voltage source
            source_old = "V_V_{0} n_{0}X 0".format(swd_tran.contact)
            if source_old not in str_netlist:
                raise IOError(
                    "DMT->DutNgspice: Did not find voltage source for transient signal input."
                )

            # if swd_tran.

            sources_new = (
                "V_V_{0} n_{0}_DC 0\n".format(swd_tran.contact)
                + "V_V_{0}_tr n_{0}X n_{0}_DC ".format(swd_tran.contact)
                + self._convert_swd_trans_to_pwl(swd_tran)
                + " r=-1"
            )
            str_netlist = str_netlist.replace(source_old, sources_new)
        except StopIteration:
            swd_tran = False

        # create vectors for each voltage
        one_ele_array = False
        for voltage_source in voltage_sources:
            try:
                vals = df[voltage_source.name].to_numpy()
            except (
                KeyError
            ):  # assume that a voltage not specified in the sweep is grounded
                vals = np.zeros_like(0, shape=len(df))
            if (
                len(vals) == 1
            ):  # Ngspice does not support 1 element arrays ... so we just extend it.
                vals = np.append(vals, vals)
                one_ele_array = True
            str_vec = (
                "compose V_"
                + voltage_source.name
                + "_vec values "
                + "".join(["(" + str(val) + ") " for val in vals])
            )
            str_netlist += str_vec + "\n"

            # compose ve_vec values 0 0 0 0 0 0 0 0 0 0 0

        # TODO create vectors for each current source

        n_bias = len(vals)
        if one_ele_array:  # special case: just one OP to simulate
            n_bias = n_bias - 1
        str_netlist += "let index=0\n"
        str_netlist += "while index<" + str(int(n_bias)) + "\n"

        # so we have VOLTAGE sources and CURRENT sources and Frequency for every operating point.
        str_netlist += "    *set value of all voltage sources:\n"
        for voltage_source in voltage_sources:
            voltage_name = voltage_source.name
            str_netlist += (
                "    alter V_"
                + str(voltage_name)
                + " = V_"
                + str(voltage_name)
                + "_vec[index]\n"
            )
            # alter V_V_E = ve_vec[index]

        # for current_source in current_sources:
        #     current_name = current_source.name.replace("S", "_")
        #     try:
        #         current = row[current_name]
        #     except KeyError:
        #         current = 0
        #     str_netlist += "alter I_" + str(current_name) + " = " + str(current) + "\n"

        str_netlist += "    let index=index+1\n"

        # DC operating point analysis
        # str_netlist += 'load\n' #try to find previous analysis results
        str_netlist += "    *perform DC analysis and write output:\n"
        str_netlist += "    op\n"
        # dc output statement

        # #write to output
        str_netlist += (
            f"    wrdata output_ngspice_dc.ngspice alli allv {str_dc_output}\n"
        )

        # Add AC
        # set all ac magnitudes to zero
        str_netlist += "    *set AC mag of all sources equal zero\n"
        for voltage_source in voltage_sources:
            str_netlist += "    alter V_" + voltage_source.name + " ac=0\n"

        # turn on one voltage source at a time and save the results of ac analysis
        str_netlist += "    *turn on one AC source at a time and perform analysis\n"
        for i_ac_statement, ac_statement in enumerate(ac_statements):
            # turn on source

            # ac analysis statement
            # ngspice ac format: dec n_points f_start f_stop
            # dmt sweep format : log_10(fstart) log_10(fstop) n_points
            for voltage_source in voltage_sources:
                str_netlist += "    alter V_" + voltage_source.name + " ac=1\n"
                str_netlist += "    " + ac_statement
                # ac output statement -> move to end?
                str_netlist += (
                    "    wrdata output_ngspice_ac_"
                    + voltage_source.name
                    + ".ngspice alli allv\n"
                )

                # turn off source
                str_netlist += "    alter V_" + voltage_source.name + " ac=0\n"

            if i_ac_statement == 0:
                str_netlist += "    unset wr_vecnames\n"

        # Add transients
        if swd_tran:
            for i_tr, freq in enumerate(swd_tran.value_def):
                tau = 1 / freq

                str_netlist += (
                    "set wr_vecnames\n"
                    + f"tran {tau/40} {3*tau}\n"
                    + f"wrdata output_ngspice_tr_{i_row}_{i_tr}.ngspice_tr alli allv\n"
                    + "unset wr_vecnames\n"
                )

        str_netlist += "    unset wr_vecnames\n"
        str_netlist += "end\n"
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

        # find .ngspice files (these are DC and AC)
        files_dc_ac = [sim_file for sim_file in sim_folder.glob("*.ngspice")]
        # are there transient simulations?
        files_tran = sorted(sim_file for sim_file in sim_folder.glob("*.ngspice_tr"))

        key = self.join_key(self.get_sweep_key(sweep), "iv")
        dfs_dc_ac = [
            _read_clean_ngspice_df(
                sim_file,
                self.nodes,
                self.reference_node,
                self.ac_ports,
            )
            for sim_file in files_dc_ac
        ]
        self.data[key] = self.join(dfs_dc_ac)

        keys_tr = [
            self.join_key(self.get_sweep_key(sweep), sim_tr_file.stem[15:])
            for sim_tr_file in files_tran
        ]
        dfs_tr = [
            _read_clean_ngspice_df_transient(
                sim_tr_file, self.reference_node, self.ac_ports
            )
            for sim_tr_file in files_tran
        ]

        for key, df in zip(keys_tr, dfs_tr):
            self.data[key] = df

        logging.info(
            "Read the NGSpice simulation output data of the sweep %s. \nThe simulation folder is %s",
            sweep.name,
            sim_folder,
        )

        sim_log = os.path.join(sim_folder, "sim.log")
        with open(sim_log) as my_log:
            log_content = my_log.read()
        search_obj_time = re.search(
            r"User time(.+?)Total stopwatch time",
            log_content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if search_obj_time:
            logging.info("Simulation times: %s.", search_obj_time.group(1))

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
            print(
                "DMT - NGSPICE: Simulation failed! An error was found in the simulation log!"
            )
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

        for key, param in dict_key_para.items():
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

    def _convert_CircuitElement_netlist(self, circuit_element, index):
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
            HICUML2_HBT: "Q",
            SGP_BJT: "Q",
            "bjtn": "Q",
            SUBCIRCUIT: "X",
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
        elif (
            isinstance(circuit_element.parameters, MCard)
            and circuit_element.parameters.va_codes is not None
        ):
            element_type = "N"
        else:
            element_type = circuit_element.element_type

        str_netlist = f"{element_type}_{circuit_element.name} " + " ".join(
            circuit_element.contact_nodes
        )
        if circuit_element.parameters is not None:
            if isinstance(circuit_element.parameters, MCard):
                str_temp = "+ "
                mcard = circuit_element.parameters

                if circuit_element.element_type == HICUML2_HBT:
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

                    for key, val in self.initial_conditions.items():
                        # dirty to allow debugging ngspice
                        str_model_parameters += "{0:s}={1:10.10e} ".format(key, val)
                    str_temp = (
                        f"hicum_build_in{index:d} {str_instance_parameters}\n"  # we should count here somehow the models
                        + f".model hicum_build_in{index:d} {str_type} level=8 {str_model_parameters}"
                    )
                elif circuit_element.element_type in [SGP_BJT, "bjtn"]:
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

                    for key, val in self.initial_conditions.items():
                        # dirty to allow debugging ngspice
                        str_model_parameters += "{0:s}={1:10.10e} ".format(key, val)
                    str_temp = (
                        f"QMOD{index:d} {str_instance_parameters}\n"  # we should count here somehow the models
                        + f".model QMOD{index:d} {str_type} level=1 {str_model_parameters}"
                    )
                elif "sky130_fd_pr" in circuit_element.element_type:
                    # skywater 130 device
                    str_instance_parameters = ""

                    for para in sorted(mcard.paras, key=lambda x: (x.group, x.name)):
                        str_instance_parameters += "{0:s}={0:10.10e} ".format(para)

                    str_netlist = (
                        f'.lib "{mcard.pdk_path}" {mcard.pdk_corner}\n'
                        + f"{circuit_element.name} "
                        + " ".join(circuit_element.contact_nodes)
                    )
                    str_temp = (
                        f"{circuit_element.element_type} {str_instance_parameters}"
                    )
                elif circuit_element.parameters.va_codes is not None:
                    str_instance_parameters = ""
                    str_model_parameters = ""
                    for para in sorted(mcard.paras, key=lambda x: (x.group, x.name)):
                        if (
                            para.name in []
                        ):  # here all instance parameters TODO after next verilogae release
                            str_instance_parameters += "{0:s}={0:10.10e} ".format(para)
                        else:  # here all model parameters
                            str_model_parameters += "{0:s}={0:10.10e} ".format(para)

                    str_temp = (
                        f"model_va{index:d} {str_instance_parameters}\n"  # we should count here somehow the models
                        + f".model model_va{index:d} {circuit_element.parameters.default_module_name} {str_model_parameters}"
                    )
                else:
                    raise NotImplementedError(
                        f"The element type {circuit_element.element_type} is not implemented for ngspice.",
                        "Check the ngspice manual if this type needs special treatment and implement it accordingly.",
                    )

                self.devices_op_vars += [
                    f"@{element_type}_{circuit_element.name}[{op_var:s}]"
                    for op_var in mcard.op_vars
                ]

            else:
                str_temp = []
                for para in circuit_element.parameters:
                    if isinstance(para, str):
                        str_temp.append(para)
                    elif para[0] in ["C", "R", "L"]:
                        # rename according to ngspice manual
                        str_temp.append(para[1])
                    elif para[0] in ["Vdc", "Vac", "Idc", "Iac"] and not isinstance(
                        para[1], float
                    ):  # just leave voltages from lines, as ngpsice directly changes the sources and not the parameters
                        pass
                    else:
                        str_temp.append(para[0] + "=" + para[1])

                str_temp = " ".join(str_temp)

                # find sim paras
                sim_paras = ""
                for para in circuit_element.parameters:
                    if isinstance(para, str):
                        pass
                    try:
                        float(para[1])
                    except ValueError:
                        sim_paras = sim_paras + para[1] + "=0 "

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

    def _convert_swd_trans_to_pwl(self, swd_tran: SweepDef):
        time = swd_tran.values
        signal = swd_tran.get_input_signal()
        pwl = " ".join([f"{t:g} {s:g}" for t, s in zip(time, signal)])
        return " PWL(" + pwl + ")"

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
                raise IOError(
                    "DMT -> NGspice: frequencies of AC simulation data do not match."
                )

        # join the ac dataframes into one ac dataframe dfs_ac[0]
        for i_df in range(len(dfs_ac)):
            df = dfs_ac[i_df]
            if i_df == 0:
                y_cols = [specifiers.FREQUENCY]
            else:
                y_cols = []

            for col in df.columns:
                try:
                    if col.specifier == specifiers.SS_PARA_Y:
                        y_cols.append(col)
                except AttributeError:
                    pass  # from AC dataframes ONLY the SS paras are copied other, rest is ignored

            dfs_ac[i_df] = df[y_cols]

        df_ac = pd.concat(dfs_ac, axis=1)

        # join the dc data to the ac data
        n_freq = len(np.unique(freqs[0]))
        df_dc = DataFrame(df_dc.values.repeat(n_freq, axis=0), columns=df_dc.columns)

        df_dc.reset_index(drop=True, inplace=True)
        df_ac.reset_index(drop=True, inplace=True)
        return pd.concat([df_dc, df_ac], axis=1)


def _read_ngspice(filename):
    """read the ngspice output file"""
    # open file
    with open(filename) as my_file:
        list_lines = my_file.readlines()

    # this seems to be printed for verilog modules... probably branch currents, however node is missing?
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
    list_lines = np.array(list_lines, dtype=np.float64)
    n_col = float(len(split_header))
    n_row = float(len(list_lines) / n_col)

    # check if n_row is an integer
    if n_row.is_integer():
        n_row = int(n_row)
    else:
        raise IOError(
            "DMT -> Data_reader: Encountered a weird number of rows in "
            + filename
            + "."
        )

    # check if n_col is an integer
    if n_col.is_integer():
        n_col = int(n_col)
    else:
        raise IOError(
            "DMT -> Data_reader: Encountered a weird number of cols in "
            + filename
            + "."
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


def _read_clean_ngspice_df(filepath, nodes, reference_node, ac_ports):
    """From the df as read directly from ngspice, create a df that has DMT specifiers and is suitable for modeling."""
    df = _read_ngspice(filepath)
    df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate columns
    cols = df.columns
    nodes = [col[2:].upper() for col in cols if col[0:2] == "n_"]

    is_ac = False
    if "frequency" in cols:
        is_ac = True

    # check if more than one device has OpVars
    op_vars = []
    op_var_devices = set()
    for col in cols:
        if col.startswith("@"):
            i_bracket = col.find("[")
            op_var_devices.add(col[1:i_bracket].upper())

    if len(op_var_devices) > 1:
        op_var_multi = True
    else:
        op_var_multi = False

    data = {}
    for col in cols:
        col_raw = col.upper()
        if "#BRANCH" in col_raw:  # current that we should save
            col_raw = col_raw.replace("#BRANCH", "")
            node = next(node for node in nodes if node in col_raw)
            data[specifiers.CURRENT + node] = -df[
                col
            ]  # we want the other current direction
        elif col_raw[0:2] == "N_":  # found a node, will take the voltage
            node = col_raw[2:]
            if "_FORCED" in node:
                data[
                    specifiers.VOLTAGE
                    + node.replace("_FORCED", "")
                    + sub_specifiers.FORCED
                ] = df[col]
            else:
                data[specifiers.VOLTAGE + node] = df[col]
        elif col_raw == "FREQUENCY":
            data[specifiers.FREQUENCY] = np.real(df["frequency"].to_numpy())

        # add opvars
        if col_raw.startswith("@"):
            if op_var_multi:
                dev_op_var = re.search(r"@(.*)\[(.*)\]", col_raw)
                op_var = "{0}.{1}".format(*dev_op_var.groups()).upper()
                data[op_var] = np.real(df[col].to_numpy())
                op_vars.append(op_var)
            else:
                op_var = re.search(r"\[(.*)\]", col_raw).groups()[0].upper()
                data[op_var] = np.real(df[col].to_numpy())
                op_vars.append(op_var)

    new_df = DataFrame(data)

    # dirty: add the Y Parameters
    if is_ac:
        # step one: find which port is begin excited
        node_excited = re.search(r"V_(\w+?)$", filepath.stem).group(1)
        col_v_ne = specifiers.VOLTAGE + node_excited
        ac_voltage = 1  # fallback

        try:
            ac_voltage = new_df[col_v_ne].to_numpy()
            ac_voltage = new_df[col_v_ne + sub_specifiers.FORCED].to_numpy()
        except KeyError:
            pass
        try:
            new_df.drop(axis=1, columns=col_v_ne, inplace=True)
        except KeyError:
            pass
        try:
            new_df.drop(axis=1, columns=col_v_ne + sub_specifiers.FORCED, inplace=True)
        except KeyError:
            pass

        # delete the AC voltages, because why would anyone need them.
        for node in nodes:
            col_v_n = specifiers.VOLTAGE + node
            try:
                new_df.drop(axis=1, columns=col_v_n, inplace=True)
            except KeyError:
                pass
            try:
                new_df.drop(
                    axis=1, columns=col_v_n + sub_specifiers.FORCED, inplace=True
                )
            except KeyError:
                pass

        # step2: now calculate the y parameters Y(X,node)
        for node_2 in nodes:
            col_i_n = specifiers.CURRENT + node_2
            if col_i_n in new_df.columns:
                ac_current = new_df[col_i_n].to_numpy()
                new_df.drop(axis=1, columns=col_i_n, inplace=True)

                y_para = specifiers.SS_PARA_Y + [node_2, node_excited]
                new_df[y_para] = ac_current / ac_voltage

    fallback_dict = {}
    for op_var in op_vars:
        fallback_dict[op_var] = op_var
    return new_df.clean_data(
        nodes,
        reference_node,
        ac_ports=ac_ports,
        fallback=fallback_dict,
        warnings=False,
    )


def _read_clean_ngspice_df_transient(filepath, reference_node, ac_ports):
    """From the df as read directly from ngspice, create a df that has DMT specifiers and is suitable for modeling."""
    df = _read_ngspice(filepath)
    df = df.loc[:, ~df.columns.duplicated()]  # drop duplicate columns
    cols = df.columns
    nodes = [col[2:].upper() for col in cols if col[0:2] == "n_"]

    new_df = DataFrame()
    for col in cols:
        # opvars are not set transient..
        if col.startswith("@"):
            continue

        col_raw = col.upper()
        if "#BRANCH" in col_raw:  # current that we should save
            col_raw = col_raw.replace("#BRANCH", "")
            node = next(node for node in nodes if node in col_raw)
            new_df[specifiers.CURRENT + node] = -df[
                col
            ]  # we want the other current direction
        elif col_raw[0:2] == "N_":  # found a node, will take the voltage
            node = col_raw[2:]
            if "_FORCED" in node:
                new_df[
                    specifiers.VOLTAGE
                    + node.replace("_FORCED", "")
                    + sub_specifiers.FORCED
                ] = df[col]
            else:
                new_df[specifiers.VOLTAGE + node] = df[col]
        elif col_raw == "FREQUENCY":
            new_df[specifiers.FREQUENCY] = np.real(df["frequency"].to_numpy())
        elif col_raw == "TIME":
            new_df[specifiers.TIME] = np.real(df["time"].to_numpy())

    return new_df.clean_data(
        nodes,
        reference_node,
        ac_ports=ac_ports,
        fallback={specifiers.TIME: specifiers.TIME},
        warnings=False,
    )
