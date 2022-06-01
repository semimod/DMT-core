""" This module supplies a class to manage all simulations, regardless of the device simulator.

It works together with the DutView class, which is the subclass of all device simulators.
Features:

* Manages all simulations in a unified way, independent of the actual simulation backend.
* Supports to run simulations on multiple cores in parallel
* Supports to run simulations on a remote server (including file up- and download)

Author: Mario Krattenmacher | mario.krattenmacher@semimod.de
Author: Markus Müller | markus.mueller@semimod.de
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
import copy
import logging
import time
import subprocess
import itertools
from joblib import Parallel, delayed
from reprint import output
from pathlib import Path, PurePosixPath, PureWindowsPath
import multiprocessing

from DMT.core import Singleton, print_progress_bar
from DMT.config import DATA_CONFIG
from DMT.exceptions import SimulationUnsuccessful, SimulationFail

# import them always -> can become very annoying otherways (if default is False but one dut is remote)
from tempfile import NamedTemporaryFile
from zipfile import ZipFile

try:
    import paramiko
    from scp import SCPClient, SCPException
except ImportError:
    pass


def upload_progress(filename, size, sent):
    """Callback function for Paramiko SCP Client while uploading files."""
    print_progress_bar(sent, size, prefix="Uploading Simulations", suffix=filename, length=50)


class SimCon(object, metaclass=Singleton):
    """Simulation controller class. SINGLETON design pattern.

    Parameters
    ----------
    n_core  :  int
        Number of cores that shall be used for simulations.
    t_max   :  float
        Timeout for simulations. If a simulation runs longer than t_max in seconds, it is killed.

    Attributes
    ----------
    n_core  :  int
        Number of cores that shall be used for simulations.
    t_max   :  float
        Timeout for simulations. If a simulation runs longer than t_max in seconds, it is killed.
    sim_list :  [{'dut': :class:`~DMT.core.dut_view.DutView`, 'sweep': :class:`~DMT.core.sweep.Sweep`}]
        A list of dicts containing the queued simulations. Each dict holds a 'dut' key value pair and a 'sweep' key value pair.

    ssh_client
        Client to execute SSH commands on a remote server.
    scp_client
        Client to transfer files to a remote server via SCP.
    """

    def __init__(self, n_core=None, t_max=30):
        if n_core is None:
            # Use all available threads by default (for best performance)
            self.n_core = multiprocessing.cpu_count()
        else:
            self.n_core = n_core
        self.t_max = t_max
        self.sim_list = []

        ### ssh stuff
        self.ssh_client = None
        self.scp_client = None

    def clear_sim_list(self):
        """Remove everything from the sim_list"""
        self.sim_list = []

    def append_simulation(self, dut=None, sweep=None):
        """Adds DutViews together with Sweeps to the list of simulations sim_list.

        This methods adds each dut with a copy of each sweep to the simulation list.

        Parameters
        ----------
        dut : :class:`~DMT.core.dut_view.DutView` or [:class:`~DMT.core.dut_view.DutView`]
            Objected of a subclass of DutView. This object describes the device to be simulated and specifies the backend.
        sweep : :class:`~DMT.core.sweep.Sweep` or [:class:`~DMT.core.sweep.Sweep`]
            Definition of the sweep to be performed on the DUT according to the Sweep class.
        """
        if not isinstance(dut, list):
            dut = [dut]
        if isinstance(sweep, list):
            sweep = [copy.deepcopy(sweep_a) for sweep_a in sweep]
        else:
            sweep = [copy.deepcopy(sweep)]

        self.sim_list += [
            {"dut": dut_a, "sweep": sweep_a} for dut_a, sweep_a in itertools.product(dut, sweep)
        ]

    def run_and_read(self, force=False, remove_simulations=False, parallel_read=False):
        """Run all queued simulations and load the results into the Duts' databases.

        Parameters
        ----------
        force : bool, optional
            If True, the simulations will be run and saved back. If False, the simulations will only be run if that has not already been done before. This is ensured using the hash system., by default False
        remove_simulations : bool, optional
            If True, the simulation results will be deleted after read in, by default False. Activate to save disk space.
        parallel_read : bool, optional
            If True, the simulation results are read in using joblib parallel, by default False. Is False because some simulators have issues with this...

        Returns
        -------
        [type]
            [description]
        """
        # reduce number of jobs if we only read a very low number of simulations
        n_jobs = self.n_core if len(self.sim_list) > self.n_core else len(self.sim_list)
        if n_jobs == 0:  # sim list is empty
            return True, False  # all sims were successfull, but no simulations were run
        elif not parallel_read:
            n_jobs = 1

        run_sims = False
        if force:
            logging.info("Simulations forced!")
            sims_to_simulate = self.sim_list
            run_sims = True

        with Parallel(n_jobs=n_jobs, verbose=10) as parallel:
            if not force:
                # check which simulations really need to be run
                n_tot = len(self.sim_list)
                if parallel_read:
                    print("Checking which simulations need to be run in parallel:")
                    sims_checked = parallel(
                        delayed(_check_simulation_needed)(i_sim, n_tot, **sim)
                        for i_sim, sim in enumerate(self.sim_list)
                    )
                else:
                    print("Checking which simulations need to be run:")
                    # parallel not working with VAE modelcard currently since get_circuit is monkey patched
                    sims_checked = [
                        _check_simulation_needed(i_sim, n_tot, **sim)
                        for i_sim, sim in enumerate(self.sim_list)
                    ]

                print_progress_bar(n_tot, n_tot, prefix="Finish", length=50)
                print("\n")  # new line after the progress bar

                sims_to_simulate = []
                # add data to the duts and filter simulations to do
                for sim_to_do, sim_checked in zip(
                    self.sim_list, sims_checked
                ):  # as we are keeping the order, we can copy the data over
                    if sim_checked is None:
                        sims_to_simulate.append(sim_to_do)
                    else:
                        sim_to_do["dut"].data.update(sim_checked)

                run_sims = bool(sims_to_simulate)  # will be False if list is empty

            # remote simulations ?
            if any([sim for sim in sims_to_simulate if sim["dut"].simulate_on_server]):
                self.create_ssh_client()

            # start the simulations using the simulation control.
            process_finished = self.run_simulations(sims_to_simulate)

            if process_finished:
                if parallel_read:
                    print("Reading in the results in parallel:")
                    sims_read = parallel(
                        delayed(_read_process_results)(
                            process["success"], process["dut"], process["sweep"]
                        )
                        for process in process_finished
                    )
                else:
                    print("Reading in the results:")
                    # parallel not working with VAE modelcard currently since get_circuit is monkey patched
                    sims_read = [
                        _read_process_results(process["success"], process["dut"], process["sweep"])
                        for process in process_finished
                    ]
                all_sim_success = all(sim["success"] for sim in sims_read)
                # read data
                for sim in sims_read:
                    # find dut in self.sim_list
                    dut = next(
                        sim_to_do["dut"]
                        for sim_to_do in self.sim_list
                        if sim_to_do["dut"].get_hash() == sim["dut_hash"]
                    )
                    dut.data.update(sim["data"])
            else:
                all_sim_success = True  # no simulations run -> all successfull

        if self.ssh_client is not None:
            self.close_ssh_client()

        if remove_simulations:
            # if storage saving is on, the read simulations can be deleted:
            for sim in self.sim_list:
                sim["dut"].delete_sim_results(sim["sweep"], ignore_errors=True)

        # reset the queue
        self.sim_list = []

        return (
            all_sim_success,
            run_sims,
        )  # the list is empty if no simulations were necessary, empty list -> False

    def create_ssh_client(self):
        """Creates the clients to communicate with the server."""
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(
            DATA_CONFIG["server"]["adress"],
            username=DATA_CONFIG["server"]["ssh_user"],
            key_filename=str(Path(DATA_CONFIG["server"]["ssh_key"]).expanduser()),
            disabled_algorithms=dict(pubkeys=["rsa-sha2-512", "rsa-sha2-256"]),
        )

        self.scp_client = SCPClient(
            self.ssh_client.get_transport(), socket_timeout=self.t_max, progress=upload_progress
        )

        # ensure the correct path:
        if DATA_CONFIG["server"]["unix"]:
            DATA_CONFIG["server"]["simulation_path"] = PurePosixPath(
                DATA_CONFIG["server"]["simulation_path"]
            )
        else:
            DATA_CONFIG["server"]["simulation_path"] = PureWindowsPath(
                DATA_CONFIG["server"]["simulation_path"]
            )

        # make sure that the target folder exists
        for folder in reversed(DATA_CONFIG["server"]["simulation_path"].parents):
            self.ssh_client.exec_command("mkdir -p " + str(folder))
        self.ssh_client.exec_command("mkdir -p " + str(DATA_CONFIG["server"]["simulation_path"]))

    def close_ssh_client(self):
        """Closes the ssh connection again."""
        self.ssh_client.close()

        self.ssh_client = None
        self.scp_client = None

    def copy_zip_to_server(self, sims_to_zip):
        """Copies the simulation data to the server. Before doing this, old simulation data is deleted

        Parameters
        ----------
        sims_to_zip : list[dict]
            A list of dictionaries with 2 keys:
            dut : DutView
            sweep : Sweep
        """

        def add_to_zip(folder, rel_to):
            # add folder (not really needed, if there is any file in the folder, but we don't know this....)
            zip_ref.write(folder, arcname=folder.relative_to(rel_to))
            # add all data inside folder
            for child in folder.iterdir():
                if child.is_file():
                    zip_ref.write(child, arcname=child.relative_to(rel_to))
                else:
                    add_to_zip(child, rel_to)

        assert self.ssh_client is not None
        assert self.scp_client is not None

        sim_path_on_server = DATA_CONFIG["server"]["simulation_path"]
        commands = []
        # delete possible old directories:
        for sim_to_zip in sims_to_zip:
            sim_folder = sim_to_zip["dut"].get_sim_folder(sim_to_zip["sweep"])
            dut_folder = sim_folder.parts[-2]
            sweep_folder = sim_folder.parts[-1]
            commands.append("rm -rf " + str(sim_path_on_server / dut_folder / sweep_folder))

        for command in commands:
            self.ssh_client.exec_command(command)

        with NamedTemporaryFile() as path_zip:  # dut.get_sim_folder(sweep).relative_to(dut.sim_dir)
            with ZipFile(path_zip, "w") as zip_ref:
                for sim_to_zip in sims_to_zip:
                    add_to_zip(
                        sim_to_zip["dut"].get_sim_folder(sim_to_zip["sweep"]),
                        sim_to_zip["dut"].sim_dir,
                    )
                    # add "central" VA-Files -.-
                    if not sim_to_zip["dut"]._copy_va_files:
                        va_files_dir = sim_to_zip["dut"].sim_dir / "VA_codes"
                        for vafile in sim_to_zip["dut"]._list_va_file_contents:
                            dir_code = va_files_dir / vafile.get_tree_hash()
                            add_to_zip(
                                dir_code,
                                sim_to_zip["dut"].sim_dir,
                            )

            # transfer and save name
            self.scp_client.put(path_zip.name, remote_path=str(sim_path_on_server))
            name_zip_file = Path(path_zip.name).name

        # unzip
        # here we should wait for finish
        _stdin, stdout, _stderr = self.ssh_client.exec_command(
            "unzip -o -d " + str(sim_path_on_server) + " " + str(sim_path_on_server / name_zip_file)
        )
        stdout.channel.set_combine_stderr(True)
        output = stdout.readlines()

        # delete temp zip on the server
        self.ssh_client.exec_command("rm -f " + str(sim_path_on_server / name_zip_file))

    def copy_from_server(self, dut, sweep, zip_result=True):
        """Collects the simulation data from the server.

        Parameters
        ----------
        dut : DutView
        sweep : Sweep
        zip_result : bool, optional
            If True, the result is zipped before transfer, the zip is copied and then unzipped locally.
        """
        sim_folder = dut.get_sim_folder(sweep)
        root = sim_folder.parent
        sweep_folder = sim_folder.parts[-1]
        dut_folder = sim_folder.parts[-2]
        if zip_result:
            # delete possible old zip:
            self.ssh_client.exec_command(
                "rm -f {0:s}.zip".format(
                    str(DATA_CONFIG["server"]["simulation_path"] / dut_folder / sweep_folder)
                )
            )  # remove to be sure

            # create new zip and copy it via scp
            channel_zip = self.ssh_client.get_transport().open_session(timeout=self.t_max)
            channel_zip.exec_command(
                "cd {0:s} && zip -r {1:s}.zip ./{1:s}".format(
                    str(DATA_CONFIG["server"]["simulation_path"] / dut_folder), sweep_folder
                )
            )
            while not channel_zip.exit_status_ready():
                time.sleep(0.5)

            try:
                self.scp_client.get(
                    str(DATA_CONFIG["server"]["simulation_path"] / dut_folder / sweep_folder)
                    + ".zip",
                    local_path=str(root),
                )
            except (SCPException, paramiko.SSHException, TimeoutError) as err:
                raise FileNotFoundError from err

            path_zip = sim_folder.with_suffix(".zip")
            with ZipFile(path_zip, "r") as zip_ref:
                zip_ref.extractall(root)

            path_zip.unlink()
        else:
            try:
                self.scp_client.get(
                    str(DATA_CONFIG["server"]["simulation_path"] / dut_folder / sweep_folder),
                    local_path=str(root),
                    recursive=True,
                )
            except (SCPException, paramiko.SSHException) as err:
                # reraise it in order to allow run_and_read to go on and try again in 2 seconds
                raise FileNotFoundError from err

    def copy_log_from_server(self, dut, sweep):
        """Collects the simulation log file from the server.

        Parameters
        ----------
        dut : DutView
        sweep : Sweep
        """
        sim_folder = dut.get_sim_folder(sweep)
        root = sim_folder.parent
        sweep_folder = sim_folder.parts[-1]
        dut_folder = sim_folder.parts[-2]
        try:
            self.scp_client.get(
                str(
                    DATA_CONFIG["server"]["simulation_path"] / dut_folder / sweep_folder / "sim.log"
                ),
                local_path=str(root / sweep_folder),
                recursive=True,
            )
        except (SCPException, paramiko.SSHException) as err:
            # reraise it in order to allow run_and_read to go on and try again in 2 seconds
            raise FileNotFoundError from err

    def run_simulations(self, sim_list):
        """Runs all given simulations in parallel.

        Parameters
        ----------
        sim_list :  [{}]
            List of dictionaries, each dictionary has a 'dut': :class:`~DMT.core.DutView` and 'sweep': :class:`~DMT.core.Sweep` key value pair.

        Returns
        -------
        success  :  list[process]
            List of finished processes
        """
        if len(sim_list) == 0:
            return []

        # test if same simulation is added twice.
        set_dut_hashes = set([sim_i["dut"].get_hash() for sim_i in sim_list])

        list_to_delete = []
        for dut_hash in set_dut_hashes:
            list_sweep_hashes = []
            for i_sim, sim_a in enumerate(sim_list):
                if sim_a["dut"].get_hash() == dut_hash:
                    if sim_a["sweep"].get_hash() in list_sweep_hashes:
                        list_to_delete.append(i_sim)
                    else:
                        list_sweep_hashes.append(sim_a["sweep"].get_hash())

        for to_delete in sorted(list_to_delete, reverse=True):
            del sim_list[to_delete]

        # start simulations
        process_running = []
        process_finished = []
        finished = False
        n = 0
        n_total = len(sim_list)

        # prepare simulations
        print_progress_bar(0, len(sim_list), prefix="Preparing Simulations", length=50)
        sims_to_zip = []

        # if True: use pbs job scheduler
        pbs = DATA_CONFIG["server"]["use_pbs"] and DATA_CONFIG["backend_remote"]
        if DATA_CONFIG["progress_minimal"]:
            len_output = 2
        else:
            len_output = self.n_core + 7

        for i_sim, sim in enumerate(sim_list):
            sweep = sim["sweep"]
            dut = sim["dut"]
            print_progress_bar(i_sim, len(sim_list), prefix="Preparing Simulations", length=50)
            dut.prepare_simulation(sweep)
            if dut.simulate_on_server:
                sims_to_zip.append({"dut": dut, "sweep": sweep})

        print_progress_bar(len(sim_list), len(sim_list), prefix="Preparing Simulations", length=50)
        print("\n")  # new line after the progress bar

        if sims_to_zip:
            print("Uploading simulation input files and folders to server...")
            self.copy_zip_to_server(sims_to_zip)
            print("finish uploading.")

        # do not print download status
        if self.scp_client is not None:
            self.scp_client._progress = False

        with output(output_type="list", initial_len=len_output, interval=0) as output_list:
            while not finished:
                # run infinite processes parallel on the server
                # if (len([process for process in process_running if not process['backend_remote']]) < self.n_core) and (len(sim_list) > 0 ):
                if (len([process for process in process_running]) < self.n_core) and (
                    len(sim_list) > 0
                ):
                    # take the next element from the self.sim_list and start it
                    sim = sim_list[0]
                    sim_list = sim_list[1:]
                    # start the simulation on this core
                    sweep = sim["sweep"]
                    dut = sim["dut"]
                    if (
                        not hasattr(dut, "t_max") or dut.t_max is None
                    ):  # make sure t_max is set in every simulated dut
                        dut.t_max = self.t_max

                    if dut.simulate_on_server:
                        pid = self.run_simulation_remote(dut, sweep, pbs=pbs)
                        process = 0

                    else:
                        process = self.run_simulation_local(dut, sweep)
                        pid = process.pid

                    if pid == 0:
                        continue  # failed to start simulation, just wait and try again

                    if hasattr(dut, "zip_result"):
                        zip_result = dut.zip_result
                    else:
                        zip_result = True  # per default True, it is better because scp struggles with many files...

                    n += 1
                    t0 = time.time()
                    process_running.append(
                        {
                            "n": n,
                            "t0": t0,
                            "dt": t0,
                            "dut": dut,
                            "sweep": sweep,
                            "process": process,
                            "pid": pid,
                            "success": True,
                            "backend_remote": dut.simulate_on_server,
                            "last_poll": 0,
                            "zip_result": zip_result,
                        }
                    )

                # check for finished processes. DO THIS BEFORE TIMEOUT CHECKING.
                for p in process_running:
                    process = p["process"]
                    if p["backend_remote"]:
                        p["last_poll"] += 1
                        if (
                            p["last_poll"] % 5 == 0
                        ):  # every 20th round -> every 2 seconds (is this too much?)
                            if pbs:
                                # use qstat
                                _stdin, stdout, _stderr = self.ssh_client.exec_command(
                                    ("qstat_script " + str(p["pid"]))
                                )
                                out = str(stdout.read())
                                if (
                                    "Unknown Job" in out or out == "b''"
                                ):  # if job finished, these strings are returned
                                    try:
                                        self.copy_from_server(
                                            p["dut"], p["sweep"], zip_result=p["zip_result"]
                                        )
                                        process_finished.append(p)
                                        try:
                                            p["dut"].validate_simulation_successful(p["sweep"])
                                        except (
                                            SimulationFail,
                                            SimulationUnsuccessful,
                                            FileNotFoundError,
                                        ):
                                            p["success"] = False
                                    except (SimulationUnsuccessful, FileNotFoundError):
                                        pass  # just try again

                            else:  # copy everything and check => slow
                                try:
                                    self.copy_log_from_server(p["dut"], p["sweep"])
                                    p["dut"].validate_simulation_successful(p["sweep"])
                                    self.copy_from_server(
                                        p["dut"], p["sweep"], zip_result=p["zip_result"]
                                    )
                                    process_finished.append(p)
                                except (SimulationUnsuccessful, FileNotFoundError):
                                    pass
                                except SimulationFail:
                                    p["success"] = False
                                    process_finished.append(p)

                    else:
                        returncode = process.poll()
                        if returncode is not None:
                            if (
                                returncode != 0
                                and returncode != 134
                                and returncode != 139
                                and returncode != 1
                            ):  # 134 sometimes happens but still ads works...
                                p["success"] = False

                            process_finished.append(p)

                # check for timeouts
                t = time.time()
                for p in process_running:
                    p["dt"] = t - p["t0"]
                    if (p["dt"] > p["dut"].t_max) and (
                        p["dt"] > self.t_max
                    ):  # both t_max have to be smaller than the simulation time
                        if not p["backend_remote"]:
                            p["process"].kill()
                        # TODO: kill with pbs
                        p["success"] = False
                        process_finished.append(p)

                # remove finished processes from running processes
                for p in process_finished:
                    if p in process_running:
                        process_running.remove(p)

                # update status that is displayed on the console
                len_progress = 20  # number of #
                progress = int(
                    len(process_finished)
                    / (len(sim_list) + len(process_running) + len(process_finished))
                    * len_progress
                )
                output_list[0] = "DMT is now simulating!         "
                output_list[1] = (
                    "finished: "
                    + str(len(process_finished))
                    + " of "
                    + str(n_total)
                    + ":["
                    + "#" * progress
                    + " " * (len_progress - progress)
                    + "]"
                )

                if not DATA_CONFIG["progress_minimal"]:
                    output_list[2] = "-------------------------------"
                    output_list[3] = "| sim_n | pid        | dt     |"
                    output_list[4] = "-------------------------------"
                    for i in range(self.n_core):
                        try:
                            p = process_running[i]
                            str_ = "|{:^7d}|{:^12d}|{:^8.1f}|".format(p["n"], p["pid"], p["dt"])
                        except (KeyError, IndexError):
                            str_ = "|{:^7s}|{:^12s}|{:^8.1f}|".format("x", "x", 0)

                        output_list[i + 5] = str_

                    output_list[-2] = "-------------------------------"
                    output_list[-1] = "                               "

                # are we finished?
                if len(process_running) == 0 and len(sim_list) == 0:
                    finished = True
                elif len(process_running) == self.n_core or len(sim_list) == 0:
                    time.sleep(0.1)

        # print download status
        if self.scp_client is not None:
            self.scp_client._progress = True

        return process_finished

    def run_simulation_local(self, dut, sweep):
        """Starts the simulation

        Parameters
        ----------
        dut : DutView
        sweep : Sweep
        """
        sim_folder = dut.get_sim_folder(sweep)
        logging.info(
            "Started the simulation for the dut %s of the sweep %s!", dut.get_hash(), sweep.name
        )
        logging.debug("The simulation folder of this simulation is %s", sim_folder)
        log_file = open(sim_folder / "sim.log", "w")
        log_file.write(f"The simulation command is\n{dut.get_start_sim_command()}\n\n")
        return subprocess.Popen(
            dut.get_start_sim_command().split(),
            shell=False,
            cwd=sim_folder,
            stderr=subprocess.STDOUT,
            stdout=log_file,
        )

    def run_simulation_remote(self, dut, sweep, pbs=False):
        """Starts the remote simulation

        Parameters
        ----------
        dut : DutView
        sweep : Sweep
        pbs : Boolean

        Returns
        -------
        pid : int
            0 if failed, -1 if running via ssh directly and id of job for PBS simulation.
        """
        sim_folder = dut.get_sim_folder(sweep)
        sweep_folder = sim_folder.parts[-1]
        dut_folder = sim_folder.parts[-2]

        logging.info(
            "Started the remote simulation for the dut %s of the sweep %s!",
            dut.get_hash(),
            sweep.name,
        )
        logging.debug("The simulation folder of this simulation is %s", sim_folder)

        # start a subprocess with the ssh command
        if not pbs:
            _stdin, _stdout, _stderr = self.ssh_client.exec_command(
                (
                    "cd "
                    + str(DATA_CONFIG["server"]["simulation_path"] / dut_folder / sweep_folder)
                    + ";"
                    + dut.get_start_sim_command()
                    + " > sim.log &"
                )
            )
            return -1
        else:
            _stdin, stdout, _stderr = self.ssh_client.exec_command(
                (
                    "cd "
                    + str(DATA_CONFIG["server"]["simulation_path"] / dut_folder / sweep_folder)
                    + ";"
                    + DATA_CONFIG["server"]["command_qsub"]
                )
            )
            output = stdout.read()
            _error = _stderr.read()
            id_ = "".join([n for n in str(output).split(".")[0] if n.isdigit()])
            try:
                return int(id_)
            except ValueError:
                return 0


def _check_simulation_needed(i_sim, n_tot, dut=None, sweep=None):
    """Function to check if the simulation is needed or already present in the database

    Parameter
    -----------
    dut : DMT.core.DutView
    sweep : DMT.core.Sweep

    Returns
    -------
    {key: DMT.core.Dataframe}
        In case the data is read from database or previous simulation.
    None
        In case the simulation must be done.
    """
    dut_name = dut.name + str(dut.get_hash())
    sim_name = sweep.name + "_" + sweep.get_hash()
    # print("Check: dut: {:s}, sweep: {:s}".format(dut_name, sim_name))
    print_progress_bar(i_sim, n_tot, prefix="Progress", length=50)
    if dut.check_existence_sweep(sweep):
        logging.info("Simulation of DuT %s with sweep %s loaded from database.", dut_name, sim_name)
    else:
        # if not in dut.data and not in dut.db
        try:
            # was it simulated already successfully ?
            dut.validate_simulation_successful(sweep)
            logging.info(
                "Simulation of DuT %s with sweep %s already done and results are valid, only data needs to be read.",
                dut_name,
                sim_name,
            )
            logging.debug(
                "The simulation folder of this simulation was %s", dut.get_sim_folder(sweep)
            )
            dut.add_data(sweep)
        except SimulationFail:
            print("Simulation of DuT %s with sweep %s already done and failed!", dut_name, sim_name)
        # except (SimulationUnsuccessful, FileNotFoundError, IndexError, struct.error):
        except:  # all exceptions should be re-simulated
            # ok simulate it!
            dut.delete_sim_results(sweep, ignore_errors=True)  # remove for safety
            logging.info("Simulation of DuT %s with sweep %s needed.", dut_name, sim_name)
            return None

    return dut.data


def _read_process_results(success, dut, sweep):
    """Read the process results

    Parameter
    -----------
    success : bool
    dut : DMT.core.DutView
    sweep : DMT.core.Sweep

    Returns
    -------
    {'success': success, 'dut_hash':dut.get_hash(), 'data':dut.data}
    """
    dut_name = dut.name + str(dut.get_hash())
    sim_name = sweep.name + "_" + sweep.get_hash()
    sim_folder = dut.get_sim_folder(sweep)
    print("Read: dut: {:s}, sweep: {:s}".format(dut_name, sim_name))
    # inform data_manager about the finished simulations
    try:
        if success:
            dut.add_data(sweep)
            logging.info("Simulation of DuT %s with sweep %s successfull.", dut_name, sim_name)
        else:
            color_red = "\033[91m"
            color_end = "\033[0m"
            print(
                "{0:s}Simulation of DuT {1:s} with sweep {2:s} failed.{3:s}".format(
                    color_red, dut_name, sim_name, color_end
                )
            )
            print(
                "{0:s}Simulation folder: {1:s} {2:s}".format(color_red, str(sim_folder), color_end)
            )
            print((sim_folder / "sim.log").read_text())
            logging.info("Simulation of DuT %s with sweep %s failed.", dut_name, sim_name)
    except (SimulationUnsuccessful, FileNotFoundError, KeyError):
        color_red = "\033[91m"
        color_end = "\033[0m"
        print(
            "{0:s}Simulation of DuT {1:s} with sweep {2:s} failed.{3:s}".format(
                color_red, dut_name, sim_name, color_end
            )
        )
        print("{0:s}Simulation folder: {1:s} {2:s}".format(color_red, str(sim_folder), color_end))
        print((sim_folder / "sim.log").read_text())
        logging.info("Simulation of DuT %s with sweep %s failed.", dut_name, sim_name)

    return {"success": success, "dut_hash": dut.get_hash(), "data": dut.data}
