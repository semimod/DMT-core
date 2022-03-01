# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-device>
#
# This file is part of DMT.
#
# DMT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DMT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import os
import _pickle as cpickle
import shutil
import copy
import re
import filecmp
import numpy as np
from scipy import interpolate
from pathlib import Path
from joblib import Parallel, delayed
from DMT.core import (
    DutType,
    print_progress_bar,
    specifiers,
    sub_specifiers,
    specifiers_ss_para,
    DATA_CONFIG,
    DutView,
)
from DMT.exceptions import NoOpenDeembeddingDut, NoShortDeembeddingDut
from DMT.core.plot import MIX, PLOT_STYLES, natural_scales, Plot
from DMT.external.os import recursive_copy

try:
    from DMT.external.pylatex import SubFile, Tex
    from pylatex import Section, Subsection, SmallText, Tabular, NoEscape, Center, Figure
except ImportError:
    pass


class __Filter(object):
    """Superclass for all implemented filters. Is used to compare specified properties of devices and deembedding structures.

    Parameters
    ----------
    devProp     : 'str'
        Property of the device that is to be compared to that of the deembedding structure.
    testProp    : 'str'
        Property of the deembedding structure that is to be compared to that of the device.


    Methods
    -------
    filter(dev, testStructure)
        Compare the specified property of a device to the corresponding one of the teststructure.

    """

    def __init__(self, devProp, testProp=None):
        if testProp is None:
            self.testProp = devProp
        else:
            self.testProp = testProp
        self.devProp = devProp

    def filter(self, dev, testStructure):
        """Compares the device and teststructure with regards to the specified property and returns 'True' if they match.

        Parameters
        ----------
        dev             : [DutMeas]
            Object of a DutMeas class. TODO: Should I make that DutView? So it can also be used for sims?
        testStructure   : [DutMeas]
            Object of DutMeas class with the dut_type 'open' or 'short'.
        """
        try:
            propTest = getattr(testStructure, self.testProp)
            propDev = getattr(dev, self.devProp)
        except AttributeError as err:
            raise IOError(
                "DMT -> DutLib -> Filter: the property " + self.devProp + " is not existent."
            ) from err

        if isinstance(propDev, str):
            if propDev == propTest:
                # if propDev in propTest or propTest in propDev:
                return True
            else:
                return False
        else:
            if np.isclose(propDev, propTest, 1e-8, 1e-8):
                return True
            else:
                return False


class LenFilter(__Filter):
    """Subclass of __Filter, that compares the device's and the testStructure's emitter length."""

    def __init__(self):
        super().__init__("length")


class WidthFilter(__Filter):
    """Subclass of __Filter, that compares the device's and the testStructure's emitter width."""

    def __init__(self):
        super().__init__("width")


class NameFilter(__Filter):
    """Subclass of __Filter, that compares the device's and the testStructure's name (contact configuration)."""

    def __init__(self):
        super().__init__("deemb_name")  # , testProp = "deemb_name")


class LenNameFilter:
    """Class that combines the typically used filters for emitter length and device name."""

    def __init__(self):
        self.nameFilter = NameFilter()
        self.lenFilter = LenFilter()

    def filter(self, dev, testStructure):
        return self.nameFilter.filter(dev, testStructure) & self.lenFilter.filter(
            dev, testStructure
        )


