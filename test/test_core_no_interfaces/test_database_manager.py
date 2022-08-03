""" Testing the database manager
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from DMT.config import DATA_CONFIG
from DMT.core import read_data, DataFrame, DatabaseManager

folder_path = Path(__file__).resolve().parent


def test_data_save_load_df():
    db_manager = DatabaseManager()

    df = read_data(folder_path / "test_data" / "Spar_vb.mdm")

    path_tmp = "test/tmp/db_manager/df.p"
    db_manager.save_df(df, path_tmp)

    df_load = db_manager.load_df(path_tmp)

    assert np.all(np.isclose(df_load["vbe"], df["vbe"]))

    db_manager.del_db(path_tmp)


def test_data_save_load_db_hdf():
    temp = DATA_CONFIG["useHDF5Store"]
    DATA_CONFIG["useHDF5Store"] = True
    db_manager = DatabaseManager()

    df_0 = read_data(folder_path / "test_data" / "Spar_vb.mdm")
    df_1 = read_data(folder_path / "test_data" / "Spar_vb.mdm")
    df_2 = read_data(folder_path / "test_data" / "Spar_vb.mdm")

    # need to clean for db save and load
    nodes = ["B", "C", "E", "S"]
    df_0 = df_0.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )
    df_1 = df_1.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )
    df_2 = df_2.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )

    db = {
        "df_0": df_0,
        "df_1": df_1,
        "df_2": df_2,
    }

    path_tmp = "test/tmp/db_manager/df.hdf"
    db_manager.save_db(path_tmp, db)

    db_load = db_manager.load_db(path_tmp)

    assert np.all(np.isclose(db["df_0"]["V_B"], db_load["df_0"]["V_B"]))

    db_manager.del_db(path_tmp)
    DATA_CONFIG["useHDF5Store"] = temp


def test_data_save_load_db_pickle():
    temp = DATA_CONFIG["useHDF5Store"]
    DATA_CONFIG["useHDF5Store"] = False
    db_manager = DatabaseManager()

    df_0 = read_data(folder_path / "test_data" / "Spar_vb.mdm")
    df_1 = read_data(folder_path / "test_data" / "Spar_vb.mdm")
    df_2 = read_data(folder_path / "test_data" / "Spar_vb.mdm")

    # need to clean for db save and load
    nodes = ["B", "C", "E", "S"]
    df_0 = df_0.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )
    df_1 = df_1.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )
    df_2 = df_2.clean_data(
        nodes,
        "E",
        fallback={
            "S_deemb(1,1)": None,
            "S_deemb(2,1)": None,
            "S_deemb(1,2)": None,
            "S_deemb(2,2)": None,
        },
        ac_ports=["B", "C"],
    )

    db = {
        "df_0": df_0,
        "df_1": df_1,
        "df_2": df_2,
    }

    path_tmp = "test/tmp/db_manager/df.p"
    db_manager.save_db(path_tmp, db)

    db_load = db_manager.load_db(path_tmp)

    assert np.all(np.isclose(db["df_0"]["V_B"], db_load["df_0"]["V_B"]))

    db_manager.del_db(path_tmp)
    DATA_CONFIG["useHDF5Store"] = temp


def test_errors():
    # some errors
    db_manager = DatabaseManager()

    with pytest.raises(FileNotFoundError):
        db_manager.load_db("test/tmp/db_manager/not_there.hdf")


def test_alternatives():
    # no dict of dataframes : just pickle it!
    path_tmp = "test/tmp/db_manager/df.hdf"
    db_manager = DatabaseManager()
    db_manager.save_db(path_tmp, {"a": 5})
    dict_test = db_manager.load_db(path_tmp)
    assert dict_test["a"] == 5


def test_pd_frames():
    path_tmp = "test/tmp/db_manager/df.hdf"
    db_manager = DatabaseManager()
    df_0 = read_data(folder_path / "test_data" / "Spar_vb.mdm")
    df_0.__class__ = pd.DataFrame
    db = {"df_0": df_0}

    db_manager.save_db(path_tmp, db)

    assert db["df_0"].__class__ == DataFrame  # side effect :(

    db_load = db_manager.load_db(path_tmp)

    assert db_load["df_0"].__class__ == DataFrame


if __name__ == "__main__":
    test_data_save_load_df()
    test_data_save_load_db_hdf()
    test_data_save_load_db_pickle()
    test_errors()
    test_alternatives()
    test_pd_frames()
