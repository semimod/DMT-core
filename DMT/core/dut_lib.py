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
from pathlib import Path
from joblib import Parallel, delayed
from DMT.core import DutType, print_progress_bar, DutView
from DMT.exceptions import NoOpenDeembeddingDut, NoShortDeembeddingDut

try:
    from pylatex import Section, Subsection, SmallText, Tabular, NoEscape, Center
    from DMT.external.pylatex import Tex
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
            import_dir = Path(import_dir).resolve()

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
            duts.append(dut_filter(str(import_dir)))
            dut_paths.append(import_dir)
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
