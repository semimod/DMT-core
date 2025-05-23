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
import os
import re
import shutil
import _pickle as cpickle  # type: ignore
import json
import copy
import logging
from pathlib import Path
import pandas as pd
from typing import List, Dict, Type, Union

try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

from DMT.core.data_frame import DataFrame
from DMT.core.database_manager import DatabaseManager
from DMT.core.data_reader import read_data
from DMT.core.dut_type import DutTypeFlag, DutTypeInt, DutType
from DMT.core.va_file import VAFileMap
from DMT.core.sweep import Sweep
import DMT.core.technology as dmt_tech
from DMT.config import DATA_CONFIG
from DMT.exceptions import UnknownColumnError

SEMVER_DUTVIEW_CURRENT = VersionInfo(major=1, minor=0)


class DutView(object):
    """DutView is the parent class of all DUTs in DMT.

    All simulation back-end classes must inherit from this class and overwrite the methods that raise NotImplemented errors.
    This ensures that all classes in DMT work independent of the concrete simulation back-end.

    Parameters
    ----------

    database_dir :  str or None
        The directory where all the databases of this project are saved. If None, DMT.config.DATA_CONFIG["directories"]["database"] is used.
    name       :  str
        The name of the DutView object, which is used as a prefix for saving the database and the pickled object.
    dut_type   : :class:`~DMT.core.dut_type.DutType`
        Type of the DutView object, represented by a DutType object (basically an Enumeration).
    nodes      : [string], optional
        List of names of the nodes of the DutView object. Only nodes that shall be present in the DutView's database are relevant.
        They are past in the given order to all df methods which need the small-signal parameters.
    copy_va_files : {False, True}, optional
    force      : {False, True}, optional
        If True, all data found in the duts database are deleted.
    separate_databases : {False, True}, optional
        If True, each simulation is saved in a separate database file and only the needed files are loaded.
        Usefull for large simulation files, like transient simulations. For small files, the lookup in the hard drive takes to long.
    list_copy : [], optional
        List of files or file contents to copy to the simulation directory as additional files.
    t_max : int, optional
        Maximum simulation duration for this dut. This value and the simulation controller value have to be exceeded.
    simulate_on_server : {False, True, None}, optional
        If not set, the config value is used.
    simulator_command : str
        Command to start the correct circuit simulator
    simulator_arguments : list[str]
        List of arguments for the simulator command, will be added one by one before the input file.
    technology     :  :class:`~DMT.core.technology.Technology`, optional
    width          :  float64, optional
        Width in m.
    length         :  float64, optional
        Length in m.
    nfinger        : int, optional
        Number of parallel emitter fingers
    contact_config : str, optional
        String describing the physical contact config for this device. The possible value depends on the technology, example: 'CBEBC'.
    inp_name   :  str
        The name of the input file to be generated.

    Attributes
    ----------
    database_dir :  str
        The directory where all the databases of this project are saved.
    name       :  str
        The name of the DutView object, which is used as a prefix for saving the database and the pickled object.
    manager    :  :class:`~DMT.core.database_manager.DatabaseManager`
        The DatabaseManager object of the DutView, used to interact with its database.
    sim_folder :  str
        Path to the simulation folder
    inp_name   :  str
        The name of the input file to be generated.
    save_dir   : string
        This is the directory were the DutView object will save its object and database.
    dut_dir    : string
        This is the directory were the DutView object will create its pickle file. This equals save_dir+'.h5'
    database_dir     : string
        This is the directory were the DutView object will create its database. This equals save_dir+'.h5'
    dut_type   : :class:`~DMT.core.dut_type.DutType`
        Type of the DutView object, represented by a DutType object (basically an Enumeration).
    nodes      : [string]
        List of names of the nodes of the DutView object. Only nodes that shall be present in the DutView's database are relevant.
        They are past in the given order to all df methods which need the small-signal parameters.
    ac_ports   : [string]
        List of ports for AC simulations. At each port mentioned here a AC source is applied. Defaults to the first 2 nodes.
    list_copy : [data]
        List of path or data to save to the simlation folder. If it is a path, the file is copied. If it is data, a file is created.

    Methods
    -------
    run_simulation(sweep)
        Start the simulation of this DutView object.
    prepare_simulation(sweep)
        Prepare a simulation folder and run make_input().
    make_input(sweep)
        Create the correct simulation input file from this Dut_view together with a Sweep object.
    get_hash()
        Return a unique hash for this Dut without considering the Sweep.
    save()
        Save this DutView as a pickled .p file to save_dir.
    __getstate__()
        This helper methods helps in the pickling process.
    __setstate__(state)
        This helper methods helps in the pickling process.
    load_dut(save_dir)
        Static class method. Loads a DutView object from a pickle file with full path save_dir.
    add_data(df, key, force=True)
        Add data into the DutView's database.
    get_data(key)
        Get the data stored in key from the DutView's database.
    check_existence_sweep(self, sweep)
        Returns True if the simulation corresponding to this DutView object in combination with Sweep object sweep has already been run.
    del_db()
        Delete the DutView's database.
    clean_all_data()
        Iterate through all keys in the DutView's database and try to clean the column names according to the internal DMT format.
    """

    def __init__(
        self,
        database_dir,
        name,
        dut_type,
        *,
        reference_node,
        copy_va_files=True,
        force=False,
        loading=False,
        separate_databases=False,
        list_copy=None,
        t_max=None,
        sim_dir=DATA_CONFIG["directories"]["simulation"],
        simulate_on_server=None,
        simulator_command="",
        simulator_arguments=None,
        technology: "dmt_tech.Technology" = None,
        width=None,
        length=None,
        nfinger=None,
        contact_config=None,
        flavor=None,
        ac_ports=None,
        nodes=None,
        inp_name=None,
        va_code_filter=None,
    ):
        if database_dir is None:
            self._database_dir = DATA_CONFIG["directories"]["database"]
        else:
            if isinstance(database_dir, Path):
                self._database_dir = database_dir.expanduser().resolve()
            else:
                self._database_dir = Path(database_dir).expanduser().resolve()

        if os.path.isabs(name):
            raise IOError(
                "DMT.DutView: The DutView name must not be a valid absolute directory path!"
            )
        self.name = name
        self._copy_va_files = copy_va_files
        # files to be copied into simulation directory
        if list_copy is None:
            self.list_copy = []
        else:
            if not isinstance(list_copy, list):
                self.list_copy = [list_copy]
            else:
                self.list_copy = list_copy
        self._list_va_file_contents: list[VAFileMap] = []

        self.manager = DatabaseManager()
        # if the dut already exists and no force -> error!
        if self.save_dir.exists():
            if force:
                # delete the saved database
                self.del_db()
                self.del_dut()
            elif loading:
                pass
            else:
                raise IOError(
                    "DMT.DutView: Created a DutView with a save_dir which already exists. Better load that one or remove it."
                )

        # attributes for data management
        self._separate_databases = separate_databases
        self._data: dict[str, DataFrame] = {}  # this is now hidden

        self.dut_type: Union[DutTypeFlag, DutTypeInt] = dut_type

        if nodes is None:
            self.nodes = dut_type.get_nodes()
        else:
            if isinstance(nodes, str):
                self.nodes = nodes.split(",")
            else:
                self.nodes = nodes

        if ac_ports is None:
            self.ac_ports = self.nodes[0:2]  # ports for AC simulations
        else:
            self.ac_ports = ac_ports

        self.reference_node = reference_node
        if reference_node is None:
            raise IOError("Reference node not specified. DMT does not support this.")

        # simulation attributes
        self.inp_name = inp_name
        self.sim_command = simulator_command
        self.va_code_filter = va_code_filter

        if simulator_arguments is None:
            self.sim_args = []
        else:
            self.sim_args = simulator_arguments

        if not isinstance(sim_dir, Path):
            sim_dir = Path(sim_dir)
        self.sim_dir = sim_dir

        self.technology = technology
        self.contact_config = contact_config
        self.flavor = flavor
        self.width = width
        self.length = length
        self.nfinger = nfinger
        try:
            self.perimeter = (self.width + self.length) * 2  # type: ignore
            self.area = self.width * self.length  # type: ignore
        except TypeError:
            self.perimeter = None
            self.area = None

        # simulation attributes
        self.t_max = t_max
        if simulate_on_server is None:
            self.simulate_on_server = DATA_CONFIG["backend_remote"]
        else:
            self.simulate_on_server = simulate_on_server
        self.zip_result = True

        # in these attributes, store the name of another dut that has been used for deembedding...for documentation this is nice
        self.open_deembedded_with = "-"
        self.short_deembedded_with = "-"

    def prepare_simulation(self, sweep: Sweep):
        """Creates a simulation folder, appends the sweep to the structure definition and creates a input file in the simulation folder.

        Parameters
        ----------
        sweep : Sweep
        """
        logging.info(
            "Preparing to simulate the Dut %s the sweep with the hash %s",
            self.get_hash(),
            sweep.get_hash(),
        )

        # set the simulation folder
        sim_folder = self.get_sim_folder(sweep)

        try:
            sim_folder.mkdir(parents=True)
        except OSError:
            logging.debug("Folder already existed! Will be deleted")
            try:
                shutil.rmtree(str(sim_folder))
                sim_folder.mkdir(parents=True, exist_ok=True)
            except FileNotFoundError:
                raise OSError(
                    "Simulation folder exists but can not be deleted. Is the location mounted correctly? Hint: Shut down Windows correctly."
                )

        # copy va files into simulation folder?
        sim_folder = self.get_sim_folder(sweep)
        if self._copy_va_files:
            for vafile in self._list_va_file_contents:
                vafile.write_files(sim_folder, filter=self.va_code_filter)
        else:
            # write the files into a separate folder in simulations/va_files/HASH/
            va_files_dir = self.sim_dir / "VA_codes"
            for vafile in self._list_va_file_contents:
                dir_code = va_files_dir / vafile.get_tree_hash()
                if not dir_code.is_dir():
                    vafile.write_files(dir_code, filter=self.va_code_filter)

        inp_content = self.make_input(sweep)
        (sim_folder / self.inp_name).write_text(inp_content)
        if DATA_CONFIG["server"]["use_pbs"] and DATA_CONFIG["backend_remote"]:
            pbs_content = self.make_pbs(sweep)  # needs to be implemented by the DUT
            (sim_folder / "pbs_job").write_text(pbs_content)

        for data_copy in self.list_copy:
            try:
                if os.path.isfile(data_copy):
                    filename = os.path.basename(data_copy)
                    shutil.copyfile(data_copy, os.path.join(sim_folder, filename))
                else:
                    # filename ??? Setting default file name... seems crazy here
                    (sim_folder / "datafile.tbl").write_text(data_copy)
            except TypeError:
                file_content = self._write_data_table(data_copy)
                file_name = sim_folder / "datafile.tbl"
                with file_name.open("a") as file_table:
                    file_table.write(file_content)

        str_log = " Prepared a simulation in the folder: \n{0:s}".format(str(sim_folder))
        print(str_log)
        logging.info(str_log)

    def get_start_sim_command(self):
        """Returns the command to start the simulation

        Returns
        -------
        str
        """
        return self.sim_command + " " + " ".join(self.sim_args) + " " + self.inp_name

    def _write_data_table(self, data):
        """Option to write a data table for a simulation. As the file type may depend on the simulator this is not implemented here!"""
        raise NotImplementedError("Has to be overwritten in the subclass.")

    def make_pbs(self, sweep):
        """Create a PBS script for the PBS job system. (See: https://albertsk.files.wordpress.com/2011/12/pbs.pdf)"""
        raise NotImplementedError("Not Implemented for this Dut Class!")

    def make_input(self, sweep: Sweep):
        """Joins simulation header with a given Sweep object and returns it.

        Parameters
        ----------
        sweep : :class:`DMT.core.sweep.Sweep`
            Sweep specification according to the Sweep class.
        """
        raise NotImplementedError("DutView does not implement the concrete make_input method!")

    def get_hash(self):
        """Return a unique hash for this Dut without (!) considering the Sweep.

        Returns
        -------
        hash : float64
            Hash that corresponds to this DUT.
        """
        raise NotImplementedError("DutView does not implement the concrete get_hash method!")

    def import_output_data(self, sweep, delete_sim_results=False):
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
        raise NotImplementedError(
            "DutView does not implement the concrete import_output_data method!"
        )

    def validate_simulation_successful(self, sweep: Sweep):
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
        raise NotImplementedError(
            "DutView does not implement the concrete import_output_data method!"
        )

    @property
    def save_dir(self) -> Path:
        if self.get_hash():
            return self.database_dir / (self.name + "_hash_" + str(self.get_hash()))
        else:
            return self.database_dir / self.name

    @property
    def database_dir(self):
        return self._database_dir

    @database_dir.setter
    def database_dir(self, new_dir):
        """Make sure data is loaded before changing save location of this DutView."""
        if not self._data:
            self.load_db()

        self._database_dir = Path(new_dir)

    def get_db_dir(self, name="db") -> Path:
        """Returns the name for a db, either use 'db' for regular behavior or use 'sweep.get_hash()' for a db per sweep."""
        return self.save_dir / (name + ".h5")

    @property
    def dut_dir(self):
        return self.save_dir / "dut.json"

    @property
    def data(self):
        """data is a property to ensure loading before usage.

        As _data is a dict, the getter is also called before setting. So the separate setter is not necessary.
        If someone tries to set dut.data an attribute error occurs, but setting dict entries is possible directly.

        """
        if not self._data:  # empty dict evaluates to false
            self.load_db()

        return self._data

    def get_sim_folder(self, sweep: Sweep) -> Path:
        """Returns the simulation folder of the given sweep

        Parameters
        ----------
        sweep  :  Sweep
            Sweep object that corresponds to the folder.

        Returns
        -------
        str
            Path to the simulationfolder
        """
        return (
            self.sim_dir
            / (self.name + str(self.get_hash()))
            / (sweep.name + "_" + sweep.get_hash())
        )

    def delete_sim_results(self, sweep: Sweep, ignore_errors=False):
        """Deletes the simulation results of the given sweep.

        Parameters
        ----------
        sweep  :  Sweep
            Sweep object that corresponds to the folder.
        ignore_errors : {False, True}, optional
            Passed through to :meth:`shutil.rmtree`. If ignore_errors is true, errors resulting from failed removals will be ignored.
        """
        sim_folder = self.get_sim_folder(sweep)
        shutil.rmtree(sim_folder, ignore_errors=ignore_errors)

        logging.info(
            "The simulation data of the sweep %s with the hash %s was deleted",
            sweep.name,
            sweep.get_hash(),
        )

    def save(self, **kwargs):
        """Save this DutView as a json file and the also the data into the database on the hard drive. The kwargs are passed on to :py:method::`DMT.core.dut_view.DutView.info_json()` or the overwritten method."""
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._database_dir = self._database_dir.resolve()  # convert to absolute path

        self.save_db()

        self.dut_dir.write_text(json.dumps(self.info_json(**kwargs), indent=4), encoding="utf8")

        if self.dut_dir.with_suffix(".p").exists():
            # it there is still a "old" pickle file in the directory -> remove it
            self.dut_dir.with_suffix(".p").unlink()

    def info_json(self, **_kwargs) -> Dict:
        """Returns a dict with serializeable content for the json file to create.

        Add the info about the concrete subclass to create here! See :py:method::`DMT.core.dut_meas.DutMeas.info_json()` for an example implementation.

        Returns
        -------
        dict
            serialized dictionary ready to be dumped to json.
        """
        if self.technology is None:
            tech = self.technology
        else:
            tech = self.technology.serialize()
        return {
            "__DutView__": str(SEMVER_DUTVIEW_CURRENT),
            "copy_va_files": self._copy_va_files,
            "list_copy": [str(to_copy) for to_copy in self.list_copy],
            "list_va_file_contents": [
                va_file.export_dict() for va_file in self._list_va_file_contents
            ],
            "separate_databases": self._separate_databases,
            "database_dir": str(self._database_dir),
            "dut_type": self.dut_type.serialize(),
            "name": self.name,
            "nodes": self.nodes,
            "ac_ports": self.ac_ports,
            "reference_node": self.reference_node,
            "inp_name": self.inp_name,
            "sim_command": self.sim_command,
            "va_code_filter": self.va_code_filter,
            "sim_args": self.sim_args,
            "sim_dir": str(self.sim_dir),
            "technology": tech,
            "contact_config": self.contact_config,
            "flavor": self.flavor,
            "width": self.width,
            "length": self.length,
            "nfinger": self.nfinger,
            "t_max": self.t_max,
            "simulate_on_server": self.simulate_on_server,
            "zip_result": self.zip_result,
            "open_deembedded_with": self.open_deembedded_with,
            "short_deembedded_with": self.short_deembedded_with,
        }

    def __getstate__(self):
        """Return state values to be pickled. Implemented according `to <https://www.ibm.com/developerworks/library/l-pypers/index.html>`_ .

        Notes
        -----
        ..todo:
            iterate through all properties and throw away the HDFStore objects.
        """
        d = copy.copy(self.__dict__)

        if "_data" in d:
            del d["_data"]

        return d

    def __setstate__(self, state):
        """Return state values to be pickled. Implemented according `to <https://www.ibm.com/developerworks/library/l-pypers/index.html>`_ ."""
        self.__dict__ = state  # pylint: disable=attribute-defined-outside-init
        self.__dict__["_data"] = {}

    @staticmethod
    def load_dut(
        file_dut,
        classes_technology: List[Type["dmt_tech.Technology"]] = None,
        classes_dut_view: List[Type["DutView"]] = None,
    ) -> "DutView":
        """Static class method. Loads a DutView object from a pickle file with full path save_dir.

        Parameters
        ----------
        file_dut  :  str or os.Pathlike
            Path to the json or pickle DutView file that shall be loaded.
        classes_technology : List[Type[Technology]]
            All possible technologies this loaded DutView can have. One will be choosen according to the serialized technology loaded from the file.
        classes_dut_view : List[Type[DutView]]
            All possible DutViews this loaded DutView can be. One will be choosen according to the serialized dutview class name loaded from the file.

        Returns
        -------
        DutView
            Loaded object.
        """
        if not isinstance(file_dut, Path):
            file_dut = Path(file_dut)

        if file_dut.suffix == ".json":
            from DMT.core import _DEFAULT_DUT_VIEWS

            if classes_dut_view is None:
                classes_dut_view = _DEFAULT_DUT_VIEWS
            else:
                classes_dut_view += _DEFAULT_DUT_VIEWS

            with file_dut.open("r", encoding="utf8") as file_json:
                json_content = json.load(file_json)

            # the key on the first dictionary is the class
            clsstr_dut_view = list(json_content.keys())[0]
            try:
                cls_dut_view = next(
                    cls_dv for cls_dv in classes_dut_view if str(cls_dv) == clsstr_dut_view
                )
            except StopIteration as err:
                raise IOError(
                    f"DMT.DutLib: Encountered unknown DutView class while loading the library: {clsstr_dut_view}"
                ) from err

            dut = cls_dut_view.from_json(json_content[clsstr_dut_view], classes_technology)

        elif file_dut.suffix == ".p":
            with file_dut.open(mode="rb") as handle:
                dut = cpickle.load(handle)
        else:
            raise IOError("DMT.DutView: I can not load an file ending on " + file_dut.suffix)

        # check the dirs:
        # obtain database_dir from file_dut
        database_dir = file_dut.parent.parent

        # check if equal, if not -> changed machine -> broken absolute path
        if database_dir != dut._database_dir:  # pylint: disable=protected-access
            dut._database_dir = database_dir  # pylint: disable=protected-access

        if not os.path.exists(dut.sim_dir):
            dut.sim_dir = DATA_CONFIG["directories"]["simulation"]

        return dut

    @classmethod
    def from_json(
        cls,
        json_content: Dict,
        classes_technology: List[Type["dmt_tech.Technology"]],
        subclass_kwargs: Dict = None,
    ) -> "DutView":
        """Static class method. Loads a DutView object from a pickle file with full path save_dir.

        Parameters
        ----------
        json_content  :  dict
            Readed dictionary from a saved json DutView.
        classes_technology : List[Type[Technology]]
            All possible technologies this loaded DutView can have. One will be choosen according to the serialized technology loaded from the file.
        subclass_args: List = None,
            Positional arguments needed
        subclass_kwargs: Dict = None,

        Returns
        -------
        DutView
            Loaded object.
        """
        if json_content["__DutView__"] != SEMVER_DUTVIEW_CURRENT:
            raise NotImplementedError("DMT.DutView: Unknown version of DutView to load!")

        serialized_technology = json_content["technology"]
        if serialized_technology is None:
            tech = None
        else:
            try:
                cls_technology = next(
                    cls_tech
                    for cls_tech in classes_technology
                    if str(cls_tech.__name__) in serialized_technology["class"]
                )
            except StopIteration as err:
                raise IOError(
                    "DMT.DutLib: Encountered unknown Technology class while loading the library."
                ) from err
            args = serialized_technology.get("args", [])
            kwargs = serialized_technology.get("kwargs", {})
            if serialized_technology.get("constructor", None) is None:
                tech = cls_technology(*args, **kwargs)
            else:
                tech = getattr(cls_technology, serialized_technology["constructor"])(
                    *args, **kwargs
                )

        if subclass_kwargs is None:
            subclass_kwargs = {}

        dut_view = cls(
            database_dir=json_content["database_dir"],
            name=json_content["name"],
            dut_type=DutType.deserialize(json_content["dut_type"]),
            **subclass_kwargs,
            reference_node=json_content["reference_node"],
            copy_va_files=json_content["copy_va_files"],
            force=False,
            loading=True,
            separate_databases=json_content["separate_databases"],
            list_copy=json_content["list_copy"],
            t_max=json_content["t_max"],
            sim_dir=json_content["sim_dir"],
            simulate_on_server=json_content["simulate_on_server"],
            simulator_command=json_content["sim_command"],
            simulator_arguments=json_content["sim_args"],
            technology=tech,
            width=json_content["width"],
            length=json_content["length"],
            nfinger=json_content["nfinger"],
            contact_config=json_content["contact_config"],
            flavor=json_content["flavor"],
            ac_ports=json_content["ac_ports"],
            nodes=json_content["nodes"],
            inp_name=json_content["inp_name"],
            va_code_filter=json_content["va_code_filter"],
        )

        dut_view._list_va_file_contents = [
            VAFileMap.import_dict(va_file) for va_file in json_content["list_va_file_contents"]
        ]
        dut_view.zip_result = json_content["zip_result"]
        dut_view.open_deembedded_with = json_content["open_deembedded_with"]
        dut_view.short_deembedded_with = json_content["short_deembedded_with"]
        return dut_view

    def add_data(
        self,
        data: Union[DataFrame, Sweep, str, os.Pathlike],
        key: Union[str, None] = None,
        force: bool = True,
        validate: bool = True,
        **kwargs,
    ):
        """Add a measurement or simulation data to the DutView's data.

        Parameters
        ----------
        data   :   DataFrame, sweep or str
            If DataFrame: Directly added to the data using the given key.
            If str: Full path to the file that shall be added to the database
            if sweep: Simulated sweep to import.
        key    :   string, optional
            Key that shall be used in the database to save the data.
        force  :  bool, optional
            Default=True. If = True, the data is added even if it already exists.
        kwargs : keyword arguments, optional
            Passed on to read_data in case of str as a data argment.
        """
        if key is None:
            try:
                key = self.get_sweep_key(data)
            except AttributeError:
                pass

        if key in self.data.keys():
            if force:
                logging.info(
                    "DMT -> DutView -> add_data(): Removed a dataframe with key %s since it was already existent in dut.data.",
                    key,
                )
                self.remove_data(key)
            else:
                logging.info(
                    "DMT -> DutView -> add_data(): Skipped a dataframe with key %s since it was already existent in dut.data.",
                    key,
                )
                return

        if isinstance(data, DataFrame) or isinstance(data, pd.DataFrame):
            # it is a regular dataframe
            # prevents pandas bug with non-unique columns:
            if not data.columns.is_unique:
                data = data.loc[:, ~data.columns.duplicated()]
            self.data[key] = data
        elif isinstance(data, Sweep):
            # simulation valid?
            if not validate:
                self.validate_simulation_successful(data)
            # try special import
            self.import_output_data(data)
        else:
            self.data[key] = read_data(data, **kwargs)

        logging.info(
            "DMT -> DutView -> add_data(): Added a dataframe with key %s to the dut.",
            key,
        )

    def remove_data(self, key: str):
        """Remove a measurement or simulation dataframe from the DutView's data.

        Parameters
        ----------
        key    :   string
            Key that shall be removed from the database.
        """
        del self.data[key]

    def get_data(self, key: str = "iv", sweep: Sweep = None) -> DataFrame:
        """Return data stored in the DutView's data.

        One needs to specify either:

        - key      : The data stored under the path key in the dut's database is returned.
        - sweep    : Get the data from this sweep. If none, key must be a valid key for the database.
        - sweep+key: Return the data stored as self.get_sweep_key(sweep)+'/'+key from the dut's database.

        Parameters
        ----------
        key    :  str, optional, {'iv'}
            The key of the data in the DutView's database that shall be retrieved.
        sweep  :  :class:`DMT.core.sweep.Sweep`, optional
            The sweep whose data shall be looked for.
        """
        if self._separate_databases:
            if sweep is None:
                raise IOError("If you do not know the sweep, just use dut.data[key]..")

            key = self.join_key(self.get_sweep_key(sweep), key)
            if key not in self._data.keys():
                self.load_db(sweep)

        else:
            if sweep is not None:
                key = self.join_key(self.get_sweep_key(sweep), key)

            if not self._data:
                self.load_db()

        try:
            return self._data[key]
        except KeyError:
            ## missed the starting '/' ?
            return self._data[self.join_key("", key)]

    def del_db(self):
        """Delete the DutView's complete database."""
        # iterate over the folder in case of self.separate_databases
        for my_file in self.save_dir.glob("*.h5"):
            self.manager.del_db(my_file)
        logging.info("DMT -> DutView -> del_data(): Deleted a complete database.")

    def del_dut(self):
        """Delete the DutView's pickled file."""
        self.dut_dir.unlink(missing_ok=True)
        logging.info("DMT -> DutView -> del_dut(): Deleted a DutView object.")

    def clean_data(self, fallback=None, **kwargs):
        """Clean the dataframe columns of the DataFrame objects in this DutMeas objects database.

        Parameters
        ----------
        fallback : dict, optional
            Is used to update self.nodes_fallback for this special key to clean.

        """
        if fallback is None:
            fallback = {}
        for key, df in self.data.items():
            try:
                df = df.clean_data(
                    self.nodes,
                    self.reference_node,
                    fallback=fallback,
                    ac_ports=self.ac_ports,
                    **kwargs,
                )
            except AttributeError:
                df.__class__ = DataFrame  # cast to DMT.DataFrame
                df = df.clean_data(
                    self.nodes,
                    self.reference_node,
                    fallback=fallback,
                    ac_ports=self.ac_ports,
                    **kwargs,
                )
            except UnknownColumnError as err:
                raise UnknownColumnError(
                    "The DutView is "
                    + self.name
                    + " of DutType "
                    + self.dut_type.get_string()
                    + " with the ac_ports "
                    + str(self.ac_ports)
                ) from err

            self.data[key] = df

    def save_db(self, sweep_keys=None, sweeps=None):
        """Write a database for this dut. If it already exists it is overwritten. Does NOT save all keys starting with '_'

        Parameters
        ----------
        sweep_keys : list[str], optional
            List of sweeps to save to database. Usefull if a lot of data is loaded but only a part should be saved to the hard drive database.

        """
        if not self._data:
            return  # nothing to do here

        if self._separate_databases:
            if sweep_keys is None:
                if sweeps is None:
                    # find all sweeps in self.data
                    sweep_keys = []
                    for key in self._data.keys():
                        ## key is equal except for the last part -> same sweep
                        sweep_key = self.join_key(*self.split_key(key)[0:-1])
                        if sweep_key not in sweep_keys:
                            sweep_keys.append(sweep_key)
                else:
                    sweep_keys = []
                    for sweep in sweeps:
                        sweep_keys.append(self.get_sweep_key(sweep))

            for sweep_key in sweep_keys:
                data_to_save = {}
                for key, data in self._data.items():
                    if (
                        not key.startswith("_")
                        and self.join_key(*self.split_key(key)[0:-1]) == sweep_key
                    ):
                        data_to_save[key] = data

                self.manager.save_db(self.get_db_dir(sweep_key), data_to_save)
        else:
            data_to_save = {}
            for key, data in self._data.items():
                if not key.startswith("_"):
                    data_to_save[key] = data

            self.manager.save_db(self.get_db_dir(), data_to_save)

    def load_db(self, sweep=None):
        """Load saved data from the database into the object.

        If the complete dictionary is reloaded, here it is set directly to self._data.
        if separate databases is activated it loads only the given sweep (and it has to be given then!)

        Parameters
        ----------
        sweep : Sweep or str, optional
            In case of separate databases, the sweep must be given either directly or as string name

        Returns
        -------
        bool
            Is True if the database was loaded successfully
        """
        if self._separate_databases:
            if sweep is None:
                return True
                # raise IOError(
                #     "DMT->DutView: If a separated database should be loaded, the sweep/databasefilename has to be given"
                # )

            if isinstance(sweep, str):
                if sweep == "all":
                    # iter throuh self.save_dir and load all .h5
                    for file_db in self.save_dir.glob("**/*.h5"):
                        self._data.update(self.manager.load_db(file_db))

                    return True
                else:
                    name = sweep
            else:
                name = self.get_sweep_key(sweep)

            try:
                self._data.update(self.manager.load_db(self.get_db_dir(name)))
            except FileNotFoundError:
                return False
        else:
            try:
                self._data = self.manager.load_db(self.get_db_dir())
            except FileNotFoundError:
                return False

        return True

    def check_existence_sweep(self, sweep: Sweep):
        """Return true, if the combination dut+sweep has already been simulated.

        If self.data is None, the database is loaded first.

        Parameters
        ----------
        sweep  : :class:`DMT.core.sweep.Sweep`
            Sweep object that can return a hash.

        Returns
        -------
        existence  :  bool
            Is True if the combination dut+sweep has already been simulated.

        """
        key_sweep = self.get_sweep_key(sweep)
        if self._separate_databases:
            if not any(key_sweep in data_key for data_key in self.data.keys()):  # needs full check
                self.load_db(sweep)
        else:
            if not self._data:  # easy check
                self.load_db()

        return any(key_sweep in data_key for data_key in self.data.keys())

    def join_key(self, *parts_key):
        """Joins the parts of the key into one key for self.dict

        Parameters
        ----------
        parts_key : iterable

        Returns
        -------
        str
            parts_key[0]/parts_key[1]/.../parts_key[-1]
        """
        return "/".join(parts_key)

    def split_key(self, key):
        """Splits the key up in its parts.

        Parameters
        ----------
        key : str

        Returns
        -------
        list[str]
            key splitted at '/'

        """
        return key.split("/")

    def get_sweep_key(self, sweep: Sweep):
        """Key for the dict in dut.data.

        Parameters
        ----------
        sweep : :class:`~DMT.core.sweep.Sweep` or str
            Either the key for the given sweep or if it is a string, directly the string

        Returns
        -------
        key : str
        """
        try:
            return self.join_key(sweep.get_temperature(), sweep.name + "_" + sweep.get_hash())
        except AttributeError:
            # given sweep parameter does not have a get_hash(), is it a string?!?
            return sweep

    def get_key_temperature(self, key):
        """Function that returns the temperature of a given data key. Overwrite this if the measurements differ from the default DMT naming.

        Default naming is:

        * Single temperature: "Txxx.xxK"
        * List of temperatures: "T(xxx.xx,yyy.yy,...)K"
        * Range of temperatures: "T[xxx.xx-sss.ss-yyy.yy]K", s is the step

        Parameters
        ----------
        key : str
            Key that shall be evaluated.

        Returns
        -------
        temp : float
            The temperature at which the measurement "key" has been conducted in Kelvin.
        """
        key_parts = self.split_key(key)

        # first check the best and most useful way for a single temperature
        for key_part in key_parts:
            re_temp = re.search(r"T?([0-9p\.]+)K", key_part)
            if re_temp:
                try:
                    # always replace "p" with ".", if it is already with ".", it doesnt matter
                    return round(float(re_temp.group(1).replace("p", ".")), 3)
                except ValueError:
                    # if a value error in the except clause happens, try the next key part.
                    pass

        # check for list
        for key_part in key_parts:
            re_temp = re.search(r"T[(](.+)[)]K", key_part)
            if re_temp:
                try:
                    str_temps = re_temp.group(1).split(",")
                    return [round(float(str_temp), 3) for str_temp in str_temps]
                except ValueError:
                    # if a value error in the except clause happens, try the next key part.
                    pass

        # check for range
        for key_part in key_parts:
            re_temp = re.search(r"T\[(.+)\)K", key_part)
            if re_temp:
                try:
                    str_temps = re_temp.group(1).split("-")
                    return (round(float(str_temp), 3) for str_temp in str_temps)
                except ValueError:
                    # if a value error in the except clause happens, try the next key part.
                    pass

        # alternative:
        for key_part in key_parts:
            if key_part.startswith("T"):
                try:
                    return round(float(key_part[1:].replace("p", ".")), 3)
                except ValueError:
                    # if a value error in the except clause happens, try the next key part.
                    pass

        # finally as a last escape: direct conversion :(
        for key_part in key_parts:
            try:
                return round(float(key_part.replace("p", ".")), 3)
            except ValueError:
                # if a value error in the except clause happens, try the next key part.
                pass

        raise NameError(
            "DMT -> DutMeas -> get_key_temperature: Was not able to extract the temperature from the key: "
            + key
            + "."
        )
