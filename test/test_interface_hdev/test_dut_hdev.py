""" test DutHdev
"""
import logging

from DMT.core import DutType, SimCon, constants
from DMT.Hdev import DutHdev
from hdevpy.tools import (
    get_sweep,
    get_hdev_dfs,
    get_default_plot,
)
from hdevpy.devices import n3_hbt
import numpy as np
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=Path(__file__).resolve().parent.parent.parent / "logs" / "test_hdev.log",
    filemode="w",
)


def test_dut_hdev():
    # define a hdev input structure, look into the "n3_hbt" function for details
    # hint: have a look into the n3_hbt function to understand how a 1D HBT is defined in detail! Also check out the Hdev manual https://gitlab.com/metroid120/hdev_simulator
    inp = n3_hbt(
        "1.20", reco=True, tn=True
    )  # tn=True => Energy Transport Simulation, tn=False => Drift-Diffusion simulation

    # Create a DUT using DMT.core.DutHdev, which is used for simulation control
    dut = DutHdev(
        None,
        DutType.npn,
        inp,
        reference_node="E",
    )

    # define an output sweep using the hdevpy function get_sweep
    sweep = get_sweep(vce=[0, 9, 201], vbe=[0.65], ac=False)

    # start simulations
    simcon = SimCon(n_core=4, t_max=460)
    simcon.append_simulation(dut, sweep)
    simcon.run_and_read(force=False)

    # retrieve simulation data for sweep "sweep" => one pandas DataFrame with IV data, one with internal quantities "inqu"
    df_iv, df_inqu = get_hdev_dfs(dut, sweep, index=10)

    # get various data for tests
    ic = df_iv["I_C"].to_numpy()
    ie = df_iv["I_E"].to_numpy()
    ib = df_iv["I_B"].to_numpy()
    vb = df_iv["V_B"].to_numpy()

    n = df_inqu["N"].to_numpy()
    p = df_inqu["P"].to_numpy()
    ec = df_inqu["EC"].to_numpy()
    ev = df_inqu["EV"].to_numpy()
    efn = -df_inqu["PHI|N"].to_numpy()
    efp = -df_inqu["PHI|P"].to_numpy()
    nc = df_inqu["n_eff"].to_numpy()
    nv = df_inqu["p_eff"].to_numpy()
    vt = constants.P_K * df_inqu["TEMP"].to_numpy() / constants.P_Q

    n_dmt = nc * np.exp((efn - ec) / vt)
    p_dmt = nv * np.exp(-(efp - ev) / vt)

    assert np.isclose(vb, 0.65).all()  # output voltage makes sense
    assert np.isclose(ic[50:], -ie[50:] - ib[50:], rtol=1e-2).all()  # global continuity equation
    assert np.isclose(n, n_dmt, rtol=1e-3).all()  # n carrier densities make sense
    assert np.isclose(p, p_dmt, rtol=1e-3).all()  # p carrier densities make sense

    return dut, sweep


if __name__ == "__main__":
    dut, sweep = test_dut_hdev()
