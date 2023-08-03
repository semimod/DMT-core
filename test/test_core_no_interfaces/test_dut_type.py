""" Testing the class DMT.core.DutType """

import warnings
import logging
from pathlib import Path

# import pytest
from DMT.core.dut_type import DutType

folder_path = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_dut_type.log",
    filemode="w",
)


def test_unique():
    """DuType values should be unique."""
    values = [
        getattr(DutType, dt).value for dt in dir(DutType) if hasattr(getattr(DutType, dt), "value")
    ]

    assert len(values) == len(set(values))


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
    assert DutType.tlmb.is_subtype(DutType.tlm)

    assert DutType.npn.is_subtype(DutType.bjt)
    assert DutType.npn.is_subtype(DutType.transistor)
    assert not DutType.npn.is_subtype(DutType.mos)

    assert DutType.n_mos.is_subtype(DutType.mos)
    assert not DutType.n_mos.is_subtype(DutType.bjt)


def test_get_nodes():
    """Tests the get nodes of the flags."""

    assert DutType.tetrode.get_nodes() == ["B1", "B2", "E", "C", "S"]


def test_to_string():
    npn = DutType.deem_open_bjt
    assert str(npn) == "open-bjt"


def test_serialize():
    assert DutType.tetrode == DutType.deserialize(DutType.tetrode.serialize())
    assert DutType.pin_diode == DutType.deserialize(DutType.pin_diode.serialize())
    assert DutType.tlmbc == DutType.deserialize(DutType.tlmbc.serialize())
    assert DutType.deem_short_bjt == DutType.deserialize(DutType.deem_short_bjt.serialize())
    assert DutType.deem_short_mos == DutType.deserialize(DutType.deem_short_mos.serialize())

    with warnings.catch_warnings(record=True):
        DutType.deserialize(
            {
                "DutType": "DMT.core.dut_type.DutTypeInt",
                "string": "definitily_newer_used_dut_type_name!!",
                "value": -1,
                "nodes": ["abc", "efd"],
                "__DutType__": "1.0.0",
            }
        )


if __name__ == "__main__":
    test_unique()
    test_subtypes()
    test_get_nodes()
    test_to_string()
    test_serialize()
