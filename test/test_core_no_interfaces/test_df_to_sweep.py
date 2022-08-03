import numpy as np
import pytest
from pathlib import Path
from DMT.core import specifiers, sub_specifiers, read_elpa, read_mdm, Sweep, get_sweepdef

folder_path = Path(__file__).resolve().parent


def test_errors():
    df_elpa = read_elpa(folder_path / "HBT_vbc.elpa")

    with pytest.raises(IOError):  # sweep is tried created from 2 forced currents
        _sweep = get_sweepdef(
            df_elpa,
            inner_sweep_voltage=specifiers.CURRENT + "B",
            outer_sweep_voltage=specifiers.CURRENT + "C",
        )

    df_elpa[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_elpa["VCE"]

    with pytest.raises(
        IOError
    ):  # sweeps need an entry point for the sweep tree -> potential with single value for all ops...
        _sweep = get_sweepdef(df_elpa)


def test_convert_elpa():
    col_vbe = specifiers.VOLTAGE + ["B", "E"]
    col_vce = specifiers.VOLTAGE + ["C", "E"]
    col_vbc = specifiers.VOLTAGE + ["B", "C"]
    col_vbe_forced = specifiers.VOLTAGE + ["B", "E"] + sub_specifiers.FORCED
    col_vce_forced = specifiers.VOLTAGE + ["C", "E"] + sub_specifiers.FORCED
    col_vbc_forced = specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED

    df_elpa = read_elpa(folder_path / "HBT_vbc.elpa")

    df_elpa[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_elpa["VBE"] * 0
    df_elpa[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_elpa["VCE"]

    sweep = Sweep.get_sweep_from_dataframe(df_elpa, temperature=300.0)

    df_sweep = sweep.create_df()

    df_elpa.ensure_specifier_column(col_vbe_forced)
    df_elpa.ensure_specifier_column(col_vbc_forced)
    df_elpa.ensure_specifier_column(col_vce_forced)
    df_sweep.ensure_specifier_column(col_vbe)
    df_sweep.ensure_specifier_column(col_vbc)
    df_sweep.ensure_specifier_column(col_vce)
    assert df_elpa.shape[0] == df_sweep.shape[0]
    assert all(
        [
            np.isclose(vbe_elpa, vbe_sweep)
            for (vbe_elpa, vbe_sweep) in zip(
                sorted(df_elpa[col_vbe_forced]), sorted(df_sweep[col_vbe])
            )
        ]
    )
    assert all(
        [
            np.isclose(vce_elpa, vce_sweep)
            for (vce_elpa, vce_sweep) in zip(
                sorted(df_elpa[col_vce_forced]), sorted(df_sweep[col_vce])
            )
        ]
    )
    assert all(
        [
            np.isclose(vbc_elpa, vbc_sweep)
            for (vbc_elpa, vbc_sweep) in zip(
                sorted(df_elpa[col_vbc_forced]), sorted(df_sweep[col_vbc])
            )
        ]
    )

    df_elpa = read_elpa(folder_path / "HBT_vce.elpa")

    df_elpa[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED] = df_elpa["VBE"]
    df_elpa[specifiers.VOLTAGE + "E" + sub_specifiers.FORCED] = df_elpa["VBE"] * 0
    df_elpa[specifiers.VOLTAGE + "C" + sub_specifiers.FORCED] = df_elpa["VCE"]

    sweep = Sweep.get_sweep_from_dataframe(df_elpa, temperature=300.0)

    df_sweep = sweep.create_df()

    df_elpa.ensure_specifier_column(col_vbe_forced)
    df_elpa.ensure_specifier_column(col_vbc_forced)
    df_elpa.ensure_specifier_column(col_vce_forced)
    df_sweep.ensure_specifier_column(col_vbe)
    df_sweep.ensure_specifier_column(col_vbc)
    df_sweep.ensure_specifier_column(col_vce)
    assert df_elpa.shape[0] == df_sweep.shape[0]
    assert all(
        [
            np.isclose(vbe_elpa, vbe_sweep)
            for (vbe_elpa, vbe_sweep) in zip(
                sorted(df_elpa[col_vbe_forced]), sorted(df_sweep[col_vbe])
            )
        ]
    )
    assert all(
        [
            np.isclose(vbc_elpa, vbc_sweep)
            for (vbc_elpa, vbc_sweep) in zip(
                sorted(df_elpa[col_vbc_forced]), sorted(df_sweep[col_vbc])
            )
        ]
    )
    assert all(
        [
            np.isclose(vce_elpa, vce_sweep)
            for (vce_elpa, vce_sweep) in zip(
                sorted(df_elpa[col_vce_forced]), sorted(df_sweep[col_vce])
            )
        ]
    )


def test_convert_mdm():
    col_vbe = specifiers.VOLTAGE + ["B", "E"]
    col_vce = specifiers.VOLTAGE + ["C", "E"]
    col_vbc = specifiers.VOLTAGE + ["B", "C"]
    col_vbe_forced = specifiers.VOLTAGE + ["B", "E"] + sub_specifiers.FORCED
    col_vce_forced = specifiers.VOLTAGE + ["C", "E"] + sub_specifiers.FORCED
    col_vbc_forced = specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED
    # load test measurements
    df_mdm = read_mdm(folder_path / "test_data" / "Spar_vb.mdm")

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

    sweep = Sweep.get_sweep_from_dataframe(df_mdm, temperature=300.0)

    df_sweep = sweep.create_df()

    df_mdm.ensure_specifier_column(col_vbe_forced)
    df_mdm.ensure_specifier_column(col_vbc_forced)
    df_mdm.ensure_specifier_column(col_vce_forced)
    df_sweep.ensure_specifier_column(col_vbe)
    df_sweep.ensure_specifier_column(col_vbc)
    df_sweep.ensure_specifier_column(col_vce)

    assert df_mdm.shape[0] == df_sweep.shape[0]
    assert all(
        [
            np.isclose(vbe_mdm, vbe_sweep)
            for (vbe_mdm, vbe_sweep) in zip(
                sorted(df_mdm[col_vbe_forced]), sorted(df_sweep[col_vbe])
            )
        ]
    )
    assert all(
        [
            np.isclose(vbc_mdm, vbc_sweep)
            for (vbc_mdm, vbc_sweep) in zip(
                sorted(df_mdm[col_vbc_forced]), sorted(df_sweep[col_vbc])
            )
        ]
    )
    assert all(
        [
            np.isclose(vce_mdm, vce_sweep)
            for (vce_mdm, vce_sweep) in zip(
                sorted(df_mdm[col_vce_forced]), sorted(df_sweep[col_vce])
            )
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
