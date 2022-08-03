import logging
from pathlib import Path
from DMT.core import DutMeas, DutType, Plot, DutLib

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent
# -->Start main function
# --->Setup for log
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_manager.log",
    filemode="w",
)


def test_lib_import():
    """Test if the types are the correct subtypes."""
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
                name="dut_meas_npn",
                reference_node="E",
            )

            return dut_transistor

    # --->Arrange DMT class to dmt
    lib = DutLib(
        save_dir=test_path / "tmp",
        force=True,
        AC_filter_names=[("freq_vbc", "ac")],
        DC_filter_names=[("fgummel", "dc")],
    )
    # --->Add source measurement information in dmt and to duts
    lib.import_directory(
        import_dir=folder_path / "test_data" / "0p25x10x1_full",
        dut_filter=filter_dut,
        dut_level=0,
        force=True,
    )
    lib.dut_ref = lib.duts[0]

    # %%
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

    # --->Deembedding only when ac_filter is returned as True
    lib.deembed_AC(False, False, False)
    mres = lib.deembed_DC(False, False, False, t_ref=298)

    print(mres)

    return lib


def test_lib_import_lvl1():
    """Test if the types are the correct subtypes."""
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
                name="dut_meas_npn",
                reference_node="E",
            )

            return dut_transistor

    # --->Arrange DMT class to dmt
    lib = DutLib(
        save_dir=test_path / "tmp",
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

    # %%
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

    # --->Deembedding only when ac_filter is returned as True
    lib.deembed_AC(False, False, False)
    mres = lib.deembed_DC(False, False, False, t_ref=298)

    print(mres)

    return lib


if __name__ == "__main__":
    lib_test = test_lib_import()
    lib_test = test_lib_import_lvl1()
    lib_test.save()

    # --->Read freq related data with "298" and "freq_vbc" from duts
    ft_dfs = []
    for dut in lib_test:
        for key in dut.data.keys():
            if "298" in key and "freq_vbc" in key:
                ft_dfs.append(dut.get_data(key=key))

    # --->Extract ic, ft, vbc from ft_dfs
    ic, ft, vbc, ic_ftmax = [], [], [], []
    for df in ft_dfs:
        df = df.calc_ft("B", "C")
        df = df[df["FREQ"] == 10e9]
        ic.append(df["I_C"])
        ft.append(df["F_T"])
        vbc.append(df["V_B"].to_numpy() - df["V_C"].to_numpy())
        df = df.loc[df["F_T"].idxmax()]
        ic_ftmax.append(df["I_C"])
        vbc[-1] = round(vbc[-1][0], 3)

    # -->Plot
    # --->Define plot type according to Plot
    plt_ft = Plot("f_T(I_C)", x_log=True, style="color", legend_location="upper left")

    # --->Add x,y data in plot with using enumerate: loop index+elements
    for i, array in enumerate(ic):
        plt_ft.add_data_set(
            ic[i] * 1e3, ft[i] * 1e-9, label=r"$V_{\mathrm{BC}}=" + str(vbc[i]) + r"\,$V"
        )

    # --->Define x and y limit
    plt_ft.x_limits = (1e-1, 1e2)
    plt_ft.y_limits = (0, 325)

    # --->Get plot
    plt_ft.plot_py()
