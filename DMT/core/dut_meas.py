"""Manage measurement data in DMT in as a measurement dut. Additionally has attributes which define the size and die of the dut."""

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
import re
from typing import List, Dict, Type
from DMT.core import Technology
from DMT.core.dut_view import DutView


try:
    from semver.version import Version as VersionInfo
except ImportError:
    from semver import VersionInfo

SEMVER_DUTMEAS_CURRENT = VersionInfo(major=1, minor=0)


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
        Raises NotImplementedError since measurements can not be simulated!
    get_hash()
        Return a unique hash based on some attributes of the DutMeas object.
    add_short(short, key='/dummies/short', force=True)
        Add a short dummy to the database of this DutMeas object.
    add_open(short, key='/dummies/short', force=True)
        Add an open dummy to the database of this DutMeas object.
    get_output_data(sweep)
        Raises NotImplementedError since a measurement can not return its output files.
    """

    def __init__(
        self,
        database_dir,
        name,
        dut_type,
        wafer=None,
        die=None,
        ndevices=1,
        deemb_name=None,
        **kwargs,
    ):
        super().__init__(database_dir, name, dut_type, **kwargs)
        self.wafer = wafer
        self.die = die
        self.ndevices = ndevices

        if deemb_name is None:
            self.deemb_name = self.name
        else:
            self.deemb_name = deemb_name

    def info_json(self, **_kwargs) -> Dict:
        """Returns a dict with serializeable content for the json file to create.

        The topmost dict MUST have only one key: The string casted class name.
        Inside the parameters are:

            * A version key,
            * all extra parameters of DutMeas compared to DutView and
            * the info_json of DutView.

        Returns
        -------
        dict
            str(DutMeas): serialized content
        """
        return {
            str(DutMeas): {
                "__DutMeas__": str(SEMVER_DUTMEAS_CURRENT),
                "parent": super(DutMeas, self).info_json(**_kwargs),
                "wafer": self.wafer,
                "die": self.die,
                "ndevices": self.ndevices,
                "deemb_name": self.deemb_name,
            }
        }

    @classmethod
    def from_json(cls, json_content: Dict, classes_technology: List[Type[Technology]]) -> "DutMeas":
        """Static class method. Loads a DutMeas object from a pickle file with full path save_dir.

        Calls the from_json method of DutView with all dictionary inside the "parent" keyword. Afterwards the additional parameters are set correctly.

        Parameters
        ----------
        json_content  :  dict
            Readed dictionary from a saved json DutMeas.
        classes_technology : List[Type[Technology]]
            All possible technologies this loaded DutMeas can have. One will be choosen according to the serialized technology loaded from the file.

        Returns
        -------
        DutMeas
            Loaded object.
        """
        if json_content["__DutMeas__"] != SEMVER_DUTMEAS_CURRENT:
            raise NotImplementedError("DMT.DutMeas: Unknown version of DutMeas to load!")

        dut_view = super().from_json(json_content["parent"], classes_technology)

        dut_view.wafer = json_content["wafer"]
        dut_view.die = json_content["die"]
        dut_view.ndevices = json_content["ndevices"]
        dut_view.deemb_name = json_content["deemb_name"]

        return dut_view

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
            if isinstance(temp, str):
                # escape to directly manipulate the key
                key_parts[i_key_part] = temp
                continue
            elif temp == -1:  # this value is returned it the temperature is not in the key.
                continue
            elif temp < 0:
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
