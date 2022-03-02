""" Manage measurement data in DMT in as a measurement dut. Additionally has attributes which define the size and die of the dut.

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

import logging
import re
from DMT.core import print_progress_bar
from DMT.core.dut_view import DutView


class DutMeas(DutView):
    """Subclass of DutView that is used to capture relevant methods and properties of measured data.

    Parameters
    ----------
    database_dir         :  string
        Root directory for saving duts and databases of this project.
    name           :  string
        Name of the dut to save it human readable.
    dut_type       : :class:`~DMT.core.dut_type.DutType`
    width          :  float64, optional
        Width in m.
    length         :  float64, optional
        Length in m.
    wafer          :  string, optional
        Wafer identification string of this object.
    die            :  string, optional
        Die identification string of this object.
    ndevices       :  integer
        Number of physically parallel devices of this measurement.
    hash           :  float64
        Unique hash of this object.

    Attributes
    ----------
    width          :  float64
        Width in m.
    length         :  float64
        Length in m.
    perimeter      :  float64
        Perimeter in m.
    area           :  float64
        Area of this DutMeas object in m^2.
    wafer          :  string
        Wafer identification string of this object.
    die            :  string
        Die identification string of this object.
    ndevices       :  integer
        Number of physically parallel devices of this measurement.

    Methods
    -------
    run_simulation(sweep)
        Return a NotImplemented exception. Measurements can not be simulated!
    get_hash()
        Return a unique hash based on some attributes of the DutMeas object.
    add_short(short, key='/dummies/short', force=True)
        Add a short dummy to the database of this DutMeas object.
    add_open(short, key='/dummies/short', force=True)
        Add an open dummy to the database of this DutMeas object.
    deembed(filter_func, short_key='/dummies/short', open_key='/dummies/open')
        Deembed some dataframes of this DutMeas object using a user supplied filter function.
    clean_data()
        Clean the dataframe columns of the DataFrame objects in this DutMeas objects database.
    get_output_data(sweep)
        Raises NotImplementedError since a measurement can not return its output files.

    """

    def __init__(
        self,
        database_dir,
        name,
        dut_type,
        force=False,
        wafer=None,
        die=None,
        ndevices=1,
        deemb_name=None,
        **kwargs,
    ):
        super().__init__(database_dir, name, dut_type, nodes=None, force=force, **kwargs)
        self.wafer = wafer
        self.die = die
        self.ndevices = ndevices

        if deemb_name is None:
            self.deemb_name = self.name
        else:
            self.deemb_name = deemb_name

        if self.width is not None:
            try:
                self.perimeter = (self.width + self.length) * 2
                self.area = self.width * self.length
            except TypeError:
                pass  # if either spacer is None or width or length are tuples.

    def run_simulation(self, sweep):
        """Raise a OSError. Measurements can not be simulated!

        Raises
        ------
        OSError
            Always when called.
        """
        raise OSError("DutMeas: Measured data can not be simulated!")

    def prepare_simulation(self, sweep):
        """Raise a OSError. Measurement duts can not be simulated!

        Raises
        ------
        OSError
            Always when called.
        """
        raise OSError("DutMeas: Measured data can not be simulated!")

    def make_input(self, sweep):
        """Should genrate the input file for a given simulation sweep. This is not possible for measurements!

        Raises
        ------
        OSError
            Always when called.
        """
        raise OSError("DutMeas: Measured data can not be simulated!")

    def get_hash(self):
        """Empty string, so it is evaluated to false, but still a string.

        Returns
        -------
        ''
        """
        return ""

    def __format__(self, key):
        if key == "":
            return f"DutMeas:\n\tname: {self.name}\n\ttype: {self.dut_type}\n\tcontact_config: {self.contact_config}\n\twidth: {self.width}\n\tlength: {self.length}\n\tndev: {self.ndevices}"
        elif key == "long":
            return f"DutMeas:\n\tname: {self.name}\n\ttype: {self.dut_type}\n\tcontact_config: {self.contact_config}\n\twidth: {self.width}\n\tlength: {self.length}\n\tndev: {self.ndevices}\n\t data: {[key for key in self.data.keys]}"
        else:
            raise ValueError(f"Unkown format {key}")

    def add_short(self, short, key=r"dummies/short"):
        """Add a short dummy to the database of this DutMeas object.

        Parameters
        ----------
        short  :  string or DMT.DataFrame or pd.DataFrame
            The File or DataFrame with the short small signal parameters as a function of frequency.

        key    :  string
            Key that will be used to save the short dummy in the database. Default='/dummies/short'

        """

        self.add_data(short, key, force=True)
        logging.info("DMT -> DutMeas -> add_short(): Added a short to the DUT")

    def add_open(self, open_, key=r"dummies/open"):
        """Add an open dummy to the database of this DutMeas object.

        Parameters
        ----------
        open_  :  string or DMT.DataFrame or pd.DataFrame
            The File or DataFrame with the short small signal parameters as a function of frequency.

        key    :  string
            Key that will be used to save the short dummy in the database. Default='/dummies/short'

        """
        self.add_data(open_, key, force=True)
        logging.info("DMT -> DutMeas -> add_open(): Added an open to the DUT")

    def deembed(self, filter_func, short_key="dummies/short", open_key="dummies/open"):
        """Deembed some dataframes of this DutMeas object using a user supplied filter function.

        Parameters
        ----------
        filter_func  :  callable object
            This used supplied callable object, e.g. function, is called with each key in the DutView's database.
            If True is returned, the dataframe corresponding to key is deembedded.
        short_key    :  string
            Default='/dummies/short'. Key that corresponds to the short dummy in the database.
        open_key     :  string
            Default='/dummies/open'. Key that corresponds to the open dummy in the database.

        Returns
        -------
        self  :  DutMeas
            The updated DutMeas object.

        Notes
        -----
        todo: Delete this method since this functionality will be taken over by DutLib!
        """
        raise IOError("Obsolete")

        # retrieve the short and open dummies
        no_dummies = False
        try:
            df_short = self.data[short_key]
            df_open = self.data[open_key]
        except:
            no_dummies = True

        # find keys of dataframes that need to be deembedded
        keys = [key for key in self.data.keys() if filter_func(key)]

        if len(keys) > 0 and no_dummies:
            raise IOError(
                "DMT -> DutMeas -> deembed: Found keys that require deembedding, however no short or open dummies are present in this Dut."
            )

        if len(keys) == 0:  # some DUTs are only DC
            return self

        # go through each DataFrame where the function filter returns true and deembed()
        i = 0
        n_frames = len(self.data)
        print_progress_bar(i, n_frames, prefix="Deembedding:", suffix="Complete\n", length=50)
        for key in self.data.keys():
            if filter_func(key):
                i = i + 1
                df = self.data[key]
                self.data[key] = df.deembed(df_open, df_short, ports=self.nodes)
                logging.info("DMT -> DutMeas -> deembed(): Deembedded dataframe with key %s.", key)
                print_progress_bar(
                    i, n_frames, prefix="Deembedding:", suffix="Complete\n", length=50
                )

        if (
            self.ndevices > 1
        ):  # if we have more than one device in parallel, normalize the currents to the area of one device
            for key in self.data.keys():
                df = self.data[key]
                self.data[key] = df.parallel_norm(self.ndevices)

        return self

    def get_output_data(self, sweep):
        raise NotImplementedError(
            "DMT -> DutMeas -> get_output_data(): DutMeas does not implement this method on purpose!"
        )

    def join_key_temperature(self, *key_parts, temperature_converter=None):
        """Collects the temperature from key_parts and replaces it by a proper temperature key part.

        Parameters
        ----------
        key_parts : [str]
            List of key strings to join. One element contains the temperature information.
        temperature_converter : callable object, optional
            Function to convert a key part into a temperature.

        Returns
        -------
        key : str
            The correctly joined key_parts. If the temperature was inside, it is converted into "T" + temp + "K".

        """

        if temperature_converter is None:
            temperature_converter = self.temp_converter_default

        key_parts = list(key_parts)
        for i_key_part, key_part in enumerate(key_parts):
            temp = temperature_converter(key_part)
            if temp == -1:  # this value is returned it the temperature is not in the key.
                continue
            if temp < 0:
                raise ValueError(
                    "Got a negative temperature for the key. This is nonphysical since the temperature must be in Kelvin!"
                )
            elif temp < 50:
                warning = (
                    "DutMeas -> join_key_temperature: The temperature of a measurement is below 50K. The given measurement is "
                    + self.join_key(*key_parts)
                    + " of the DuT "
                    + self.name
                    + "."
                )
                logging.warning(warning)
                print(warning)

            key_parts[i_key_part] = "T{:.2f}K".format(temp)

        return self.join_key(*key_parts)

    def temp_converter_default(self, key_part):
        """Default converter from key_part to temperature. Asumes the temperature in the key parts is in Kelvin.

        Parameters
        ----------
        key_part : str
            Key to inspect

        Returns
        -------
        temp : float or None
            If key does not contain a temperature, -1 is returned.
            If id does contain a temperature, the temperature in Kelvin is returned.
        """
        temp = None
        re_temp = re.search(r"T([0-9p\.]+)K", key_part)
        if re_temp:
            try:
                # always replace "p" with ".", if it is already with ".", it doesn't matter
                temp = round(float(re_temp.group(1).replace("p", ".")), 3)
            except ValueError:
                # if a value error in the except clause happens, try the next key part.
                pass

        # alternative:
        if key_part.startswith("T"):
            try:
                temp = round(float(key_part[1:].replace("p", ".")), 3)
            except ValueError:
                # if a value error in the except clause happens, try the next key part.
                pass

        # finally as a last escape: direct conversion :(
        try:
            temp = round(float(key_part.replace("p", ".")), 3)
        except ValueError:
            # if a value error in the except clause happens, try the next key part.
            pass

        if temp is None:
            return -1
        else:
            return temp
