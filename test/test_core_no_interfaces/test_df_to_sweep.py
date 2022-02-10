import os.path
import numpy as np
import pytest
from pathlib import Path
from DMT.core import specifiers, sub_specifiers, read_elpa, read_mdm
from DMT.core.df_to_sweep import df_to_sweep


def test_errors():
    df_elpa = read_elpa(Path(__file__).parent / "HBT_vbc.elpa")

    with pytest.raises(
        IOError
    ):  # sweep is created from forced potentials -> df_elpa has no forced potential..
        _sweep = df_to_sweep(df_elpa)

    df_elpa[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_elpa["VCE"]

    with pytest.raises(
        IOError
    ):  # sweeps need an entry point for the sweep tree -> potential with single value for all ops...
        _sweep = df_to_sweep(df_elpa)


def test_convert_elpa():
    col_vbe = specifiers.VOLTAGE + ["B", "E"] + sub_specifiers.FORCED
    col_vce = specifiers.VOLTAGE + ["C", "E"] + sub_specifiers.FORCED
    col_vbc = specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED

    df_elpa = read_elpa(Path(__file__).parent / "HBT_vbc.elpa")
    # df_elpa.append(read_elpa(Path(__file__).parent / 'HBT_vbc_s.elpa'))
    # df_elpa.sort_values(by=['VBC','VBE'], inplace=True)

    df_elpa[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_elpa["VBE"] * 0
    df_elpa[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_elpa["VCE"]

    sweep = df_to_sweep(df_elpa)

    assert sweep.get_hash() == "df108d8bbd3b4ef51e27b83590361a3e"
    df_sweep = sweep.create_df()

    df_elpa.ensure_specifier_column(col_vbe)
    df_elpa.ensure_specifier_column(col_vbc)
    df_elpa.ensure_specifier_column(col_vce)
    df_sweep.ensure_specifier_column(col_vbe)
    df_sweep.ensure_specifier_column(col_vbc)
    df_sweep.ensure_specifier_column(col_vce)
    assert df_elpa.shape[0] == df_sweep.shape[0]
    assert all(
        [
            np.isclose(vbe_elpa, vbe_sweep)
            for (vbe_elpa, vbe_sweep) in zip(sorted(df_elpa[col_vbe]), sorted(df_sweep[col_vbe]))
        ]
    )
    assert all(
        [
            np.isclose(vce_elpa, vce_sweep)
            for (vce_elpa, vce_sweep) in zip(sorted(df_elpa[col_vce]), sorted(df_sweep[col_vce]))
        ]
    )
    assert all(
        [
            np.isclose(vbc_elpa, vbc_sweep)
            for (vbc_elpa, vbc_sweep) in zip(sorted(df_elpa[col_vbc]), sorted(df_sweep[col_vbc]))
        ]
    )

    df_elpa = read_elpa(Path(__file__).parent / "HBT_vce.elpa")
    # df_elpa.append(read_elpa(Path(__file__).parent /'HBT_vce_s.elpa'))
    # df_elpa.sort_values(by=['VCE','VBE'], inplace=True)

    df_elpa[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_elpa["VBE"] * 0
    df_elpa[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_elpa["VCE"]

    sweep = df_to_sweep(df_elpa)

    assert sweep.get_hash() == "c84094081366be34f588e72182118358"
    df_sweep = sweep.create_df()

    df_elpa.ensure_specifier_column(col_vbe)
    df_elpa.ensure_specifier_column(col_vbc)
    df_elpa.ensure_specifier_column(col_vce)
    df_sweep.ensure_specifier_column(col_vbe)
    df_sweep.ensure_specifier_column(col_vbc)
    df_sweep.ensure_specifier_column(col_vce)
    assert df_elpa.shape[0] == df_sweep.shape[0]
    assert all(
        [
            np.isclose(vbe_elpa, vbe_sweep)
            for (vbe_elpa, vbe_sweep) in zip(sorted(df_elpa[col_vbe]), sorted(df_sweep[col_vbe]))
        ]
    )
    assert all(
        [
            np.isclose(vbc_elpa, vbc_sweep)
            for (vbc_elpa, vbc_sweep) in zip(sorted(df_elpa[col_vbc]), sorted(df_sweep[col_vbc]))
        ]
    )
    assert all(
        [
            np.isclose(vce_elpa, vce_sweep)
            for (vce_elpa, vce_sweep) in zip(sorted(df_elpa[col_vce]), sorted(df_sweep[col_vce]))
        ]
    )


def test_convert_mdm():
    col_vbe = specifiers.VOLTAGE + ["B", "E"] + sub_specifiers.FORCED
    col_vce = specifiers.VOLTAGE + ["C", "E"] + sub_specifiers.FORCED
    col_vbc = specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED
    # load test measurements
    df_mdm = read_mdm(Path(__file__).parent / "test_data" / "Spar_vb.mdm")

    # correct data format of measurements
    nodes = ["B", "C", "E", "S"]
    df_mdm = df_mdm.clean_data(
        nodes,
        "E",
        fallback={
            "S_DEEMB(1,1)": None,
            "S_DEEMB(2,1)": None,
            "S_DEEMB(1,2)": None,
            "S_DEEMB(2,2)": None,
        },
        ac_ports=["B", "C"],
    )
    df_mdm[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_mdm[specifiers.VOLTAGE + "B"]
    df_mdm[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_mdm[specifiers.VOLTAGE + "E"]
    df_mdm[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_mdm[specifiers.VOLTAGE + "C"]

    sweep = df_to_sweep(df_mdm)

    assert sweep.get_hash() == "0c0ac0e5994bbb315bee8912f2a1f278"
    df_sweep = sweep.create_df()

    df_mdm.ensure_specifier_column(col_vbe)
    df_mdm.ensure_specifier_column(col_vbc)
    df_mdm.ensure_specifier_column(col_vce)
    df_sweep.ensure_specifier_column(col_vbe)
    df_sweep.ensure_specifier_column(col_vbc)
    df_sweep.ensure_specifier_column(col_vce)

    assert df_mdm.shape[0] == df_sweep.shape[0]
    assert all(
        [
            np.isclose(vbe_mdm, vbe_sweep)
            for (vbe_mdm, vbe_sweep) in zip(sorted(df_mdm[col_vbe]), sorted(df_sweep[col_vbe]))
        ]
    )
    assert all(
        [
            np.isclose(vbc_mdm, vbc_sweep)
            for (vbc_mdm, vbc_sweep) in zip(sorted(df_mdm[col_vbc]), sorted(df_sweep[col_vbc]))
        ]
    )
    assert all(
        [
            np.isclose(vce_mdm, vce_sweep)
            for (vce_mdm, vce_sweep) in zip(sorted(df_mdm[col_vce]), sorted(df_sweep[col_vce]))
        ]
    )
    assert all(
        [
            np.isclose(freq_mdm, freq_sweep)
            for (freq_mdm, freq_sweep) in zip(
                sorted(df_mdm[specifiers.FREQUENCY]), sorted(df_sweep[specifiers.FREQUENCY])
            )
        ]
    )


if __name__ == "__main__":
    test_errors()
    test_convert_elpa()
    test_convert_mdm()
