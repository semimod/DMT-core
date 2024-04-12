""" Test case for DocuDutLib with simulation comparisions

I know.... the simulation data and the measurement data do not align!! They are from two different technologies, but those are the one we have currently at hand.

"""

import types
import logging
import shutil
from pathlib import Path
from DMT.config import COMMANDS
from DMT.core import (
    DutMeas,
    DutType,
    DocuDutLib,
    DutLib,
    specifiers,
    sub_specifiers,
    Technology,
    MCard,
)
from DMT.ngspice import DutNgspice
from test_dut_ngspice_osdi import get_circuit

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent
tmp_path = test_path / "tmp"
test_data_path = test_path / "test_core_no_interfaces" / "test_data"
# -->Start main function
# --->Setup for log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_docudutlib_simu.log",
    filemode="w",
)


class TechDummy(Technology):
    def __init__(self):
        super().__init__(name="dummy")

    @staticmethod
    def deserialize():
        return TechDummy()

    def serialize(self):
        return {
            "class": str(self.__class__),
            "args": [],
            "kwargs": {},
            "constructor": "deserialize",
        }


def create_lib():
    """Create a dut lib."""

    # -->Define subroutine at first
    # --->Subroutine: filter_dut
    def filter_dut(dut_name):
        if "dummies" in dut_name:
            return None
        elif "TLM" in dut_name:
            return None
        elif dut_name == "":
            return None
        else:
            dut_transistor = DutMeas(
                database_dir=tmp_path,
                dut_type=DutType.npn,
                force=True,
                wafer=96,
                die="y",
                width=float(0.25e-6),
                length=float(0.25e-6),
                contact_config="CBEBC",
                name="dut_meas_npn",
                reference_node="E",
                technology=TechDummy(),
            )

            return dut_transistor

    # --->Arrange DMT class to dmt
    lib = DutLib(
        save_dir=tmp_path / "dut_lib_save",
        force=True,
        AC_filter_names=[("freq_vbc", "ac")],
        DC_filter_names=[("fgummel", "dc")],
    )
    # --->Add source measurement information in dmt and to duts
    lib.import_directory(
        import_dir=test_data_path,
        dut_filter=filter_dut,
        dut_level=1,
        force=True,
    )
    lib.dut_ref = lib.duts[0]

    # --->Add the open and short dummies to the lib
    dut_short = DutMeas(
        database_dir=tmp_path,
        name="dut_short_npn",
        dut_type=DutType.deem_short_bjt,
        reference_node="E",
        force=True,
        wafer=96,
        die="y",
        width=float(0.25e-6),
        length=float(0.25e-6),
        technology=TechDummy(),
    )
    dut_short.add_data(test_data_path / "dummy_short_freq.mdm", key="ac")
    dut_short.add_data(test_data_path / "short_dc.mdm", key="dc")
    dut_open = DutMeas(
        database_dir=tmp_path,
        name="dut_open_npn",
        dut_type=DutType.deem_open_bjt,
        reference_node="E",
        force=True,
        wafer=96,
        die="y",
        width=float(0.25e-6),
        length=float(0.25e-6),
        technology=TechDummy(),
    )
    dut_open.add_data(test_data_path / "dummy_open_freq.mdm", key="ac")
    lib.add_duts([dut_short, dut_open])

    # --->Clean the names of all dataframes, e.g. VB=>V_B
    for dut_a in lib:
        dut_a.clean_data(
            fallback={
                "S_DEEMB(1,1)": None,
                "S_DEEMB(2,1)": None,
                "S_DEEMB(1,2)": None,
                "S_DEEMB(2,2)": None,
            }
        )

    # emulate forced specifiers
    col_vb = specifiers.VOLTAGE + "B"
    col_ve = specifiers.VOLTAGE + "E"
    col_vc = specifiers.VOLTAGE + "C"
    for key in lib.dut_ref.data.keys():
        lib.dut_ref.data[key][col_vb + sub_specifiers.FORCED] = lib.dut_ref.data[key][col_vb]
        lib.dut_ref.data[key][col_vc + sub_specifiers.FORCED] = lib.dut_ref.data[key][col_vc]
        lib.dut_ref.data[key][col_ve + sub_specifiers.FORCED] = lib.dut_ref.data[key][col_ve]

    return lib


def create_mcard():
    mc_D21 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=folder_path.parent
        / "test_core_no_interfaces"
        / "test_va_code"
        / "hicuml2"
        / "hicumL2V2p4p0_release.va",
    )
    mc_D21.load_model_parameters(
        folder_path.parent
        / "test_core_no_interfaces"
        / "test_modelcards"
        / "IHP_ECE704_03_para_D21.mat",
    )
    mc_D21.update_from_vae(remove_old_parameters=True)
    mc_D21.get_circuit = types.MethodType(get_circuit, mc_D21)
    return mc_D21


def test_docu_with_sim():
    COMMANDS["openvaf"] = "openvaf"

    lib_test = create_lib()
    docu = DocuDutLib(
        lib_test,
        modelcard=create_mcard(),
        DutCircuitClass=DutNgspice,
        get_circuit_arguments={"use_build_in": False},
    )
    docu_path = tmp_path / "docu_dut_lib_sim"
    docu.generate_docu(
        docu_path,
        plot_specs=[{"type": "gummel_vbc", "key": "fgummel", "style": "xtraction_color"}],
        show=False,  # not possible in CI/CD
        save_tikz_settings={
            "width": "3in",
            "height": "5in",
            "standalone": True,
            "svg": False,
            "build": False,  # not possible in CI/CD
            "mark_repeat": 20,
            "clean": False,  # Remove all files except *.pdf files in plots
        },
    )

    shutil.rmtree(docu_path)


if __name__ == "__main__":
    mcard = create_mcard()
    lib_test = test_docu_with_sim()
