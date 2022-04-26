import os
from pathlib import Path
from DMT.core import Sweep
from DMT.core import DutDummy
from DMT.core import SimCon
from DMT.core import DutType
from DMT.core import specifiers
from DMT.core import MCard


folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent


def test_run_sim():
    """Creates a sweep and a dummy dut to run using the simulation controller."""
    sim_con = SimCon(n_core=4, t_max=5)

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
    othervar = {"TEMP": 300, "w": 10, "l": 0.25}
    sweep = Sweep("test_sweep", sweepdef=sweepdef, othervar=othervar)

    mcard = MCard(["A"], "Q_HIC", "hicuml2va", va_file=folder_path / "hicumL2V2p4p0_release.va")
    mcard.load_model_parameters(
        folder_path / "test_modelcards" / "IHP_ECE704_03_para_D21.mat",
    )

    dut = DutDummy(
        test_path, "dummy", DutType.npn, mcard, nodes=None, reference_node="E", force=True
    )

    for _i in range(10):
        sim_con.append_simulation(dut, sweep)

    sim_con.run_and_read(force=True)

    (test_path / "iv.p").unlink()


if __name__ == "__main__":
    test_run_sim()
    dummy = 1
