import pytest
import pandas as pd
import numpy as np
from DMT.core import Sweep, specifiers
from DMT.core.sweep_def import (
    SweepDef,
    SweepDefConst,
    SweepDefLinear,
    SweepDefLog,
    SweepDefSync,
    SweepDefList,
    SweepDefTransSinus,
    SweepDefTransRamp,
)

sp_temp = specifiers.TEMPERATURE
sp_freq = specifiers.FREQUENCY
sp_ft = specifiers.TRANSIT_FREQUENCY
sp_vb = specifiers.VOLTAGE + "B"
sp_vcb = specifiers.VOLTAGE + ["C", "B"]
sp_vbc = specifiers.VOLTAGE + ["B", "C"]
sp_vc = specifiers.VOLTAGE + "C"
sp_ve = specifiers.VOLTAGE + "E"
sp_ic = specifiers.CURRENT + "C"
sp_ib = specifiers.CURRENT + "B"


def test_dc_sweep():
    # sweeps are defined using a sweep_def
    sweepdef = [
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 1,
            "sweep_type": "LIN",
            "value_def": [0, 1, 11],
        },
        {
            "var_name": specifiers.VOLTAGE + "C",
            "sweep_order": 2,
            "sweep_type": "CON",
            "value_def": [1],
        },
        {
            "var_name": specifiers.VOLTAGE + "E",
            "sweep_order": 3,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    # additional variables that shall be saved in the sweep
    othervar = {"TEMP": 300, "w": 10, "l": 0.25}

    # Sweep as a class, inputs are needed, e.g.
    # name:     dummy-sweep
    # sweepdef: sweepdef defined above related opering points
    # othervar: othervar defined above related T, geometries
    sweep = Sweep("dummy-sweep", sweepdef=sweepdef, othervar=othervar)  # create the Sweep object
    df = (
        sweep.create_df()
    )  # we can also create the sweep's dataframe, where the output variables are Nans.

    df.ensure_specifier_column(sp_vbc)
    assert len(df) == 11
    assert df[sp_vc].round(3).unique() == np.array([1])
    assert np.allclose(df[sp_vb], np.linspace(0, 1, 11))


def test_sync_sweep():

    # VBC = 0.1
    sweepdef = [
        {
            "var_name": sp_vb,
            "sweep_order": 1,
            "sweep_type": "LIN",
            "value_def": [0, 1, 11],
        },
        {
            "var_name": sp_vc,
            "sweep_order": 1,
            "sweep_type": "SYNC",
            "master": sp_vb,
            "offset": 0.1,
        },
        {
            "var_name": sp_ve,
            "sweep_order": 2,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    outputdef = ["I_C", "I_B"]  # define which output variables need to be saved
    othervar = {"TEMP": 300, "w": 10, "l": 0.25}
    sweep = Sweep("dummy_2", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)
    df = sweep.create_df()

    df.ensure_specifier_column(sp_vbc)
    assert len(df) == 11
    assert df[sp_vbc].round(3).unique() == np.array([-0.1])
    assert np.allclose(df[sp_vb], np.linspace(0, 1, 11))
    assert np.allclose(df[sp_vc], np.linspace(0.1, 1.1, 11))

    list_vbc = [0.5, 0.0, -0.5]
    sws_gummel = []
    df_gummel_sep = []
    for vbc in list_vbc:
        sws_gummel.append(
            Sweep(
                f"gummel_vbc_{vbc:.1f}",
                sweepdef=[
                    SweepDefConst(sp_ve, [0], sweep_order=0),
                    SweepDefLinear(sp_vb, [0.8, 1.0, 41], sweep_order=1),
                    SweepDefSync(sp_vc, sp_vb, vbc, sweep_order=1),
                    SweepDefLog(sp_freq, [9, 10, 5], sweep_order=2),
                ],
                outputdef=[],
                othervar={sp_temp: 300},
            )
        )
        df_gummel_sep.append(sws_gummel[-1].create_df())

    df_gummel_sep = pd.concat(df_gummel_sep)

    sw_gummel = Sweep(
        "gummel",
        sweepdef=[
            SweepDefConst(sp_ve, 0, sweep_order=0),
            SweepDefList(sp_vbc, list_vbc, sweep_order=2),
            SweepDefLinear(sp_vb, [0.8, 1.0, 41], sweep_order=2),
            SweepDefSync(sp_vc, sp_vb, sp_vbc, sweep_order=2),
            SweepDefLog(sp_freq, [9, 10, 5], sweep_order=3),
        ],
        outputdef=[],
        othervar={sp_temp: 300},
    )
    df_gummel = sw_gummel.create_df()
    df_gummel.drop(columns=sp_vbc, inplace=True)

    # compare the dataframes -> should be equal
    for row_gummel, row_gummel_sep in zip(df_gummel.iterrows(), df_gummel_sep.iterrows()):
        assert all(row_gummel[1] == row_gummel_sep[1])


def test_ac_sweep():
    # create a sweep with a sweeped offset variable
    sweepdef = [
        {"var_name": sp_freq, "sweep_order": 4, "sweep_type": "LOG", "value_def": [8, 9, 2]},
        {
            "var_name": sp_vb,
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0, 1, 3],
        },
        {
            "var_name": sp_vc,
            "sweep_order": 3,
            "sweep_type": "SYNC",
            "master": sp_vb,
            "offset": sp_vcb,
        },
        {
            "var_name": sp_vcb,
            "sweep_order": 2,
            "sweep_type": "LIST",
            "value_def": [-0, -0.2, -0.3],
        },
        {
            "var_name": sp_ve,
            "sweep_order": 1,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    outputdef = [specifiers.CURRENT + "C", specifiers.CURRENT + "B"]
    othervar = {"TEMP": 300, "w": 10, "l": 0.25}
    sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)
    df = sweep.create_df()

    df.ensure_specifier_column(sp_vbc)
    assert len(df) == 18
    assert np.allclose(df[sp_vbc].round(3).unique(), np.array([0.0, 0.2, 0.3]))
    assert np.allclose(df[sp_vb].round(3).unique(), np.array([0.0, 0.5, 1.0]))
    assert np.allclose(
        df[sp_vc].round(3).unique(), np.array([0.0, 0.5, 1.0, -0.2, 0.3, 0.8, -0.3, 0.2, 0.7])
    )


def test_sweepdef_errors():
    with pytest.raises(IOError):
        SweepDef("asd", "LIN")  # var_name 'asd' can not be converted to specifier

    with pytest.raises(IOError):
        SweepDef("FREQ", "LIN")  # neither master not value_def

    with pytest.raises(IOError):
        SweepDef("FREQ", "LON")  # typo in sweep type

    with pytest.raises(IOError):
        swd = SweepDef("FREQ", "CON", value_def=[0, 1])  # 2 values for constant
        swd.set_values()

    swd = SweepDef("FREQ", "LOG", value_def=[8, 9, 2])
    assert swd.sync is None


def test_sweep_swd():

    swd = SweepDef("FREQ", "LOG", value_def=[8, 9, 2])
    swds = [
        swd,
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 1,
            "sweep_type": "LIN",
            "value_def": [0, 1, 11],
        },
        {
            "var_name": specifiers.VOLTAGE + "C",
            "sweep_order": 2,
            "sweep_type": "CON",
            "value_def": [1],
        },
        {
            "var_name": specifiers.VOLTAGE + "E",
            "sweep_order": 3,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    with pytest.raises(IOError):  # no temperature
        Sweep("gummel", sweepdef=swds)

    with pytest.raises(IOError):  # 2 temperatures
        Sweep(
            "gummel",
            sweepdef=[
                {"var_name": "TEMP", "sweep_order": 0, "sweep_type": "CON", "value_def": [300]},
            ]
            + swds,
            othervar={"TEMP": 300},
        )

    with pytest.raises(IOError):  # othervar must be a dict
        Sweep("gummel", sweepdef=swds, othervar="TEMP")

    with pytest.raises(IOError):  # outputdef must be a list
        Sweep("gummel", sweepdef=swds, othervar={"TEMP": 300}, outputdef="I_C")

    with pytest.raises(IOError):  # no master sweep
        Sweep(
            "gummel",
            sweepdef=[
                {
                    "var_name": specifiers.VOLTAGE + "B",
                    "sweep_order": 1,
                    "sweep_type": "LIN",
                    "value_def": [0, 1, 11],
                },
                {
                    "var_name": specifiers.VOLTAGE + "C",
                    "sweep_order": 1,
                    "sweep_type": "SYNC",
                    "master": "V_A",
                    "offset": 0.1,
                },
                {
                    "var_name": specifiers.VOLTAGE + "E",
                    "sweep_order": 2,
                    "sweep_type": "CON",
                    "value_def": [0],
                },
            ],
        )

    with pytest.raises(IOError):  # no master sweep
        Sweep(
            "gummel",
            sweepdef=[
                {
                    "var_name": specifiers.VOLTAGE + "B",
                    "sweep_type": "LIN",
                    "value_def": [0, 1, 11],
                },
                {
                    "var_name": specifiers.VOLTAGE + "C",
                    "sweep_type": "SYNC",
                    "master": "V_A",
                    "offset": 0.1,
                },
                {"var_name": specifiers.VOLTAGE + "E", "sweep_type": "CON", "value_def": [0]},
            ],
        )

    sweep = Sweep("gummel", sweepdef=swds, othervar={"TEMP": 300})
    sweep2 = Sweep("gummel", sweepdef=swds, othervar={"TEMP": 300})

    assert sweep == sweep2

    assert sweep != 5


def test_sweep_temp():

    assert Sweep("gummel", sweepdef=[], othervar={"TEMP": 300}).get_temperature() == "T300.00K"

    assert (
        Sweep(
            "gummel",
            sweepdef=[
                {"var_name": "TEMP", "sweep_type": "CON", "value_def": [300]},
            ],
        ).get_temperature()
        == "T300.00K"
    )

    assert (
        Sweep(
            "gummel",
            sweepdef=[
                {"var_name": "TEMP", "sweep_type": "LIN", "value_def": [300, 400, 3]},
            ],
        ).get_temperature()
        == "T[300.00-3.00-400.00]K"
    )

    assert (
        Sweep(
            "gummel",
            sweepdef=[
                {"var_name": "TEMP", "sweep_type": "LIST", "value_def": [300, 320, 350]},
            ],
        ).get_temperature()
        == "T(300.00,320.00,350.00)K"
    )

    with pytest.raises(NotImplementedError):  # log sweep has not string at the moment
        Sweep(
            "gummel",
            sweepdef=[
                {"var_name": "TEMP", "sweep_type": "LOG", "value_def": [2, 4, 10]},
            ],
        ).get_temperature()


def test_tran_sweep():
    col_time = specifiers.TIME
    col_vb = specifiers.VOLTAGE + "B"
    col_vc = specifiers.VOLTAGE + "C"
    col_ve = specifiers.VOLTAGE + "E"
    frequencies = 1e9 * np.array([0.1, 0.5, 1, 2])
    sweep = Sweep(
        "test",
        sweepdef=[
            SweepDefTransSinus(
                value_def=frequencies, amp=25e-3, phase=0, contact="B", sweep_order=2
            ),
            SweepDefSync(col_vc, master=col_vb, offset=0, sweep_order=1),
            SweepDefConst(col_vb, value_def=0.87, sweep_order=1),
            SweepDefConst(col_ve, value_def=0, sweep_order=0),
        ],
        outputdef=["OpVar"],
        othervar={specifiers.TEMPERATURE: 300},
    )
    frame = sweep.create_df()
    frame["signal"] = sweep.sweepdef[3].get_input_signal()

    assert len(frame) == len(frequencies) * 121
    assert all(np.abs(frame["signal"]) <= 0.025)
    # check zero crossings
    assert np.allclose(frame.loc[0:120:20, "signal"], 0.0)
    assert np.allclose(frame.loc[121:241:20, "signal"], 0.0)
    assert np.allclose(frame.loc[242:362:20, "signal"], 0.0)
    assert np.allclose(frame.loc[363:484:20, "signal"], 0.0)

    frequencies = 1e9 * np.array([0.1, 0.5, 1, 2])
    sweep = Sweep(
        "test",
        sweepdef=[
            SweepDefTransRamp(value_def=frequencies, amp=1, phase=0, contact="B", sweep_order=2),
            SweepDefSync(col_vc, master=col_vb, offset=0, sweep_order=1),
            SweepDefConst(col_vb, value_def=0.87, sweep_order=1),
            SweepDefConst(col_ve, value_def=0, sweep_order=0),
        ],
        outputdef=["OpVar"],
        othervar={specifiers.TEMPERATURE: 300},
    )
    frame = sweep.create_df()
    frame["signal"] = sweep.sweepdef[3].get_input_signal()

    assert len(frame) == len(frequencies) * 121
    assert np.allclose(frame.loc[0:363:121, "signal"], 0)
    assert np.allclose(frame.loc[121:484:121, "signal"], 1)


if __name__ == "__main__":
    test_dc_sweep()
    test_sync_sweep()
    test_ac_sweep()
    test_sweepdef_errors()
    test_sweep_swd()
    test_sweep_temp()
    test_tran_sweep()
