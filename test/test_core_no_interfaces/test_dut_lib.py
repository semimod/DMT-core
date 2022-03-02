import logging
from pathlib import Path
from DMT.core import DutMeas, DutType, DocuDutLib, DutLib

# -->Start main function
# --->Setup for log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=Path(__file__).resolve().parent.parent.parent / "logs" / "test_dut_lib.log",
    filemode="w",
)


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
                database_dir=Path("test") / "tmp",
                dut_type=DutType.npn,
                force=True,
                wafer=96,
                die="y",
                width=float(0.25e-6),
                length=float(0.25e-6),
                name="dut_meas_npn",
                reference_node="E",
            )

            return dut_transistor

    # --->Arrange DMT class to dmt
    lib = DutLib(
        save_dir=Path("test") / "tmp",
        force=True,
        AC_filter_names=[("freq_vbc", "ac")],
        DC_filter_names=[("fgummel", "dc")],
    )
    # --->Add source measurement information in dmt and to duts
    lib.import_directory(
        import_dir=Path(__file__).parent / "test_data",
        dut_filter=filter_dut,
        dut_level=1,
        force=True,
    )
    lib.dut_ref = lib.duts[0]

    # --->Add the open and short dummies to the lib
    dut_short = DutMeas(
        database_dir=Path("test") / "tmp",
        name="dut_short_npn",
        dut_type=DutType.deem_short_bjt,
        reference_node="E",
        force=True,
        wafer=96,
        die="y",
        width=float(0.25e-6),
        length=float(0.25e-6),
    )
    dut_short.add_data(Path(__file__).parent / "test_data" / "dummy_short_freq.mdm", key="ac")
    dut_short.add_data(Path(__file__).parent / "test_data" / "short_dc.mdm", key="dc")
    dut_open = DutMeas(
        database_dir=Path("test") / "tmp",
        name="dut_open_npn",
        dut_type=DutType.deem_open_bjt,
        reference_node="E",
        force=True,
        wafer=96,
        die="y",
        width=float(0.25e-6),
        length=float(0.25e-6),
    )
    dut_open.add_data(Path(__file__).parent / "test_data" / "dummy_open_freq.mdm", key="ac")
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

    # --->Deembedding only when ac_filter is returned as True
    lib.deembed_AC(False, False, False)
    mres = lib.deembed_DC(False, False, False, t_ref=298)

    print(mres)

    return lib


def test_docu():

    lib_test = create_lib()
    docu = DocuDutLib()

    docu.plot_all(
        lib_test,
        mode={"dev_mode": "all"},
    )


if __name__ == "__main__":
    lib_test = create_lib()
