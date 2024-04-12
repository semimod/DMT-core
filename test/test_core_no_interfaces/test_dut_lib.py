import logging
import shutil
from pathlib import Path
from DMT.core import DutMeas, DutType, DocuDutLib, DutLib, specifiers, sub_specifiers, Technology

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent
# -->Start main function
# --->Setup for log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_dut_lib.log",
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
                database_dir=test_path / "tmp",
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
        save_dir=test_path / "tmp" / "dut_lib_save",
        force=True,
        AC_filter_names=[("freq_vbc", "ac")],
        DC_filter_names=[("fgummel", "dc")],
    )
    # --->Add source measurement information in dmt and to duts
    lib.import_directory(
        import_dir=folder_path / "test_data",
        dut_filter=filter_dut,
        dut_level=1,
        force=True,
    )
    lib.dut_ref = lib.duts[0]

    # --->Add the open and short dummies to the lib
    dut_short = DutMeas(
        database_dir=test_path / "tmp",
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
    dut_short.add_data(folder_path / "test_data" / "dummy_short_freq.mdm", key="ac")
    dut_short.add_data(folder_path / "test_data" / "short_dc.mdm", key="dc")
    dut_open = DutMeas(
        database_dir=test_path / "tmp",
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
    dut_open.add_data(folder_path / "test_data" / "dummy_open_freq.mdm", key="ac")
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


def test_docu():
    lib_test = create_lib()
    docu = DocuDutLib(lib_test)
    docu_path = folder_path.parent / "tmp" / "docu_dut_lib"
    docu.generate_docu(
        docu_path,
        plot_specs=[{"type": "gummel_vbc", "key": "fgummel"}],
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


def test_lib_save_load():
    lib_test = create_lib()
    lib_test.save()

    lib_loaded = DutLib.load(
        folder_path.parent / "tmp" / "dut_lib_save",
        [TechDummy],
    )

    ## some asserts
    assert len(lib_test.duts) == len(lib_loaded.duts)
    assert lib_test.dut_ref_dut_dir == lib_loaded.dut_ref_dut_dir
    assert lib_test.wafer == lib_loaded.wafer

    for dut_test in lib_test:
        # find dut in lib_loaded
        # compare data
        for dut_load in lib_loaded:
            if dut_test.name == dut_load.name:
                assert dut_test.dut_type == dut_load.dut_type
                key = ""
                if "open" in dut_test.name:
                    key = "ac"
                elif "short" in dut_test.name:
                    key = "dc"
                elif "dut_meas_npn" in dut_test.name:
                    key = "T298.00K/freq_vbc_0p3"

                assert dut_test.data[key].equals(dut_load.data[key])

    shutil.rmtree(lib_test.save_dir)


if __name__ == "__main__":
    lib_test = test_docu()
    test_lib_save_load()
