""" Testing the class DMT.core.DutType """

import logging
import os.path

# import pytest
from DMT.core.dut_type import DutType


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=os.path.join("logs", "test_dut_type.log"),
    filemode="w",
)


def test_subtypes():
    """Test if the types are the correct subtypes."""

    assert DutType.device & DutType.transistor
    assert DutType.device & DutType.npn
    assert not DutType.device & DutType.tlm  # a tlm is no device
    assert not DutType.meas_struct & DutType.npn

    assert not DutType.cap & DutType.meas_struct
    assert DutType.cap_ac & DutType.meas_struct

    assert DutType.tlmb & DutType.pn_diode  # !!! WRONG!!
    assert not DutType.tlmb.is_subtype(
        DutType.pn_diode
    )  # USE THIS!! To test for flags and not for special devices!


def test_get_nodes():
    """Tests the get nodes of the flags."""

    assert DutType.tetrode.get_nodes() == ["B1", "B2", "E", "C", "S"]


def test_to_string():
    npn = DutType.deem_open_bjt
    assert str(npn) == "open"


if __name__ == "__main__":
    test_subtypes()
    test_get_nodes()
    test_to_string()
    dummy = 1
