"""Testing Circuit and CircuitElement class."""

from pathlib import Path
from DMT.core import DutView
from DMT.ngspice import DutNgspice


def test_save_load():
    # load an "old" v1.0 DutView
    dut = DutView.load_dut(
        Path(__file__).parent
        / "test_DutView"
        / "ngspice__hash_bd39bbe0c6dee923729248d6a37e3793"
        / "dut.json",
        classes_dut_view=[DutNgspice],
    )

    assert isinstance(dut, DutNgspice)
    assert dut.name == "ngspice_"
    assert dut.get_hash() == "bd39bbe0c6dee923729248d6a37e3793"

    # save it (now it should be v1.1)
    dut.database_dir = Path(__file__).parent.parent / "tmp" / "test_DutView"
    dut.save()

    # load again
    dut_loaded = DutView.load_dut(
        Path(__file__).parent.parent
        / "tmp"
        / "test_DutView"
        / "ngspice__hash_bd39bbe0c6dee923729248d6a37e3793"
        / "dut.json",
        classes_dut_view=[DutNgspice],
    )

    assert isinstance(dut_loaded, DutNgspice)
    assert dut_loaded.name == "ngspice_"
    assert dut_loaded.get_hash() == "bd39bbe0c6dee923729248d6a37e3793"


def test_save_load_dict_copy():
    # load an "old" v1.0 DutView
    dut = DutView.load_dut(
        Path(__file__).parent
        / "test_DutView"
        / "ngspice__hash_bd39bbe0c6dee923729248d6a37e3793"
        / "dut.json",
        classes_dut_view=[DutNgspice],
    )

    assert isinstance(dut, DutNgspice)
    assert dut.name == "ngspice_"
    assert dut.get_hash() == "bd39bbe0c6dee923729248d6a37e3793"

    dut.dict_copy = {
        "datafile.tbl": """
# Table model for a ADS Verilog-AMS model
 # 
 # V_BE V_BC I_C
0.60  0.5 1.516340e-07
0.61  0.5 2.219073e-07
0.62  0.5 3.246847e-07
0.63  0.5 4.749676e-07
0.64  0.5 6.946568e-07
0.65  0.5 1.015714e-06
"""
    }

    # save it (now it should be v1.1)
    dut.database_dir = Path(__file__).parent.parent / "tmp" / "test_DutView_dict_copy"
    dut.save()

    # load again
    dut_loaded = DutView.load_dut(
        Path(__file__).parent.parent
        / "tmp"
        / "test_DutView_dict_copy"
        / "ngspice__hash_51302945514628b28b5ebf4525e230a2"
        / "dut.json",
        classes_dut_view=[DutNgspice],
    )
    # DMT_core/test/tmp/test_DutView_dict_copy/ngspice__hash_51302945514628b28b5ebf4525e230a2/dut.json

    assert isinstance(dut_loaded, DutNgspice)
    assert dut_loaded.name == "ngspice_"
    assert dut_loaded.get_hash() == "51302945514628b28b5ebf4525e230a2"


if __name__ == "__main__":
    test_save_load()
    test_save_load_dict_copy()