class DutLib(object):
    """DutLib is a class managing a library in which measured DUTs in DMT are contained.

    Class is able to match any device type with its corresponding deembedding dummies and perform the deembedding process.

    Parameters
    ----------
    deem_types      : [:class:`~DMT.core.dut_type.DutType`], optional
        A list of dut_types, that are used to filter the incoming list of duts for those devices that need deembedding.
    AC_filter_names    : [tuple], optional
        List of filter tuples that are used to determine the deembedding file corresponding to one measurement file. (e.g.: [('freq', 'hot'),('Spar', 'cold')],...)
    DC_filter_names    : [tuple], optional
        List of filter tuples that are used to determine the deembedding file corresponding to one measurement file. (e.g.: [('freq', 'hot'),('Spar', 'cold')],...)
    is_deembedded_AC   : bool, optional
        If true, all devices in the library have been AC deembedded.
    is_deembedded_DC   : bool, optional
        If true, all devices in the library have been DC deembedded.
    save_dir        : str, optional
        Here the DutLib will try to save itself
    force           : bool, optional
        If True, a already existing library will be deleted.
    n_jobs          : int, optional
        Number of parallel jobs, passed on to joblib.Parallel.

    Attributes
    ----------
    deem_types      : [:class:`~DMT.core.dut_type.DutType`]
        A list of dut_types, that are used to filter the incoming list of duts for those devices that need deembedding.
    AC_filter_names    : [tuple]
        List of filter tuples that are used to determine the deembedding file corresponding to one measurement file. (e.g.: [('freq', 'hot'),('Spar', 'cold')],...)
    DC_filter_names    : [tuple]
        List of filter tuples that are used to determine the deembedding file corresponding to one measurement file. (e.g.: [('freq', 'hot'),('Spar', 'cold')],...)
    is_deembedded_AC   : bool
        If true, all devices in the library have been AC deembedded.
    is_deembedded_DC   : bool
        If true, all devices in the library have been DC deembedded.
    duts            : [:class:`~DMT.core.dut_view.DutView`]
        The devices that shall be managed by this dut
    dut_ref         : :class:`~DMT.core.dut_view.DutView`
        The reference device of this technology
    dut_intrinsic   : :class:`~DMT.core.dut_view.DutView`
        The intrinsic dut of the reference dut (without rbi)
    dut_internal    : :class:`~DMT.core.dut_view.DutView`
        The internal dut of the reference dut (with rbi)
    save_dir        : str
        Here the DutLib will try to save itself
    n_jobs          : int, optional
        Number of parallel jobs, passed on to joblib.Parallel.

    wafer : int or str
        A unique identifier of the wafer that the data in this lib stems from
    date_tapeout  : str
        Tapeout date.
    date_received : str
        Received date.

    Methods
    -------
    find_devices(type)
        Searches for all devices of the specified type and puts them into a separate list.
    sort_duts()
        Assigns the correct Deembedding structures to the DUT.
    deembed_AC()
        Deembeds measured AC data with the corresponding O&S data.
    deembed_DC()
        Deembeds measured AC data with the corresponding O&S data.
    """

    def __init__(
        self,
        deem_types=None,
        AC_filter_names=None,
        DC_filter_names=None,
        is_deembedded_DC=False,
        is_deembedded_AC=False,
        save_dir=None,
        force=False,
        n_jobs=4,
    ):
        if deem_types is None:
            self.deem_types = [DutType.npn]
        else:
            self.deem_types = deem_types

        self.AC_filter_names = AC_filter_names
        self.DC_filter_names = DC_filter_names
        self.is_deembedded_AC = is_deembedded_AC
        self.is_deembedded_DC = is_deembedded_DC

        self.deem_open = (
            DutType.flag_open
        )  # deem_open_bjt # look only for the flag not for the device!
        self.deem_short = DutType.flag_short  # deem_short_bjt

        self.duts = []  # The devices that shall be managed by this dut
        self._dut_ref = None  # The reference device of this technology
        self.dut_ref_dut_dir = None
        self._dut_intrinsic = None  # The intrinsic dut of the reference dut (without rbi)
        self.dut_intrinsic_dut_dir = None  # The intrinsic dut of the reference dut (without rbi)
        self._dut_internal = None  # The internal dut of the reference dut (with rbi)
        self.dut_internal_dut_dir = None  # The intrinsic dut of the reference dut (without rbi)
        self._save_dir = None  # Here the DutLib will try to save itself
        if save_dir is not None:
            if force:
                try:
                    shutil.rmtree(save_dir)
                except FileNotFoundError:
                    pass

            self.save_dir = save_dir  # Here the DutLib will try to save itself

        self.ignore_duts = []  # list of names which are not returned while iteration

        self.n_jobs = n_jobs  # number of parallel jobs while directory import

        # additional information to help assess the data later
        self.wafer = None
        self.date_tapeout = None
        self.date_received = None

    @property
    def dut_ref(self):
        """Returns always just self._dut_ref"""
        if self._dut_ref is None:
            raise IOError("Dut_ref doesn't exist!")

        return self._dut_ref

    @dut_ref.setter
    def dut_ref(self, dut):
        """Ensure that dut_ref is in duts"""
        if not id(dut) in [id(dut_) for dut_ in self.duts]:
            self.duts.append(dut)

        self._dut_ref = dut

    @property
    def dut_internal(self):
        """Returns always just self._dut_internal"""
        if self._dut_internal is None:
            raise IOError("Dut_internal doesn't exist!")

        return self._dut_internal

    @dut_internal.setter
    def dut_internal(self, dut):
        """Ensure that dut_internal is in duts"""
        if not id(dut) in [id(dut_) for dut_ in self.duts]:
            self.duts.append(dut)

        self._dut_internal = dut

    @property
    def dut_intrinsic(self):
        """Returns always just self._dut_intrinsic"""
        if self._dut_intrinsic is None:
            raise IOError("Dut_intrinsic doesn't exist!")

        return self._dut_intrinsic

    @dut_intrinsic.setter
    def dut_intrinsic(self, dut):
        """Ensure that dut_intrinsic is in duts"""
        if not id(dut) in [id(dut_) for dut_ in self.duts]:
            self.duts.append(dut)

        self._dut_intrinsic = dut

    @property
    def save_dir(self):
        """Just return save dir"""
        return self._save_dir

    @save_dir.setter
    def save_dir(self, path):
        """Ensures an empty folder for the DutLib"""
        path = Path(path).resolve()
        if (path / "dut_lib.p").is_file():
            raise FileExistsError(
                "The path you chose is already used by an other library! Either delete the already existing library or load it."
            )

        self._save_dir = path

    def find_devices(self, devtype):
        """Searches the list of duts read in from the specified folder previously for the specified dut_type and adds all identified devices to a new list.

        Parameters
        ----------
        devtype : tuple
            Contains one or several dut_types that are to be identified to be added to a new list.
        """

        sorted_list = []
        # find specified dut_type and append element
        for ty in devtype:
            for dut in self:
                if dut.dut_type.is_subtype(ty):
                    sorted_list.append(dut)

        return sorted_list

    def import_directory(
        self, import_dir, dut_filter, dut_level=1, temperature_converter=None, force=True, **kwargs
    ):
        """Read in all files in import_dir into a DutLib object.

        Read in all devices in the subfolders of a directory.

        Data "dut_level" folders apart with respect to import_dir will be stored into one database and one DutView object.
        Example folder structure to illustrate this principle::

            Measurement
            ├───die1
            |   ├───Device1
            |   └───Device2
            └───die2
                └───Device1

        then for importing with this method, import_dir is set to `Measurement/` and dut_level is set to 2.
        The DutView objects need to be supplied by the callable object (function) dut_filter, which is supplied by the user.
        The dut_filter function is called with the DutView's relative path with respect to import dir and shall return a fully initialized DutView object.

        Parameters
        ----------
        import_dir       :  string or os.Pathlike
            Path to the directory that contains all dies on a wafer.
        dut_filter       :  callable
            User supplied function that is called with the relative paths dut_level levels below import_dir and returns DutView objects.
        dut_level        :  int
            Subfolder level that contains data of ONE specifid DutView. Files that lie in this level will be put into one database.
        temperature_converter :  callable object, optional
            Called to convert the directory name into a key part.
            If key does not contain a temperature, it should return -1.
            If it does contain a temperature, the temperature in Kelvin should be returned.
            Defaults to :meth:`~DMT.core.dut_meas.DutMeas.temp_converter_default`
        force            :  bool
            Default = True. If True, databases and duts that have already been imported are overwritten.
        kwargs   :  bool
            Additional keyword arguments that are passed to the read_data routines, which are called to read the (mdm, csv or elpa) data. E.g. if you have delimiter ',' in your .csv file, pass delimeter=','.

        Returns
        -------
        duts : [:class:`~DMT.core.dut_view.DutView`]
            DutViews loaded from the given directory
        """
        if not isinstance(import_dir, Path):
            import_dir = Path(import_dir)

        if not callable(dut_filter):
            raise IOError(
                "DMT -> DataManager -> import_directory(): You did not specify a dut_filter function.\n How shall DMT know what kind of Dut is where?"
            )

        print("\n")
        print("DMT will now try to recursively import DutView objects from directory:")
        print(import_dir)
        print("\n")

        # prepare progress bar and find out how many duts we will read
        duts = []
        dut_paths = []
        if dut_level == 0:
            duts.append(dut_filter(str(import_dir.resolve())))
            dut_paths.append(import_dir.resolve())
        else:
            for child in import_dir.glob("*/" * (dut_level)):  # can be used in windows and linux
                if child.is_dir():  # only directories are allowed
                    child = child.resolve()
                    dut = dut_filter(str(child))
                    if dut is not None:
                        dut_paths.append(child)
                        duts.append(dut)

        if len(duts) == 0:
            raise IOError(
                "DMT -> collect_data: Did not find a single candidate for importing in directory "
                + str(import_dir)
                + " ."
            )

        # walk through all files of each dut and gather the mdm files
        datas = Parallel(n_jobs=self.n_jobs, verbose=10)(
            _read_dut_folder(dut, path, force, temperature_converter, **kwargs)
            for dut, path in zip(duts, dut_paths)
        )

        for dut, data in zip(duts, datas):
            dut._data = data  # pylint: disable=protected-access

        print("DutLib imported " + str(len(duts)) + " DUTs.")

        if not self.is_deembedded_AC and not self.is_deembedded_DC:
            self.add_duts(duts)

        return duts

    def add_duts(self, duts):
        """Add duts to the DutLib duts array.

        Parameters
        ----------
        duts : [DutView] or DutView
            The dut or duts that shall be added.
        """
        if self.is_deembedded_AC or self.is_deembedded_DC:
            raise IOError("DutLib: I am already deembedded and don" "t want to add Duts.")

        try:
            for dut in duts:
                self.duts.append(dut)
        except TypeError:
            self.duts.append(duts)

    def save(self):
        """Save the DutLib to save_dir."""
        assert self.save_dir is not None

        if not os.path.isabs(self.save_dir):
            self._save_dir = os.path.abspath(self.save_dir)

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        ignore_duts = copy.deepcopy(self.ignore_duts)
        self.ignore_duts = []  # save all duts, even the one who were ignored
        for dut in self.duts:
            if dut.database_dir != os.path.join(self.save_dir, "duts"):
                try:  # if enough data available, sort by wafer and dies
                    directory = os.path.join(
                        self.save_dir, "duts", "wafer_" + str(dut.wafer), "die_" + str(dut.die)
                    )
                except:
                    directory = os.path.join(self.save_dir, "duts")
                dut.database_dir = directory

            dut.save()

        if self._dut_ref is not None:
            path_abs = Path(self.dut_ref.dut_dir).resolve()
            if filecmp.cmp(path_abs, self.dut_ref.dut_dir):
                self.dut_ref_dut_dir = path_abs
            else:
                raise IOError(
                    "DMT->DutLib->Save: I can not convert the relative dut path of dut_ref into an absolute path!"
                )

        if self._dut_internal is not None:
            path_abs = Path(self.dut_internal.dut_dir).resolve()
            if filecmp.cmp(path_abs, self.dut_internal.dut_dir):
                self.dut_internal_dut_dir = path_abs
            else:
                raise IOError(
                    "DMT->DutLib->Save: I can not convert the relative dut path of dut_internal into an absolute path!"
                )

        if self._dut_intrinsic is not None:
            path_abs = Path(self.dut_intrinsic.dut_dir).resolve()
            if filecmp.cmp(path_abs, self.dut_intrinsic.dut_dir):
                self.dut_intrinsic_dut_dir = path_abs
            else:
                raise IOError(
                    "DMT->DutLib->Save: I can not convert the relative dut path of dut_intrinsic into an absolute path!"
                )

        self.ignore_duts = ignore_duts  # but save the list ignore
        with open(os.path.join(self.save_dir, "dut_lib.p"), "wb") as handle:
            cpickle.dump(self, handle)

    @staticmethod
    def load(lib_directory):
        """Static class method. Loads a DutLib object from a pickle file with full path lib_directory.

        Parameters
        ----------
        lib_directory  :  str or os.Pathlike
            Path to the direcotry that contains a pickled DutLib object that shall be loaded.

        Returns
        -------
        obj  :  DutLib()
            Loaded object from the pickle file.
        """
        # pylint: disable=unused-variable
        lib_directory = Path(lib_directory).resolve()
        with (lib_directory / "dut_lib.p").open(mode="rb") as handle:
            dut_lib = cpickle.load(handle)
            dut_lib._save_dir = Path(dut_lib.save_dir)  # pylint: disable=protected-access

        save_dir_old = ""
        # need to cast paths? This is needed when the machine is changed -> new absolute paths...
        if (
            lib_directory != dut_lib.save_dir
        ):  # dut_lib.save_dir is the old absolute path of the lib
            save_dir_old = str(dut_lib.save_dir)
            # write to internal value to avoid consistency check
            dut_lib._save_dir = lib_directory  # pylint: disable=protected-access

        # load all duts
        ignore_duts = copy.deepcopy(dut_lib.ignore_duts)
        dut_lib.ignore_duts = []  # load all duts, even the one who were ignored
        for dir_name, dir_list, file_list in os.walk(dut_lib.save_dir / "duts"):  # find the duts
            for file_dut in file_list:
                if file_dut.endswith(".p"):
                    dut_lib.duts.append(DutView.load_dut(os.path.join(dir_name, file_dut)))

        # correct dut paths:
        if dut_lib.dut_ref_dut_dir is not None:
            dut_lib.dut_ref_dut_dir = Path(dut_lib.dut_ref_dut_dir)
            if not dut_lib.dut_ref_dut_dir.exists():
                dut_lib.dut_ref_dut_dir = Path(
                    str(dut_lib.dut_ref_dut_dir).replace(save_dir_old, str(lib_directory))
                )
        if dut_lib.dut_internal_dut_dir is not None:
            dut_lib.dut_internal_dut_dir = Path(dut_lib.dut_internal_dut_dir)
            if not dut_lib.dut_internal_dut_dir.exists():
                dut_lib.dut_internal_dut_dir = Path(
                    str(dut_lib.dut_internal_dut_dir).replace(save_dir_old, str(lib_directory))
                )
        if dut_lib.dut_intrinsic_dut_dir is not None:
            dut_lib.dut_intrinsic_dut_dir = Path(dut_lib.dut_intrinsic_dut_dir)
            if not dut_lib.dut_intrinsic_dut_dir.exists():
                dut_lib.dut_intrinsic_dut_dir = Path(
                    str(dut_lib.dut_intrinsic_dut_dir).replace(save_dir_old, str(lib_directory))
                )

        for dut in dut_lib.duts:
            if dut_lib.dut_ref_dut_dir is not None:
                if filecmp.cmp(dut.dut_dir, dut_lib.dut_ref_dut_dir):
                    dut_lib.dut_ref = dut
            if dut_lib.dut_internal_dut_dir is not None:
                if filecmp.cmp(dut.dut_dir, dut_lib.dut_internal_dut_dir):
                    dut_lib.dut_internal = dut
            if dut_lib.dut_intrinsic_dut_dir is not None:
                if filecmp.cmp(dut.dut_dir, dut_lib.dut_intrinsic_dut_dir):
                    dut_lib.dut_intrinsic = dut

        dut_lib.ignore_duts = ignore_duts  # but keep the list ignore
        return dut_lib

    def __getstate__(self):
        """Return state values to be pickled. Implemented according `to <https://www.ibm.com/developerworks/library/l-pypers/index.html>`_ ."""
        d = copy.copy(self.__dict__)
        if "duts" in d:
            del d["duts"]
        if "dut_ref" in d:
            del d["dut_ref"]
        if "dut_intrinsic" in d:
            del d["dut_intrinsic"]
        if "dut_internal" in d:
            del d["dut_internal"]
        return d

    def __setstate__(self, state):
        """Return state values to be pickled. Implemented according `to <https://www.ibm.com/developerworks/library/l-pypers/index.html>`_ ."""
        # pylint: disable = attribute-defined-outside-init
        self.__dict__ = state
        self.__dict__["duts"] = []
        self.__dict__["dut_ref"] = None
        self.__dict__["dut_intrinsic"] = None
        self.__dict__["dut_internal"] = None

    def deembed_AC(self, width_filter, length_filter, name_filter, user_fun=None):
        """Assign O&S structures to the correct devices for later deembedding process and adds the thus assigned devices to a new list,
        which only includes teststructures for characterization and no O&S structures separately.

        Parameters
        ----------
        width_filter : bool
            If true: use de-embedding structures at same width, else ignore width.
        length_filter : bool
            If true: use de-embedding structures at same length, else ignore length.
        name_filter : bool
            If true: use de-embedding structures with same string in property 'deemb_name', else ignore.
        user_fun : callable, optional
            User specific function that gets one Dut object as an argument and returns the corresponding open, short Duts.

        Methods
        -------
        lowLevelSort(testStru,fn)
            Applies the necessary filter functions to a device and a deembedding structure and adds the correct deembedding structure accordingly to the device.

        Notes
        -----
        ..todo: allow the user to pass his own filters.

        """
        if self.is_deembedded_AC:
            raise IOError("Library has already been deembedded.")

        lenFilter = LenFilter()
        widthFilter = WidthFilter()
        nameFilter = NameFilter()

        # Add duts to separate lists according to dut_type.
        dev_list = self.find_devices(self.deem_types)

        if len(dev_list) == 0:
            print("Warning: No devices in library require AC de-embedding.")
            return
        open_list = self.find_devices([self.deem_open])
        short_list = self.find_devices([self.deem_short])

        if len(short_list) == 0 or len(open_list) == 0:
            raise IOError("DMT -> DutLib -> sort_duts: Did not find any open or short duts.")

        # in the simplest case we only have one deemb device. Then use it.
        if len(open_list) == 1 and len(short_list) == 1:
            print("\n")
            print("DMT will now try to deembed all devices in DutLib object:")
            for i_dev, dev in enumerate(dev_list):
                self.deembed_dut_AC(dev, open_list[0], short_list[0])
                print_progress_bar(
                    i_dev, len(dev_list), prefix="Deembedding AC:", suffix=dev.name, length=50
                )

            print_progress_bar(
                len(dev_list), len(dev_list), prefix="Deembedding AC:", suffix=dev.name, length=50
            )
            self.is_deembedded_AC = True
            return

        # more than one deemb device, then we need filters.
        if not width_filter and not length_filter and not name_filter and user_fun is None:
            raise IOError(
                "DMT -> DutLib: You did not select any filter flags that would allow deembedding! Alternative: pass user_fun"
            )

        # Iterating through the dev_list, which contains all devices that require deembedding.
        for i_dev, dev in enumerate(dev_list):
            print("\n")
            print("DMT will now try to deembed all devices in DutLib object:")
            suitable_opens = []
            suitable_shorts = []
            if user_fun is None:
                for deem_dut in open_list + short_list:
                    if name_filter:
                        if not nameFilter.filter(dev, deem_dut):
                            continue

                    if width_filter:
                        if not widthFilter.filter(dev, deem_dut):
                            continue

                    if length_filter:
                        if not lenFilter.filter(dev, deem_dut):
                            continue

                    if deem_dut.dut_type.is_subtype(self.deem_open):
                        suitable_opens.append(deem_dut)
                    else:
                        suitable_shorts.append(deem_dut)
            else:  # user user supplied function
                suitable_open, suitable_short = user_fun(dev)
                suitable_opens.append(suitable_open)
                suitable_shorts.append(suitable_short)

            # if we found more than one suitable short or open, throw an error.
            if len(suitable_opens) > 1 or len(suitable_shorts) > 1:
                message = "DMT -> DutLib -> sort_duts: For dut:\n"
                message += dev.name + "\n"
                message += " more than one short/open deembeding structure was found:\n"
                for suitable_dut in suitable_opens + suitable_shorts:
                    message += suitable_dut.name + "\n"

                raise IOError(message)

            elif len(suitable_opens) == 0:
                raise NoOpenDeembeddingDut(
                    "For "
                    + dev.name
                    + " no open was found. Deemb_name is "
                    + dev.deemb_name
                    + ".\n"
                    + "Available opens: "
                    + "".join([dut.name + " " for dut in open_list])
                )
            elif len(suitable_shorts) == 0:
                raise NoShortDeembeddingDut("For " + dev.name + " no Short was found.")
            else:
                print_progress_bar(
                    i_dev, len(dev_list), prefix="Deembedding AC:", suffix=dev.name, length=50
                )
                self.deembed_dut_AC(dev, suitable_opens[0], suitable_shorts[0])

            print_progress_bar(
                len(dev_list), len(dev_list), prefix="Deembedding AC:", suffix=dev.name, length=50
            )

            # Deembed DC data if required
        self.is_deembedded_AC = True

    def deembed_AC_internal(self, mcard, method):
        """Deembed the dut_ref to this dut_lib and save the new dut as dut_internal

        Parameters
        ----------
        mcard  : Hl2Mcard
            A Hicum modelcard that contains accurate values for all external elements of the Hl2 transistor model.

        method : a function
            A compact model specific routine that has the following signature: method(df, mcard), where df is a dataframe and mcard a modelcard and method returns a df with deembedded data.
        """
        if self.dut_ref is None:
            raise IOError("Library has no reference dut that is suitable for deembedding!")

        self.deembed_dut_AC_internal(self.dut_ref, mcard, method)

    def deembed_DC(
        self,
        width_filter,
        length_filter,
        name_filter,
        function_dut=None,
        function_df=None,
        shorts=None,
        t_ref=300,
        forced_current=False,
    ):
        """Assign O&S structures to the correct devices for later deembedding process and adds the thus assigned devices to a new list,
        which only includes teststructures for characterization and no O&S structures separately.

        Parameters
        ----------
        duts : [duts]
            List of duts that needs to be sorted.
        shorts : [duts], None
            List of shorts that should be used.
        function_dut : function, optional
            a function method(dut_short) that returns the metallization resistances as a dict {'R_EM':float64, 'R_BM':float64, 'R_CM':float64}. Use this if the default DMT DC deembeding is not suitable.
        function_df  : function, optional
            a function method(df_short) that returns the metallization resistances as a dict {'R_EM':float64, 'R_BM':float64, 'R_CM':float64}. Use this if the default DMT DC deembeding is not suitable.
        t_ref       : float, optional
            Temperature of the metallization resistances to return

        Methods
        -------
        lowLevelSort(testStru,fn)
            Applies the necessary filter functions to a device and a deembedding structure and adds the correct deembedding structure accordingly to the device.

        Returns
        -------
        mres : dict
            {'R_EM':float64, 'R_BM':float64, 'R_CM':float64}

        Notes
        -----
        ..todo: allow the user to pass his own filters.

        """
        if self.is_deembedded_DC:
            raise IOError("Library has already been deembedded.")

        lenFilter = LenFilter()
        widthFilter = WidthFilter()
        nameFilter = NameFilter()

        # Add duts to separate lists according to dut_type.
        dev_list = self.find_devices(self.deem_types)
        if len(dev_list) == 0:
            print("Warning: No devices in library require DC de-embedding.")
            return
        if shorts is None:
            short_list = self.find_devices([self.deem_short])
        else:
            short_list = shorts

        if len(short_list) == 0 and not function_dut and not function_df:
            raise IOError("DMT -> DutLib -> sort_duts: Did not find any short duts.")

        # in the simplest case we only have one deemb device. Then use it.
        if len(short_list) == 1 or len(short_list) == 0:
            print("\n")
            print("DMT will now try to deembed all devices in DutLib object:")
            short_i = None
            if len(short_list) == 1:
                short_i = short_list[0]

            for i_dev, dev in enumerate(dev_list):
                if dev == self.dut_ref:
                    mres = self.deembed_dut_DC(
                        dev,
                        short_i,
                        function_dut=function_dut,
                        function_df=function_df,
                        t_ref=t_ref,
                        forced_current=forced_current,
                    )
                else:
                    self.deembed_dut_DC(
                        dev,
                        short_i,
                        function_dut=function_dut,
                        function_df=function_df,
                        t_ref=t_ref,
                        forced_current=forced_current,
                    )
                print_progress_bar(
                    i_dev, len(dev_list), prefix="Deembedding DC:", suffix=dev.name, length=50
                )

            print_progress_bar(
                len(dev_list), len(dev_list), prefix="Deembedding DC:", suffix="finish", length=50
            )
            self.is_deembedded_DC = True
            return mres

        # more than one deemb device, then we need filters.
        if not width_filter and not length_filter and not name_filter:
            raise IOError(
                "DMT -> DutLib: You did not select any filter flags that would allow deembedding!"
            )

        # Iterating through the dev_list, which contains all devices that require deembedding.
        for i_dev, dev in enumerate(dev_list):
            print("\n")
            print("DMT will now try to DC deembed all devices in DutLib object:")
            suitable_shorts = []
            for deem_dut in short_list:
                if name_filter:
                    if not nameFilter.filter(dev, deem_dut):
                        continue

                if width_filter:
                    if not widthFilter.filter(dev, deem_dut):
                        continue

                if length_filter:
                    if not lenFilter.filter(dev, deem_dut):
                        continue

                suitable_shorts.append(deem_dut)

            # if we found more than one suitabel short or open, throw an error.
            if len(suitable_shorts) > 1:
                message = r"DMT -> DutLib -> sort_duts: For dut:\n"
                message += dev.name + r"\n"
                message += r" more than one short/open deembeding structure was found:\n"
                for suitable_dut in suitable_shorts:
                    message += suitable_dut.name + r"\n"

                raise IOError(message)

            elif len(suitable_shorts) == 0:
                raise NoShortDeembeddingDut("For " + dev.name + " no short was found.")
            else:
                print_progress_bar(
                    i_dev, len(dev_list), prefix="Deembedding DC:", suffix=dev.name, length=50
                )
                mres = self.deembed_dut_DC(
                    dev,
                    suitable_shorts[0],
                    function_dut=function_dut,
                    function_df=function_df,
                    t_ref=t_ref,
                    forced_current=forced_current,
                )

        print_progress_bar(
            len(dev_list), len(dev_list), prefix="Deembedding DC:", suffix=dev.name, length=50
        )

        self.is_deembedded_DC = True

        return mres

    def deembed_dut_AC(self, dut, dut_open, dut_short):
        """Checks for all AC measurement data that needs to be deembedded. Differentiates between hot and cold S-parameters and picks the deembedding files accordingly.

        Parameters
        ----------
        dut         : [dut]
            Current DuT which is to be deembedded.
        dut_open    : [dut.DutType.open_deem]
            Corresponding open
        dut_short    : [dut.DutType.short_deem]
            Corresponding short

        """
        # Filter function that creates a temporary filter for each deembedding - DuT df pair, which need to be considered for deembedding
        # def temp_filter(filter_name, key_):
        #     if re.search(filter_name, key_, re.IGNORECASE):
        #         return True
        #     else:
        #         return False

        # Go through all available filters and find dfs matching their values
        for key in dut.data.keys():
            requires_deemb = False
            deembedded = False

            # first find out, if any filter applies here. if yes, likely this data needs deembedding
            for (meas_filter, deem_filter) in self.AC_filter_names:
                if re.search(meas_filter, key, re.IGNORECASE):
                    requires_deemb = True
                    break

            for (meas_filter, deem_filter) in self.AC_filter_names:
                # check if df needs to be AC deembedded & find O&S structure
                if re.search(meas_filter, key, re.IGNORECASE):
                    short_keys = []
                    open_keys = []

                    # find all possible opens
                    for open_key in dut_open.data.keys():
                        if re.search(deem_filter, open_key, re.IGNORECASE):
                            open_keys.append(open_key)

                    for short_key in dut_short.data.keys():
                        if re.search(deem_filter, short_key, re.IGNORECASE):
                            short_keys.append(short_key)

                    if len(short_keys) == 0 or len(open_keys) == 0:
                        continue  # maybe another filter applies

                    # if only one suitable short or open has been found we just take it
                    if len(short_keys) == 1 and len(open_keys) == 1:
                        df_open = dut_open.data[open_keys[0]]
                        df_short = dut_short.data[short_keys[0]]
                        dut.data[key] = dut.data[key].deembed(
                            df_open,
                            df_short,
                            ports=dut.nodes,
                            ndevices=dut.ndevices,
                            ndevices_open=dut_open.ndevices,
                            ndevices_short=dut_short.ndevices,
                        )
                        # we get the number of deembedded dirty...
                        # times = dut.ndevices/dut_open.ndevices # not implemented anymore
                        times = 1
                        dut.open_deembedded_with = str(times) + "x" + dut_open.name
                        dut.short_deembedded_with = str(times) + "x" + dut_short.name

                    # bad news...try to find same temperatures. #TODO: Does not work if no keys are found
                    else:
                        key_temperature = dut.get_key_temperature(key)
                        for open_key in open_keys:
                            if key_temperature == dut_open.get_key_temperature(open_key):
                                break

                        for short_key in short_keys:
                            if key_temperature == dut_short.get_key_temperature(short_key):
                                break

                        df_open = dut_open.data[open_key]
                        df_short = dut_short.data[short_key]
                        try:
                            dut.data[key] = dut.data[key].deembed(
                                df_open,
                                df_short,
                                ports=dut.nodes,
                                ndevices=dut.ndevices,
                                ndevices_open=dut_open.ndevices,
                                ndevices_short=dut_short.ndevices,
                            )
                        except ValueError as err:
                            raise IOError(
                                "The dataframes with keys "
                                + open_key
                                + " and "
                                + short_key
                                + " from open device "
                                + dut_open.name
                                + " and short device "
                                + dut_short.name
                                + " are not matching the data in key "
                                + key
                                + " from dut "
                                + dut.name
                                + "."
                            ) from err

                        # we get the number of deembedded dirty...
                        # times = dut.ndevices/dut_open.ndevices
                        times = 1
                        dut.open_deembedded_with = str(times) + "x" + dut_open.name
                        dut.short_deembedded_with = str(times) + "x" + dut_short.name

                    deembedded = True
                    break

            if not deembedded and requires_deemb:
                raise IOError(
                    "During AC Deembedding: Dataframe "
                    + key
                    + " of DutMeas "
                    + dut.name
                    + " seems to require deembedding, but not a single suitable key was found."
                )

    def deembed_dut_AC_internal(self, dut, mc, method):
        """Checks for all AC measurement data and deduces the internal small signal S Parameters.

        Parameters
        ----------
        dut         : DutView
            A suitable device for internal deembedding.
        mc          : Hl2MCard
            Hicum Modelcard that holds accurate values for the external hicum elements.
        method      : A routine that has the following signature method(df, mc), where df is a dataframe and mc a modelcard and the output is an internally
                      deembedded dataframe.

        """
        # count number of keys to deembed
        n_keys = 0
        for meas_filter in self.AC_filter_names:
            for key in dut.data.keys():
                # check if df needs to be AC deembedded & find O&S structure
                if re.search(meas_filter, key, re.IGNORECASE):
                    n_keys = n_keys + 1

        n = 1
        # Go through all available filters and find dfs matching their values
        for meas_filter in self.AC_filter_names:
            for key in dut.data.keys():
                # check if df needs to be AC deembedded & find O&S structure
                if re.search(meas_filter, key, re.IGNORECASE):
                    print_progress_bar(
                        n, n_keys, prefix="Deembedding internal:", suffix=dut.name, length=50
                    )
                    t_dev = dut.get_key_temperature(key)
                    dut.data[key] = method(dut.data[key], mc, t_dev=t_dev)
                    n = n + 1

    def load_database(self, database_dir, only_meas=True):
        """Loads all DuTs from a given database directory. Does NOT load the data of the duts, they are loaded using run_and_read

        Parameters
        ----------
        database_dir : str
        only_meas : {True, False}, optional
            If True, only folders without "_hash_" are loaded. This is exclusive for :class:`~DMT.core.dut_meas.DutMeas`

        Returns
        -------
        duts : [:class:`~DMT.core.dut_view.DutView`]
            DutViews loaded from the given directory
        """
        if only_meas:
            views = "all measurement duts"
        else:
            views = "all duts"

        print("\n")
        print("DMT will load " + views + " from the database directory:")
        print(database_dir)
        print("\n")

        duts = []
        for dir_dut in os.listdir(database_dir):
            if only_meas:
                if "_hash_" in dir_dut:
                    continue

            duts.append(DutView.load_dut(os.path.join(database_dir, dir_dut, "dut.p")))

        print("DMT loaded " + str(len(duts)) + " DUTs.")

        if not self.is_deembedded_AC and not self.is_deembedded_DC:
            self.add_duts(duts)

        return duts

    # Makes it possible to iterate over DutLib objects
    def __iter__(self):
        return iter([dut for dut in self.duts if dut.name not in self.ignore_duts])

    def __getitem__(self, key):
        return self.duts[key]

    def normalize(self, dut_type):
        for dut in self.duts:
            if dut.dut_type == dut_type:
                if dut.ndevices > 1:
                    for key in dut.data.keys():
                        df = dut.data[key]
                        dut.data[key] = df.parallel_norm(dut.ndevices, *dut.ac_ports)

    def deembed_dut_DC(
        self, dut, dut_short, function_dut=None, function_df=None, t_ref=300, forced_current=False
    ):
        """Deembeds all DC_measurements in GSG-Pads.

        Parameters
        ----------
        dut         : [dut]
            Current DuT which is to be deembedded.
        dut_short   : [dut.DutType.short_deem]
            Corresponding short
        function_dut : function, optional
            a function method(dut_short) that returns the metallization resistances as a dict {'R_EM':float64, 'R_BM':float64, 'R_CM':float64}. Use this if the default DMT DC deembeding is not suitable.
        function_df  : function, optional
            a function method(df_short) that returns the metallization resistances as a dict {'R_EM':float64, 'R_BM':float64, 'R_CM':float64}. Use this if the default DMT DC deembeding is not suitable.
        t_ref       : float, optional
            Temperature of the metallization resistances to return

        Returns
        -------
        dict  :  {'R_EM':float64, 'R_BM':float64, 'R_CM':float64}
        """
        # test input:
        if function_dut is not None and function_df is not None:
            raise IOError(
                "DMT->DutLib->deembed_DC: Either function_dut or function_df can be given, but not both!"
            )

        # print how exactly deembedding is performed for possible future debugging purposes
        # ISSUE: No for-loop "(meas_filter, deem_filter) in self.DC_filter_names:" performed here.
        # all measurements stored under keys are DC deembedded here!
        if function_dut is not None:
            mres_tref = function_dut(dut_short)
            print("\n")
            print(dut.name)
            print("\n")
            for key in dut.data.keys():
                print(key)
                dut.data[key] = dut.data[key].deembed_DC(
                    mres=mres_tref, forced_current=forced_current
                )
        else:
            mres_tref = None

            for (meas_filter, deem_filter) in self.DC_filter_names:
                # get the short keys
                short_keys = []
                for short_key in dut_short.data.keys():
                    if re.search(deem_filter, short_key, re.IGNORECASE):
                        short_keys.append(short_key)

                if len(short_keys) == 1:
                    # if only one short key has been found we just take it for everything
                    df_short = dut_short.data[short_keys[0]]

                    if function_df is None:
                        mres_tref = df_short.determine_mres(forced_current=forced_current)
                    else:
                        mres_tref = function_df(dut_short)

                for key in dut.data.keys():
                    # check if df needs to be DC deembedded
                    if re.search(meas_filter, key, re.IGNORECASE):

                        if len(short_keys) == 1:
                            mres = mres_tref
                        else:  # NOT TESTED!!!!
                            # bad news...try to find matching temperatures. #TODO: Does not work if no keys are found
                            key_temperature = dut.get_key_temperature(key)
                            for short_key in short_keys:
                                if np.isclose(
                                    key_temperature, dut_short.get_key_temperature(short_key)
                                ):
                                    break
                            df_short = dut_short.data[short_key]

                            if function_df is None:
                                try:
                                    mres = df_short.determine_mres(forced_current=forced_current)
                                except IOError as err:
                                    raise IOError(
                                        "Column missing in df of dut "
                                        + dut_short.name
                                        + " of df with key "
                                        + short_key
                                        + ". Available keys: "
                                        + str(df_short.data.keys())
                                        + "."
                                    ) from err
                            else:
                                mres = function_df(dut_short)

                            if np.isclose(key_temperature, t_ref):
                                mres_tref = mres

                        dut.data[key] = dut.data[key].deembed_DC(
                            mres=mres, forced_current=forced_current
                        )

        return mres_tref

    def toTex(self):
        """This function generates a TeX representation of a DutLib.

        | This function generates a section with the title "Measured Devices"
        | For each DutType a table is generated that summarizes the available device dimensions for this DutType.
        """
        doc = Tex()
        with doc.create(Section("Measured Devices")):
            with doc.create(Subsection("Geometry Overview")):
                dut_types = list(set([dut.dut_type for dut in self]))
                for dut_type in dut_types:
                    configs = [dut.contact_config for dut in self if dut.dut_type == dut_type]
                    configs = list(set(configs))  # cast to unique
                    for config in configs:
                        if config is None:
                            doc.append(
                                NoEscape(
                                    r"Measurements for devices of type "
                                    + str(dut_type)
                                    + r" are available with the following geometries:"
                                )
                            )
                        else:
                            doc.append(
                                NoEscape(
                                    r"Measurements for devices with contact configuration "
                                    + config.replace("_", r"\_")
                                    + r" and device type "
                                    + str(dut_type)
                                    + r" are available with the following geometries:"
                                )
                            )

                        doc.append("\r")
                        duts = list(
                            set(
                                [
                                    dut
                                    for dut in self
                                    if dut.dut_type == dut_type and dut.contact_config == config
                                ]
                            )
                        )
                        lE0s = list(set([dut.length for dut in duts]))
                        bE0s = list(set([dut.width for dut in duts]))
                        lE0s.sort()
                        bE0s.sort()
                        header = "|" + " c | " * (
                            len(lE0s) + 1
                        )  # one col for each length and one for bE0 indices
                        with doc.create(Center()) as _centered:
                            with doc.create(Tabular(header)) as table:
                                table.add_hline()
                                first_row = [
                                    NoEscape(
                                        r"\backslashbox{$b_{\mathrm{E,drawn}}/\si{\micro\meter}$}{$l_{\mathrm{E,drawn}}/\si{\micro\meter}$}"
                                    )
                                ]
                                try:
                                    first_row += ["{:04.2f}".format(lE0 * 1e6) for lE0 in lE0s]
                                except TypeError:
                                    first_row += [
                                        ",".join(["{:04.2f}".format(lE0_a * 1e6) for lE0_a in lE0])
                                        for lE0 in lE0s
                                    ]

                                table.add_row(first_row)
                                table.add_hline()
                                for bE0 in bE0s:
                                    try:
                                        row = ["{:04.2f}".format(bE0 * 1e6)]
                                    except TypeError:
                                        row = [
                                            ",".join(
                                                ["{:04.2f}".format(bE0_a * 1e6) for bE0_a in bE0]
                                            )
                                        ]
                                    for lE0 in lE0s:
                                        try:
                                            # check if dut with these dimensions exists
                                            dut = next(
                                                dut
                                                for dut in duts
                                                if dut.length == lE0 and dut.width == bE0
                                            )
                                            row.append("x")
                                        except StopIteration:
                                            row.append(" ")

                                    table.add_row(row)
                                    table.add_hline()
                        doc.append("\r")

            with doc.create(
                Subsection("Measurement Data over Temperature and Deembedding Structures")
            ):
                # table that gives overview of all devices:
                # for npns:
                # | name  | Measured@T(K) | lE0_drawn | bE0_drawn | Open Deem. Structure | Short Deem. Structure |
                # other:
                # | name  | Measured@T(K) | l_drawn | b_drawn |
                # begin table
                dut_types = list(set([dut.dut_type for dut in self]))
                for dut_type in dut_types:
                    if not dut_type == DutType.npn:
                        continue

                    configs = [dut.contact_config for dut in self if dut.dut_type == dut_type]
                    configs = list(set(configs))  # cast to unique
                    for config in configs:
                        if config is None:
                            doc.append(
                                NoEscape(
                                    r"The following table gives an overview of all measurements for devices of type "
                                    + str(dut_type)
                                    + r"."
                                )
                            )
                        else:
                            doc.append(
                                NoEscape(
                                    r"The following table gives an overview of all devices with contact configuration "
                                    + config.replace("_", r"\_")
                                    + r" and device type "
                                    + str(dut_type)
                                    + r"."
                                )
                            )

                        doc.append("\r")
                        duts = list(
                            set(
                                [
                                    dut
                                    for dut in self
                                    if dut.dut_type == dut_type and dut.contact_config == config
                                ]
                            )
                        )
                        header = "|" + " c | " * 6  # number of columns
                        with doc.create(Center()) as _centered:
                            with doc.create(SmallText()) as _small:
                                with doc.create(Tabular(header)) as table:
                                    table.add_hline()
                                    first_row = [
                                        r"name ",
                                        NoEscape(r"measured @"),
                                        NoEscape(r"$l_{\mathrm{E0,drawn}}$"),
                                        NoEscape(r"$b_{\mathrm{E0,drawn}}$"),
                                        r"Open Deem. Structure",
                                        r"Short Deem. Structure",
                                    ]
                                    table.add_row(first_row)
                                    second_row = [
                                        r"",
                                        NoEscape(r"$T/\si{\kelvin}$"),
                                        NoEscape(r"$/\si{\micro\meter}$"),
                                        NoEscape(r"$/\si{\micro\meter}$"),
                                        r"",
                                        r"",
                                    ]
                                    table.add_row(second_row)
                                    table.add_hline()
                                    for dut in duts:
                                        # find temps
                                        temps = []
                                        for key in dut.data.keys():
                                            temps.append(dut.get_key_temperature(key))
                                        temps = list(set(temps))  # unique
                                        temps.sort()
                                        lE0_drawn = dut.length * 1e6
                                        bE0_drawn = dut.width * 1e6
                                        if len(temps) < 3:
                                            temps_str = ", ".join(["{}"] * len(temps)).format(
                                                *temps
                                            )
                                            row = [
                                                "{:s}".format(dut.name),
                                                temps_str,
                                                "{:04.2f}".format(lE0_drawn),
                                                "{:04.2f}".format(bE0_drawn),
                                                "{:s}".format(dut.open_deembedded_with),
                                                "{:s}".format(dut.short_deembedded_with),
                                            ]
                                            table.add_row(row)
                                            table.add_hline()
                                        else:  # split temps over two lines
                                            temps_str = ", ".join(["{}"] * len(temps[:3])).format(
                                                *temps[:3]
                                            )
                                            row = [
                                                "{:s}".format(dut.name),
                                                temps_str,
                                                "{:04.2f}".format(lE0_drawn),
                                                "{:04.2f}".format(bE0_drawn),
                                                "{:s}".format(dut.open_deembedded_with),
                                                "{:s}".format(dut.short_deembedded_with),
                                            ]
                                            table.add_row(row)
                                            temps_str = ", ".join(["{}"] * len(temps[3:])).format(
                                                *temps[3:]
                                            )
                                            row = [
                                                "",
                                                temps_str,
                                                "",
                                                "",
                                                "",
                                                "",
                                            ]
                                            table.add_row(row)
                                            table.add_hline()
                            doc.append("\r")
            # end table

            # reference device
            lE0 = r"{:04.2f}".format(self.dut_ref.length * 1e6)
            bE0 = r"{:04.2f}".format(self.dut_ref.width * 1e6)
            doc.append(
                NoEscape(
                    r"The reference device "
                    + self.dut_ref.name.replace("_", r"\_")
                    + r" is of type "
                    + str(self.dut_ref.dut_type)
                    + " in "
                    + self.dut_ref.contact_config.replace("_", r"\_")
                    + r" configuration and has $l_{\mathrm{E,drawn}}$ of $\SI{"
                    + lE0
                    + r"}{\micro\meter}$ and $b_{\mathrm{E,drawn}}$ of $\SI{"
                    + bE0
                    + r"}{\micro\meter}$."
                )
            )
            doc.append(
                NoEscape(
                    r"\enspace All extraction steps that do not deal with special test structures (like tetrodes) or with multiple device geometries, show measured data of the reference device."
                )
            )

        return doc

    def plot_all(self, mode=None, devices=None, output_settings=None, plot_specs=None, show=True):
        """This method generates plots for selected devices in the DutLib in a highly configurable way.

        Parameters
        ----------
        mode : dict of dict
            This dictionary specifies the mode used to select devices for plotting and the mode for plotting (not implemented):

            * If "dev_mode"="sel", the user needs to pass the "devices" argument as described below.
            * If "dev_mode"="all", all devices in the lib are used.

            Example::

                mode = {'dev_mode':'sel', }

        devices : [dict]
            This list specifies which devices to select from the lib. Only needed if "dev_mode"="sel" in the mode argument.
            Each dict specifies a contact configuration, length and width. All devices that match these properties are used for plotting.
            Example::

                devices = [{
                    'contact_config':'CBEBC',
                    'length'        :2.8e-6,
                    'width'         :0.22e-6,
                },]

        output_settings : dict
            This dict specifies how the plots will be stored. Example::

                output_settings = {
                    'width'      : '4.5in', #width of the Tikz Pictures
                    'height'     : '4.5in', #height of the Tikz Pictures
                    'create_doc' : True,    #If True: create documentation as pdf
                    'fontsize'   : 'Large', #Fontsize Tex specification
                    'clean'      : True,    #If True: remove all files except rendered picture after build
                    'base_path'  : os.path.join('/home','markus','Documents','Gitprojects','B11','additional_docu') #here all output of this method will be stored.
                    'svg'        : False    #bool, False: If True, build svg files instead of pdf files.
                    'build'      : True     #bool, True: If True, build the Tex files using pdflatex compiler. Else only print .tex files.
                    'mark_repeat': 20       #int,20: Only show every nth marker, where n=mark_repeat.
                    'clean'      : False,   #bool, False: Remove all files except *.pdf files in plots. Schroeter likes this.
                }

        plot_specs : [dict]
            For every plot type you want to create, this list contains one dict. Example::

                {
                    'type'        : 'ft_jc_vbc', #possible values are the plot_types that are stored in the defaults (see code below)
                    'exclude_at'  : [-0.2,0.5],  #every plot type generates lines "at" some quantity, e.g. gummel_vbc generates for every VBC. With this argument you can exclude lines.
                    'key'         : 'freq_vbc',  #data keys that will be used for this plot
                    'exact_match' : False,       #Bool, if True, use only keys that match "key" exactly
                    'FREQ'        : 10e9,        #optional, float: If given, use only data at FREQ
                    'xmin'        : 10e-2,       #optional, float: Minimum Value on x-axis to be displayed
                    'xmax'        : 1e2,         #optional, float: Maximum Value on x-axis to be displayed
                    'ymax'        : 300,         #optional, float: Maximum Value on y-axis to be displayed
                    'ymin'        : 0,           #optional, float: Minimum Value on y-axis to be displayed
                    'no_at'       : True,        #optional, Bool: if True, do not display the "at" quantities in the legend.
                },

        show : Bool
            If True, show the figures with matplotlib before further processing.
        """
        # defaults for autodoc feature plots
        plot_defaults = {
            DutType.npn: {
                "gummel_vbc": {
                    "x_log": False,
                    "y_log": True,
                    "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.VOLTAGE + "B" + "E",
                    "quantity_y": specifiers.CURRENT_DENSITY + "C",
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"Gummel @ $V_{\mathrm{BC}}$.",
                },
                "gummel_vbc_mark_ft": {
                    "x_log": False,
                    "y_log": True,
                    "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.VOLTAGE + "B" + "E",
                    "quantity_y": specifiers.CURRENT_DENSITY + "C",
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"Gummel @ $V_{\mathrm{BC}}$.",
                },
                "output_vbe": {
                    "x_log": False,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.VOLTAGE + "C" + "E",
                    "quantity_y": specifiers.CURRENT_DENSITY + "C",
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"Output @ $V_{\mathrm{BE}}$.",
                },
                "output_ib": {
                    "x_log": False,
                    "y_log": False,
                    "at": specifiers.CURRENT_DENSITY + "B",
                    "quantity_x": specifiers.VOLTAGE + "C" + "E",
                    "quantity_y": specifiers.CURRENT_DENSITY + "C",
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"Output @ $I_{\mathrm{B}}$.",
                },
                "ft_jc_vbc": {
                    "x_log": True,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.TRANSIT_FREQUENCY,
                    "legend_location": "upper left",
                    "y_limits": (0, None),
                    "x_limits": (None, None),
                    "tex": r"$f_{\mathrm{T}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{BC}}$.",
                },
                "fmax_jc_vbc": {
                    "x_log": True,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.MAXIMUM_OSCILLATION_FREQUENCY,
                    "legend_location": "upper left",
                    "y_limits": (0, None),
                    "x_limits": (None, None),
                    "tex": r"$f_{\mathrm{max}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{BC}}$.",
                },
                "ft_jc_vce": {
                    "x_log": True,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.TRANSIT_FREQUENCY,
                    "legend_location": "upper left",
                    "y_limits": (0, None),
                    "x_limits": (None, None),
                    "tex": r"$F_{\mathrm{T}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{CE}}$.",
                },
                "fmax_jc_vce": {
                    "x_log": True,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.MAXIMUM_OSCILLATION_FREQUENCY,
                    "legend_location": "upper left",
                    "y_limits": (0, None),
                    "x_limits": (None, None),
                    "tex": r"$f_{\mathrm{max}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{CE}}$.",
                },
                "beta_jc_vbc": {
                    "x_log": True,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.DC_CURRENT_AMPLIFICATION,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$\beta_{\mathrm{DC}} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
                },
                "rey21_f_vbe_vbc": {
                    "x_log": True,
                    "y_log": False,
                    "at": [
                        specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED,
                        specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    ],
                    "quantity_x": specifiers.FREQUENCY,
                    "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$\Re \left\{ Y_{21} \right\} \left( f \right)$ @ $V_{\mathrm{BC}} @ V_{\mathrm{BE}}$.",
                },
                "imy11_f_vbe_vbc": {
                    "x_log": True,
                    "y_log": True,
                    "at": [
                        specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED,
                        specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    ],
                    "quantity_x": specifiers.FREQUENCY,
                    "quantity_y": specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.IMAG,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$\Im \left\{ Y_{11} \right\} \left( f \right)$ @ $V_{\mathrm{BC}} @ V_{\mathrm{BE}}$.",
                },
                "y21_jc_vbc": {
                    "x_log": True,
                    "y_log": True,
                    "at": [
                        specifiers.FREQUENCY,
                        specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    ],
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
                },
                "y21_jc_vbc_mark_ft": {
                    "x_log": True,
                    "y_log": True,
                    "at": [
                        specifiers.FREQUENCY,
                        specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    ],
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
                },
                "y21_jc_vbc_mark_ft": {
                    "x_log": True,
                    "y_log": True,
                    "at": [
                        specifiers.FREQUENCY,
                        specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    ],
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
                },
                "tj_jc_at_vbc": {
                    "x_log": True,
                    "y_log": False,
                    "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
                    "quantity_x": specifiers.CURRENT_DENSITY + "C",
                    "quantity_y": specifiers.TEMPERATURE,
                    "legend_location": "upper left",
                    "y_limits": (None, None),
                    "x_limits": (None, None),
                    "tex": r"$T_{\mathrm{j}} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
                    "rth": 3e3,
                },
            },
        }
        output_settings_defaults = {
            "width": "3in",
            "height": "5in",
            "standalone": True,
            "svg": False,
            "build": True,
            "mark_repeat": 20,
            "clean": False,  # Remove all files except *.pdf files in plots
            "create_doc": False,  # Put everything into pdf
        }

        plot_spec_defaults = {
            "style": MIX,
            "legend": True,
            "dut_type": DutType.npn,
            "no_at": False,  # no at_specifier= in legend
        }

        # set defaults
        for plot_spec in plot_specs:
            for key in plot_spec_defaults:
                if key not in plot_spec.keys():
                    plot_spec[key] = plot_spec_defaults[key]

        for key in output_settings_defaults:
            if not key in output_settings.keys():
                output_settings[key] = output_settings_defaults[key]

        if not "base_path" in output_settings.keys():
            raise IOError("You did not specify a base_path in output_settings dict. Abort.")

        # check plot_spec
        for plot_spec in plot_specs:
            try:
                plot_type = plot_spec["type"]
            except KeyError as err:
                raise IOError("type not specified for plot specification.") from err

            valid_plots = plot_defaults[plot_spec["dut_type"]].keys()
            if not plot_type in valid_plots:
                raise IOError(
                    "Plot type "
                    + plot_type
                    + " not valid. Valid: "
                    + " ".join(str(plot_defaults.keys()))
                    + " ."
                )

            if not plot_spec["style"] in PLOT_STYLES:
                raise IOError("Plot style not valid. Valid: " + " ".join(PLOT_STYLES))

            if not "key" in plot_spec.keys():
                raise IOError("Database key not specified for plot of type " + plot_type + " .")

        # check input
        if not "dev_mode" in mode.keys():
            raise IOError('"dev_mode" not given in input_settings.')
        if not "plt_mode" in mode.keys():
            raise IOError('"plt_mode" not given in input_settings.')

        valid_modes = ["sel", "all"]
        if mode["plt_mode"] not in valid_modes:
            raise IOError("plt_mode " + mode + " not recognized. Valid: " + str(valid_modes) + " .")
        if mode["dev_mode"] not in valid_modes:
            raise IOError("dev_mode " + mode + " not recognized. Valid: " + str(valid_modes) + " .")

        duts = []  # array of DMT Duts
        if mode["dev_mode"] == "sel":
            for device_specs in devices:
                for dut in self:
                    # check all properties of device_spec
                    ok = True
                    for device_spec, val in device_specs.items():
                        if isinstance(val, str):
                            dut_property = getattr(dut, device_spec)
                            if dut_property != val:
                                ok = False
                        elif isinstance(val, float):
                            dut_property = getattr(dut, device_spec)
                            try:
                                if not np.isclose(dut_property, val):
                                    ok = False
                            except ValueError:  # tetrodes will not work like this (tuple dut_property)
                                pass

                    if ok:
                        print("Found device " + dut.name + ".")
                        duts.append(dut)
        else:
            duts = self.duts

        if len(duts) == 0:
            raise IOError("Found 0 devices.")

        print("Search finished...\nFound " + str(len(duts)) + " devices for plotting.")

        # ensure that plot with type gummel_vbc_mark_ft comes first
        for i, plot_spec in enumerate(plot_specs):
            if plot_spec["type"] == "gummel_vbc_mark_ft":
                if i == 0:
                    pass
                else:
                    plot_specs[0], plot_specs[i] = plot_specs[i], plot_specs[0]  # swap elements

                break

        print("Generating plots...")
        # for every plot try to generate appropriate plots
        plts = []
        for plot_spec in plot_specs:
            plot_type = plot_spec["type"]
            print("Generating plots of type " + plot_type + " .")

            style = plot_spec["style"]
            print("Chosen plot style: " + style)

            for dut in duts:
                # load default settings of plot
                try:
                    x_log = plot_defaults[dut.dut_type][plot_type]["x_log"]
                    y_log = plot_defaults[dut.dut_type][plot_type]["y_log"]
                    quantity_x = plot_defaults[dut.dut_type][plot_type]["quantity_x"]
                    quantity_y = plot_defaults[dut.dut_type][plot_type]["quantity_y"]
                    legend_location = plot_defaults[dut.dut_type][plot_type]["legend_location"]
                    at_specifier = plot_defaults[dut.dut_type][plot_type]["at"]
                except KeyError:
                    continue  # no plot_type in plot_defaults for this plot_spec

                # overwrite defaults with plot_spec
                try:
                    legend_location = plot_spec["legend_location"]
                except KeyError:
                    pass

                if not isinstance(at_specifier, list):
                    at_specifier = [at_specifier]

                quantities_to_ensure = [quantity_x, quantity_y] + at_specifier
                if "mark_ft" in plot_type:
                    quantities_to_ensure.append(specifiers.TRANSIT_FREQUENCY)
                    peaks = {"vbe": [], "jc": [], "vbc": []}  # store peak ft values for later

                at_scale = []
                for at_ in at_specifier:
                    try:
                        at_scale_ = natural_scales[at_.specifier]
                    except AttributeError:
                        at_scale_ = natural_scales[at_]

                    if at_ == specifiers.CURRENT + "B" or at_ == specifiers.CURRENT_DENSITY + "B":
                        at_scale_ = at_scale_ * 1e3

                    at_scale.append(at_scale_)

                print("Generating plot of type " + plot_type + " for dut " + dut.name + " ...")
                name = [
                    "dut_",
                    dut.name,
                    "_",
                    plot_type,
                ]
                if specifiers.TEMPERATURE in plot_spec.keys():
                    name.append("atT" + str(plot_spec[specifiers.TEMPERATURE]) + "K")
                if specifiers.FREQUENCY in plot_spec.keys():
                    name.append("atf" + str(plot_spec[specifiers.FREQUENCY] * 1e-9) + "GHz")

                for at_ in at_specifier:
                    name.append("at" + at_)

                name = "_".join(name)

                # calc drawn emitter windows area
                AE0_drawn = dut.width * dut.length * dut.contact_config.count("E")

                # find temperatures
                temps = []
                for key in dut.data.keys():
                    temps.append(dut.get_key_temperature(key))
                temps = list(set(temps))

                for temp in temps:

                    y_scale = 1
                    x_label = None  # autolabel
                    y_label = None
                    if (
                        quantity_y.specifier in specifiers.SS_PARA_Y
                    ):  # special cases that I do not want in DMT
                        y_scale = 1e3 / (1e6 * 1e6)  # mS/um^2
                        y_label = r"$\Re{ \left\{ Y_{21} \right\} } / \si{\milli\siemens\per\square\micro\meter } $"

                    plt = Plot(
                        name,
                        style=style,
                        num=name,
                        x_specifier=quantity_x,
                        y_specifier=quantity_y,
                        x_log=x_log,
                        y_log=y_log,
                        y_scale=y_scale,
                        x_label=x_label,
                        y_label=y_label,
                        legend_location=legend_location,
                    )
                    plt.dut_name = dut.name
                    plt.plot_type = plot_type
                    plt.dut = dut
                    plt.temp = temp
                    plt.plot_spec = plot_spec

                    n = 0
                    for key in dut.data.keys():
                        # selected only keys at temp
                        if not dut.get_key_temperature(key) == temp:
                            continue

                        if specifiers.TEMPERATURE in plot_spec.keys():
                            if temp != plot_spec[specifiers.TEMPERATURE]:
                                continue  # key not suitable

                        # matching key?
                        if "exact_match" not in plot_spec.keys():
                            plot_spec["exact_match"] = False

                        match = False
                        if plot_spec["exact_match"]:
                            match = plot_spec["key"] == key.split("/")[-1]
                        else:
                            match = plot_spec["key"] in key

                        if match:
                            df = dut.data[key]
                            if specifiers.FREQUENCY in plot_spec.keys():
                                try:
                                    df = df[
                                        df[specifiers.FREQUENCY] == plot_spec[specifiers.FREQUENCY]
                                    ]
                                except KeyError:
                                    pass

                            for quantity in quantities_to_ensure:
                                try:
                                    df.ensure_specifier_column(
                                        quantity, area=AE0_drawn, ports=dut.ac_ports
                                    )
                                except KeyError:
                                    if quantity == specifiers.TEMPERATURE:
                                        # calculate rough temperature
                                        pdiss = (
                                            df[specifiers.CURRENT + "C"].to_numpy()
                                            * df[specifiers.VOLTAGE + "C"].to_numpy()
                                        )

                                        # for the time beeing, only works for CBEBC devices...
                                        # calculate rth parameter
                                        a = 4.0 * self.dut_ref.length / self.dut_ref.width
                                        F_th = 1
                                        if a > 0.0:
                                            F_th = self.dut_ref.length / np.log(a)
                                        SRTHRM = plot_spec["rth"] / F_th

                                        # scale
                                        a = 4.0 * dut.length / dut.width
                                        F_th = 1
                                        if a > 0.0:
                                            F_th = dut.length / np.log(a)
                                        rth = SRTHRM * F_th

                                        df.loc[:, quantity] = temp + pdiss * rth
                                        dut.rth = rth

                                try:
                                    if quantity.specifier in specifiers_ss_para.SS_PARA_Y:
                                        df.loc[:, quantity] = df[quantity] / AE0_drawn
                                except:
                                    pass

                            at_vals = []
                            for i, at_ in enumerate(at_specifier):
                                at_val = df[at_].to_numpy()
                                if at_.specifier == specifiers.VOLTAGE:
                                    at_val = np.round(at_val, decimals=3)
                                    at_val = np.unique(at_val)
                                elif at_.specifier == specifiers.CURRENT:
                                    at_val = np.round(at_val, decimals=8)
                                    at_val = np.unique(at_val)
                                elif at_.specifier == specifiers.CURRENT_DENSITY:
                                    at_val = np.round(at_val, decimals=0)
                                    at_val = np.unique(at_val)

                                if "at_vals" in plot_spec:
                                    at_val = plot_spec["at_vals"][i]
                                    if not isinstance(at_val, list):
                                        at_val = [at_val]

                                at_vals.append(at_val)

                            units = []
                            for i, at_ in enumerate(at_specifier):
                                units.append(at_.get_tex_unit(scale=at_scale[i]))

                            f = []
                            if len(at_specifier) == 1:
                                for point in at_vals[0]:
                                    f.append((point,))
                            elif len(at_specifier) == 2:
                                f = [(x, y) for x in at_vals[0] for y in at_vals[1]]
                            else:
                                raise IOError("at with more than two specifiers not implemented.")

                            for point in f:
                                df_filter = True
                                at_str = r"$"
                                for i, (speci, u, scale_) in enumerate(
                                    zip(at_specifier, units, at_scale)
                                ):
                                    df_filter = np.logical_and(
                                        df_filter, np.isclose(df[speci], point[i], rtol=1e-3)
                                    )
                                    if at_str != r"$":
                                        at_str += r",\,"
                                    if plot_spec["no_at"]:
                                        at_str += r"{0:1.2f}".format(point[i] * scale_) + u
                                    else:
                                        at_str += (
                                            speci.to_tex()
                                            + r" = {0:1.2f}".format(point[i] * scale_)
                                            + u
                                        )

                                at_str += r"$"
                                df_tmp = df[df_filter]
                                x = df_tmp[quantity_x].to_numpy()
                                y = df_tmp[quantity_y].to_numpy()

                                # device if legend is wanted...default yes
                                kwargs = {}
                                if plot_spec["legend"]:
                                    kwargs["label"] = at_str

                                plt.add_data_set(
                                    x,
                                    y,
                                    **kwargs,
                                )

                                # add dots at peak ft
                                if "mark_ft" in plot_type:
                                    ft = df_tmp[specifiers.TRANSIT_FREQUENCY].to_numpy() * 1e-9
                                    interp_fun_ft = interpolate.interp1d(x, ft)
                                    interp_fun_ic = interpolate.interp1d(x, y)

                                    index_peak_ft = np.argmax(ft)
                                    try:
                                        vbe_new = np.linspace(
                                            x[index_peak_ft - 10], x[index_peak_ft + 10], 201
                                        )  # may error
                                    except IndexError:
                                        vbe_new = np.linspace(
                                            x[index_peak_ft - 10], x[-1], 201
                                        )  # may error

                                    index_peak_ft = np.argmax(interp_fun_ft(vbe_new))

                                    vbe_peak = vbe_new[index_peak_ft]
                                    jc_peak = interp_fun_ic(vbe_new[index_peak_ft])
                                    vbc_peak = point

                                    plt.add_data_set(
                                        np.tile(np.array(vbe_peak), 5),
                                        np.tile(np.array(jc_peak), 5),
                                        style=" ök",  # black dots
                                    )
                                    peaks["vbe"].append(np.tile(vbe_peak, 10))
                                    peaks["jc"].append(np.tile(jc_peak, 10))
                                    peaks["vbc"].append(np.tile(point[0], 10))

                                n = n + 1

                            if "ymin" in plot_spec.keys() or "ymax" in plot_spec.keys():
                                if not "ymin" in plot_spec.keys():
                                    plot_spec["ymin"] = None
                                if not "ymax" in plot_spec.keys():
                                    plot_spec["ymax"] = None
                                plt.y_limits = (plot_spec["ymin"], plot_spec["ymax"])

                            else:
                                try:
                                    plt.y_limits = plot_defaults[plot_type]["y_limits"]
                                except KeyError:
                                    pass

                            if "xmin" in plot_spec.keys() or "xmax" in plot_spec.keys():
                                if not "xmin" in plot_spec.keys():
                                    plot_spec["xmin"] = None
                                if not "xmax" in plot_spec.keys():
                                    plot_spec["xmax"] = None
                                plt.x_limits = (plot_spec["xmin"], plot_spec["xmax"])

                            else:
                                try:
                                    plt.x_limits = plot_defaults[plot_type]["x_limits"]
                                except KeyError:
                                    pass

                    # plots that required to mark peak of ft are accounted for here.
                    if plot_type == "gummel_vbc_mark_ft":
                        dut.peaks = peaks
                    elif plot_type == "output_ib":  # add ft peaks if they exist
                        try:
                            peaks = dut.peaks
                            jc = np.array(peaks["jc"]).flatten()
                            vbe = np.array(peaks["vbe"]).flatten()
                            vbc = np.array(peaks["vbc"]).flatten()
                            vce = vbe - vbc

                            inds = vce.argsort()
                            plt.add_data_set(
                                vce[inds],
                                jc[inds],
                                style="-ök",  # black dots
                            )
                        except AttributeError:
                            pass

                    print(
                        "...finished plot of type "
                        + plot_type
                        + " for dut "
                        + dut.name
                        + " , found "
                        + str(n)
                        + " lines."
                    )

                    if n == 0:
                        print("Found no lines for plot " + plot_type + " .")
                    else:
                        plts.append(plt)

        if show:
            if len(plts) > 1:
                for plt in plts[:-1]:
                    plt.plot_py(show=False)

            plts[-1].plot_py(show=True)

        base_path = os.path.join(output_settings.pop("base_path"))
        for plt in plts:
            plot_path = os.path.join(base_path, "figs", plt.dut_name)
            try:
                os.mkdir(plot_path)
            except FileExistsError:
                pass

            plot_path = os.path.join(base_path, "figs", plt.dut_name, "T" + str(plt.temp) + "K")
            try:
                os.mkdir(plot_path)
            except FileExistsError:
                pass

            plot_path = os.path.join(
                base_path, "figs", plt.dut_name, "T" + str(plt.temp) + "K", plt.plot_type
            )
            if plt.plot_type == "tj_jc_at_vbc":
                plot_path = os.path.join(
                    base_path,
                    "figs",
                    plt.dut_name,
                    "T" + str(plt.temp) + "K",
                    plt.plot_type + "rth_" + "{0:1.1f}".format(plt.dut.rth * 1e-3) + "kWperK",
                )
            if os.path.exists(plot_path):
                shutil.rmtree(plot_path)
            os.mkdir(plot_path)

            # special output from plot_spec
            output_settings_tmp = copy.deepcopy(output_settings)
            for special in ["width", "height"]:
                try:
                    output_settings_tmp[special] = plt.plot_spec[special]
                except KeyError:
                    continue

            try:
                output_settings_tmp.pop("create_doc")
            except KeyError:
                pass

            plt.legend_location = "upper right outer"
            filename = plt.save_tikz(plot_path, **output_settings_tmp)

            plt.path = os.path.join(plot_path, filename.replace("tex", "pdf"))

        destination = os.path.join(base_path, "doc_pdf")
        if output_settings["create_doc"]:
            dir_source = DATA_CONFIG["directories"]["libautodoc"]

            os.makedirs(destination, exist_ok=True)

            recursive_copy(dir_source, destination)

            try:
                # now rename _x_title and _author
                with open(
                    os.path.join(destination, "content", "deckblatt.tex"), "r", encoding="utf-8"
                ) as deckblatt:
                    string_deckblatt = deckblatt.read()

                string_deckblatt = string_deckblatt.replace("_author", DATA_CONFIG["user_name"])
                string_deckblatt = string_deckblatt.replace(
                    "_x_title", str("B11").replace("_", r"\_")
                )
                string_deckblatt = string_deckblatt.replace(
                    "_wafer", str(self.wafer).replace("_", r"\_")
                )
                string_deckblatt = string_deckblatt.replace(
                    "_date_TO", str(self.date_tapeout).replace("_", r"\_")
                )
                string_deckblatt = string_deckblatt.replace(
                    "_date_received", str(self.date_received).replace("_", r"\_")
                )

                with open(
                    os.path.join(destination, "content", "deckblatt.tex"), "w", encoding="utf-8"
                ) as deckblatt:
                    deckblatt.write(string_deckblatt)
            except FileNotFoundError:
                pass

            # finish copy template

            doc_path = os.path.join(base_path, "doc_pdf")
            try:
                os.mkdir(doc_path)
            except FileExistsError:
                pass

            # subfile that contains overview of library
            lib_tex = SubFile(master="../documentation.tex")
            lib_tex.append(self.toTex())

            # subfile that contains all plots
            plots_tex = SubFile(master="../documentation.tex")
            doc = Tex()
            for dut in duts:
                with doc.create(Section(dut.name)):
                    plts_for_this_dut = []
                    for plt in plts:
                        if plt.dut == dut:
                            plts_for_this_dut.append(plt)

                    temps = []
                    for plt in plts_for_this_dut:
                        temps.append(plt.temp)

                    temps = list(set(temps))

                    for temp in temps:
                        with doc.create(Subsection("T=" + str(temp) + "K")):
                            for plt in plts_for_this_dut:
                                if plt.temp == temp:
                                    # check if plot exists
                                    if os.path.isfile(plt.path):
                                        doc.append(NoEscape(r"\FloatBarrier "))
                                        with doc.create(Figure(position="ht!")) as _plot:
                                            _plot.append(
                                                NoEscape(r"\setlength\figurewidth{\textwidth}")
                                            )
                                            # _plot.append(CommandInput(arguments=Arguments(plt.path)))
                                            # \includegraphics[scale=0.65]{screenshot.png}
                                            _plot.add_image('"' + plt.path + '"')
                                            _plot.add_caption(
                                                NoEscape(
                                                    plot_defaults[dut.dut_type][plt.plot_type][
                                                        "tex"
                                                    ]
                                                )
                                            )
                                            # _plot.append(CommandLabel(arguments=Arguments(fig_name)))

                                        doc.append(NoEscape(r"\FloatBarrier "))

            # put into subfile
            plots_tex.append(doc)

            # doc.generate_tex(os.path.join(doc_path, r'libdoc'))
            lib_tex.generate_tex(os.path.join(destination, "content", "lib_overview"))
            plots_tex.generate_tex(os.path.join(destination, "content", "lib_plots"))


@delayed
def _read_dut_folder(dut, path, force, temperature_converter, **kwargs):
    """Reads all files inside this path for the given dut. Returns the read dictionary.

    Parameter
    -----------
    dut : DutView
    path : str
    force : bool
    temperature_converter : callable or None
    **kwargs
        Passed to DutView.add_data

    Returns
    -------
    dut.data : {key: DMT.DataFrame}
    """
    if not force:
        dut.load_db()
    for root, _dirs, files in os.walk(path):
        for name in files:
            # get extension name and cast to lower case
            extension = name.split(".")[-1]
            extension = extension.lower()
            if (
                (extension == "mdm")
                or (extension == "elpa")
                or (extension == "csv")
                or (extension == "feather")
            ):
                path_root = Path(root)
                # cut the everything before dut lvl and split the path into groups
                key_list = path_root.relative_to(path).parts
                # join the groups together into a valid dut_data key
                key = dut.join_key_temperature(
                    *key_list, name.split(".")[0], temperature_converter=temperature_converter
                )
                dut.add_data(path_root / name, key, force, **kwargs)

    return dut.data
