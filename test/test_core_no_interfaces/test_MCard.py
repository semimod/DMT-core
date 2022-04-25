""" Testing McParameter, McParameterCollection, MCard and McHicum from L2
"""
from importlib.resources import read_text
import os
import logging
import pytest
import numpy as np
from pathlib import Path
from DMT.core import MCard

from DMT.core.mc_parameter import McParameter
from DMT.core.circuit import HICUML2_HBT

from DMT.exceptions import BoundsError, ValueTooLargeError

folder_path = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_mcard_class.log",
    filemode="w",
)


def test_type_mc_parameter():
    """Test the type (float or int) of the mc_parameter class"""
    a = McParameter("asd", value=int(65))  # setting a integer value, but not, float type
    assert (
        a.val_type == float
    )  # even if a integer is set, the type is still float to prevent unwanted conversions
    assert a.value == int(65)

    a.value = 65.43

    with pytest.raises(IOError):
        a.val_type = int

    a.value = 65  # here we set a integer value and int type
    a.val_type = int

    with pytest.raises(TypeError):  # can not set a float number anymore
        a.value = 65.342

    with pytest.raises(BoundsError):  # can not set a maximum below the current value
        a.max = 20

    a.max = 100
    with pytest.raises(ValueTooLargeError):  # can not set a value above the maximum value
        a.value = 120


def test_format_mc_parameter():
    """Format mc parameters, so this is just pretty printing feature!

    Notice: __format__ is redefined in class McParameter in which format "s" corresponds name in McParameter, and "d","e","f", "g" corredpond value
    """

    value = 6556.1234
    name = "para"
    a = McParameter(name, value=value)
    assert "{0:f}".format(a) == "{0:f}".format(value)
    assert "{0:e}".format(a) == "{0:e}".format(value)

    assert "{0:s}".format(a) == "{0:s}".format(name)


def test_mcard_load_compare():
    """Compare two loaded model cards"""
    mc_D21 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
    )
    mc_D21.load_model_parameters(
        folder_path / "test_modelcards" / "IHP_ECE704_03_para_D21.mat",
    )
    mc_N5 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
    )
    mc_N5.load_model_parameters(
        folder_path / "test_modelcards" / "ITRS_N5.mat",
    )
    assert mc_N5 != mc_D21


def test_set_va_code():
    hicum_path = folder_path / "hicumL2V2p4p0_release.va"

    mc = MCard(
        ["A"],
        "Q_HIC",
        "hicuml2va",
        va_file=hicum_path,
    )

    assert mc.va_codes is not None and (
        all([vafile in [hicum_path.name] for (vafile, vacode) in mc.va_codes.iter_codes()])
        and len(mc.va_codes) == 1
    )
    assert set(mc.nodes_list) == {"c", "b", "e", "tnode", "s"}

    mc.set_va_codes(
        folder_path / "test_va_code" / "diode_cmc_160823" / "diode_cmc.va",
    )

    va_codes_target_names = {
        "diode_cmc.va",
        "DIODE_CMC_InitModel.include",
        "DIODE_CMC_macrodefs.include",
        "DIODE_CMC_parlist.include",
        "DIODE_CMC_SIMKIT_macrodefs.include",
        "DIODE_CMC_varlist1.include",
        "DIODE_CMC_varlist2.include",
    }

    assert set(vafile for vafile, vacode in mc.va_codes.iter_codes()) == va_codes_target_names

    file_name = "test_va_codes.json"
    mc.dump_json(file_name, save_va_code=False)

    mc_saved = MCard.load_json(file_name)
    assert mc_saved.va_codes is None

    mc.dump_json(file_name)  # is true per default
    mc_saved = MCard.load_json(file_name)
    assert mc_saved.va_codes is not None and (
        set(vafile for vafile, vacode in mc_saved.va_codes.iter_codes()) == va_codes_target_names
    )

    file_name_compressed = "test_va_codes_compressed.json"
    mc.dump_json(file_name_compressed, compress_va_code=True)
    mc_saved = MCard.load_json(file_name_compressed)
    assert mc_saved.va_codes is not None and (
        set(vafile for vafile, vacode in mc_saved.va_codes.iter_codes()) == va_codes_target_names
    )
    assert mc_saved.va_codes == mc.va_codes

    os.remove(file_name)
    os.remove(file_name_compressed)

    # test the regex for minimal working environment..
    mc_saved.read_va_file_boundaries()

    assert mc_saved.default_module_name == "DIODE_CMC"
    assert len(mc_saved.paras) == 102
    assert set(mc_saved.nodes_list) == {"A", "K"}

    # test the vae updating
    assert "c10" in mc.name
    mc.update_from_vae(remove_old_parameters=True)

    assert "c10" not in mc.name
    assert set(mc.nodes_list) == {"A", "K"}


def test_read_va_file():
    mc = MCard(["A"], "Q_HIC", "hicuml2va", va_file=folder_path / "hicumL2V2p4p0_release.va")
    mc.update_from_vae()  # McHicum(va_file=VA_FILES["L2V2.4.0_release"])

    assert len(mc) == 136


def test_json():
    mc = MCard(["A"], "Q_HIC", "hicuml2va", va_file=folder_path / "hicumL2V2p4p0_release.va")
    mc.set_values({"c10": 3e-15})  # just a little change

    file_name = "test_json_mchicum.json"
    mc.dump_json(file_name)
    mc_read = MCard.load_json(file_name)

    assert mc == mc_read

    mc_read_general = MCard.load_json(file_name)  # This should also work?
    assert mc == mc_read_general

    os.remove(file_name)

    mc = MCard(["A"], "Q_HIC", "hicuml2va", va_file=folder_path / "hicumL2V2p4p0_release.va")
    with pytest.raises(KeyError):
        mc.set_values({"is": 3e-15})  # just a little change


def test_load_MCard_v1():
    """Load a version 1 model"""
    file_name = folder_path / "test_modelcards" / "N3_MCard_v1.json"
    mc_read = MCard.load_json(file_name)

    assert mc_read.va_codes is None  # path can not be resolved!

    assert np.isclose(mc_read["c10"].value, 5.991798808405992e-30)


if __name__ == "__main__":
    test_type_mc_parameter()
    test_format_mc_parameter()
    test_mcard_load_compare()
    test_set_va_code()
    test_read_va_file()
    test_json()
    test_load_MCard_v1()
