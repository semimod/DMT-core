import numpy as np
from pathlib import Path
from DMT.core import read_data, DataFrame, specifiers, sub_specifiers


def test_clean_data():
    data = read_data(Path(__file__).resolve().parent / "test_data" / "dummy_open_freq.mdm")
    data_clean = data.clean_data(nodes=["B", "E", "C"], reference_node="E", ac_ports=["B", "C"])
    return data_clean


def test_clean_data_potentials():
    # create a simple df that has only voltages
    df = DataFrame()
    vbe = np.linspace(0, 1, 101)
    vce = np.linspace(0, 1, 101)
    df[specifiers.VOLTAGE + "B" + "E"] = vbe
    df[specifiers.VOLTAGE + "C" + "E"] = vce
    df = df.clean_data(nodes=["B", "E", "C"], reference_node="E")
    print(df.columns)
    assert specifiers.VOLTAGE + "B" in df.columns
    assert specifiers.VOLTAGE + "C" in df.columns
    assert specifiers.VOLTAGE + "E" in df.columns
    assert specifiers.VOLTAGE + "B" + "E" not in df.columns
    assert specifiers.VOLTAGE + "C" + "E" not in df.columns


def test_clean_data_potential_mix():
    # create a simple df that has only voltages
    df = DataFrame()
    vbe = np.linspace(0, 1, 101)
    vce = np.linspace(0, 1, 101)
    df[specifiers.VOLTAGE + "B" + "E"] = vbe
    df[specifiers.VOLTAGE + "C"] = vce
    df = df.clean_data(nodes=["B", "E", "C"], reference_node="E")
    print(df.columns)
    assert specifiers.VOLTAGE + "B" in df.columns
    assert specifiers.VOLTAGE + "C" in df.columns
    assert specifiers.VOLTAGE + "E" in df.columns
    assert specifiers.VOLTAGE + "B" + "E" not in df.columns
    assert specifiers.VOLTAGE + "C" + "E" not in df.columns


def test_clean_data_potential_mix_2():
    # create a simple df that has only voltages
    df = DataFrame()
    vbe = np.linspace(0, 1, 101)
    vce = np.linspace(0, 1, 101)
    df[specifiers.VOLTAGE + "B"] = vbe
    df[specifiers.VOLTAGE + "C"] = vce
    df = df.clean_data(nodes=["B", "E", "C"], reference_node="E")
    print(df.columns)
    assert specifiers.VOLTAGE + "B" in df.columns
    assert specifiers.VOLTAGE + "C" in df.columns
    assert specifiers.VOLTAGE + "E" in df.columns
    assert specifiers.VOLTAGE + "B" + "E" not in df.columns
    assert specifiers.VOLTAGE + "C" + "E" not in df.columns


def test_clean_data_potential_mix_3():
    # create a simple df that has only voltages
    df = DataFrame()
    vbe = np.linspace(0, 1, 101)
    vce = np.linspace(0, 1, 101)
    df[specifiers.VOLTAGE + "B"] = vbe
    df[specifiers.VOLTAGE + "B" + "C"] = vce
    df = df.clean_data(nodes=["B", "E", "C"], reference_node="E")
    print(df.columns)
    assert specifiers.VOLTAGE + "B" in df.columns
    assert specifiers.VOLTAGE + "C" in df.columns
    assert specifiers.VOLTAGE + "E" in df.columns
    assert specifiers.VOLTAGE + "B" + "E" not in df.columns
    assert specifiers.VOLTAGE + "C" + "E" not in df.columns


def test_clean_data_throw_error():
    # create a simple df that has only voltages
    df = DataFrame()
    vbe = np.linspace(0, 1, 101)
    vce = np.linspace(0, 1, 101)
    df[specifiers.VOLTAGE + "B" + "E" + "FORCED"] = vbe
    df[specifiers.VOLTAGE + "B" + "E"] = vbe
    df[specifiers.VOLTAGE + "C" + "E" + "FORCED"] = vbe
    df[specifiers.VOLTAGE + "C" + "E"] = vbe
    df = df.clean_data(nodes=["B", "E", "C"], reference_node="E")
    print(df.columns)
    assert specifiers.VOLTAGE + "B" in df.columns
    assert specifiers.VOLTAGE + "C" in df.columns
    assert specifiers.VOLTAGE + "E" in df.columns
    assert specifiers.VOLTAGE + "B" + "E" not in df.columns
    assert specifiers.VOLTAGE + "B" + "E" + "FORCED" not in df.columns
    assert specifiers.VOLTAGE + "C" + "E" not in df.columns
    assert specifiers.VOLTAGE + "C" + "E" + "FORCED" not in df.columns


if __name__ == "__main__":
    data_clean = test_clean_data()
    test_clean_data_potentials()
    test_clean_data_potential_mix()
    test_clean_data_potential_mix_2()
    test_clean_data_potential_mix_3()
    test_clean_data_throw_error()

    # print(data_clean['S_BB'].to_numpy())
