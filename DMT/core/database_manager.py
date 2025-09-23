"""Database management

Class which represents all common features in DMT that are used to search, organize and filter data.
Features:

* Can read all relevant file formats produced by simulators used at CEDIC.
* Uses pandas to manage the data internally.
* Allows to "search" and "filter" existing data.

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
import os
import pandas as pd
import warnings
import _pickle as cpickle
from typing import Union
from pathlib import Path
from pyarrow.lib import ArrowInvalid

from DMT.config import DATA_CONFIG
from DMT.core.data_frame import DataFrame
from DMT.core.singleton import Singleton
from DMT.core.naming import SpecifierStr


class DatabaseManager(object, metaclass=Singleton):
    """Class responsible for data management in DMT.

    Methods
    -------
    load_db(db_dir):
        Load a full db from the given path.

    save_db(db_dir, data):
        Save a full db to the given path.

    del_db(db_dir)
        Delete the hole database.

    save_df(df, file_name):
        Save a dataframe as file_name, where file_name is the direct path to the desired file.

    load_df(file_name):
        Loads a DMT dataframe from the file.
    """

    def load_db(self, db_dir):
        """Loads all DMT.DataFrames from the database at db_dir using implicit casting.

        Parameters
        ----------
        db_dir  : str or os.Pathlike
            Path to the database that shall be used to load df.

        Raises
        ------


        Returns
        -------
        data : {key: DataFrame}
            Loaded dataframes
        """
        if not isinstance(db_dir, Path):
            db_dir = Path(db_dir)

        if not db_dir.exists():
            raise FileNotFoundError

        data = {}

        if DATA_CONFIG["useHDF5Store"]:
            try:
                db = pd.io.pytables.HDFStore(
                    str(db_dir.expanduser()), mode="r", complevel=9, complib="zlib"
                )

                keys_db = db.keys()  # sorry :(
                for key in keys_db:
                    df = db.get(key)
                    df.__class__ = DataFrame  # cast to DMT.DataFrame
                    key = key[1:]  # remove starting '/'

                    # cast back
                    dict_reconvert = {}
                    for col in df.columns:
                        dict_reconvert[col] = SpecifierStr.string_from_load(col)

                    df.rename(columns=dict_reconvert, inplace=True)
                    # prevent invisible column bug:
                    df = df.loc[:, ~df.columns.duplicated()]
                    if not df.columns.is_unique:
                        raise IOError()

                    data[key] = df
                db.close()
            except (OSError, RuntimeError):
                with db_dir.open(mode="rb") as my_db:
                    data = cpickle.load(my_db)

        else:
            with db_dir.open(mode="rb") as my_db:
                data = cpickle.load(my_db)

        # cast back
        for key, df in data.items():
            if isinstance(df, pd.DataFrame):
                df.__class__ = DataFrame

        return data

    def save_db(self, db_dir, data):
        """Save the complete data into the database of dut. The old database is overwritten!

        Parameters
        ----------
        db_dir   :  str or os.Pathlike
            Path to the database that shall be used to save the data.
        data     :  {key: DataFrame}
            Dataframes to save
        """
        if not isinstance(db_dir, Path):
            db_dir = Path(db_dir)

        # create all directories until database
        db_dir.parent.mkdir(parents=True, exist_ok=True)

        # convert to usual pandas dataframe
        try:
            for key, df in data.items():
                if isinstance(df, DataFrame):
                    df.__class__ = pd.DataFrame
                elif isinstance(df, pd.DataFrame):
                    pass
                else:
                    raise TypeError("Only DMT.core.DataFrame can be converted to pandas.DataFrame!")
        except TypeError:
            # if it is not a DataFrame, just directly dump it.
            with db_dir.open(mode="wb") as my_db:
                cpickle.dump(data, my_db)

            return

        if DATA_CONFIG["useHDF5Store"]:
            db = pd.io.pytables.HDFStore(
                str(db_dir.expanduser()), mode="w", complevel=9, complib="zlib"
            )  # file is created if it does not exist
            for key, df in data.items():
                # cast to unique string
                dict_convert = {}
                dict_reconvert = {}
                for col in df.columns:
                    try:
                        dict_convert[col] = col.string_to_save()
                        dict_reconvert[col.string_to_save()] = col
                    except AttributeError:
                        pass
                df = df.rename(columns=dict_convert)

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    db.put(key, df)

                df = df.rename(columns=dict_reconvert)
            db.close()
        else:
            with db_dir.open(mode="wb") as my_db:
                cpickle.dump(data, my_db)

        # convert back
        for key, df in data.items():
            df.__class__ = DataFrame

    def del_db(self, db_dir):
        """Delete the database file for a dut.

        Parameters
        ----------
        db_dir   :  string or os.Pathlike
            Full path to the database.
        """
        if not isinstance(db_dir, Path):
            db_dir = Path(db_dir)

        db_dir.unlink(missing_ok=True)

    def save_df(
        self,
        df: Union[DataFrame, pd.DataFrame],
        file_name: Union[str, os.PathLike],
        version=2,
        compression="lz4",
        **kwargs
    ):
        """Save the data stored in df as file_name, where file_name is the direct path to the file.

        Parameters
        ----------
        df  :  DMT.core.DataFrame
            A dataframe object that shall be saved.
        file_name  :  str or os.Pathlike
            Direct path to the file
        """
        df.to_feather(file_name, version=version, compression=compression, **kwargs)

    def load_df(self, file_name: Union[str, os.PathLike], to_specifier=True):
        """Load the data stored in file_name, where file_name is the direct path to the file.

        Parameters
        ----------
        file_name  :  str
            Direct path to the file
        to_specifier : bool
            If True, the column names are cast to specifiers. Only neeeded for feather files. Default is True.

        Returns
        -------
        df  :  DMT.core.DataFrame
            Loaded dataframe object.
        """
        try:
            df = DataFrame.from_feather(file_name, to_specifier=to_specifier)
        except ArrowInvalid:
            df = pd.read_pickle(str(file_name))
            df.__class__ = DataFrame
        return df
