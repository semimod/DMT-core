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
import numpy as np
import pandas as pd
from DMT.core import DutView


class DutDummy(DutView):
    """DutDummy is a dummy subclass of DutView that can be used for testing other modules of DMT. It implements some basic functionality that mimics an actual DutView.

    Methods
    -------
    run_simulation()
        run the simulation for this DutView object using a specified sweep on a specified core.

    Attributes
    ----------
    database_dir   :  string
        Path to the DUT's database.

    name     :  string
        Name of the DUT's database.

    type     :  string
        type of the DUT according to the Dut_type class.

    nodes     : [string]
        List of strings that contain the node names of DUT. Default is none. If nodes is None, nodes will be requested from Dut_type class.
    """

    def __init__(self, database_dir, name, dut_type, modelcard, **kwargs):
        """Initialization routine.

        Parameters
        ----------
        database_dir    : string
            This is the directory were the DUT will create its database.
        name      : string
            This is the name that will be assigned to the DUT.
        dut_type  : Dut_type()
            Type of the DUT.
        nodes     : [string]
            List of strings that contain the node names of DUT. Default is none. If nodes is None, nodes will be requested from Dut_type class.
        """
        self.modelcard = modelcard
        super().__init__(database_dir, name, dut_type, **kwargs)
        self.inp_name = "dummy_input.inp"

    def get_start_sim_command(self):
        return "sleep 1"

    def get_hash(self):
        """Return a hash for the DutView's input file.

        Returns
        -------
        hash : float64
            Hash that corresponds to this DUT.
        """
        mcf = self.modelcard.get("mcf")
        mcf = mcf.value
        return str(mcf)

    # def prepare_simulation(self, sweep):
    #    """ Prepare a dummy simulation.
    #    """
    #    pass

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
        mcf = self.modelcard.get("mcf").value
        data = {}
        df_sweep = sweep.create_df()
        data["V_B"] = df_sweep["V_B"].to_numpy()
        data["I_C"] = np.exp(data["V_B"] / (mcf * 25e-3))
        df = pd.DataFrame(data=data)
        self.manager.save_df(df, self.database_dir / "iv.p")
        return df

    def make_input(self, sweep):
        """Joins simulation header and with a given sweep and returns it!

        Parameters
        ----------
        sweep : :class:`DMT.core.sweep.Sweep`
            Sweep specification according to the Sweep class.
        """
        # self.sweep = sweep
        return "dummy inp"

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
        pass
