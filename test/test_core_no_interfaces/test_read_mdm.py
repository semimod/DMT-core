import requests
import numpy as np
from pathlib import Path
from DMT.core import read_data, Plot, specifiers
from DMT.core.data_reader import read_mdm


folder_path = Path(__file__).resolve().parent
folder_tmp = folder_path.parent / "tmp"


def test_read_mdm():
    df = read_data(folder_path / "test_data" / "short_freq.mdm")
    df = read_data(folder_path / "test_data" / "short_dc.mdm")


def test_read_skywater_mdm():
    req = requests.get(
        "https://raw.githubusercontent.com/google/skywater-pdk-sky130-raw-data/5738bf8753688baf2111d8d1b6a3e51a38a0bbeb/sky130_fd_pr/cells/nfet_01v8/sky130_fd_pr__nfet_01v8_w0p36u_l0p15u_m1(8701_9_10_IDVD).mdm"
    )
    if req.status_code == requests.codes.ok:
        file_tmp = folder_tmp / "skywater_nfet_01v8.mdm"
        with open(file_tmp, "w") as tmp_file:
            tmp_file.write(req.text)
        df = read_mdm(file_tmp)
        file_tmp.unlink()
    else:
        raise IOError()

    assert len(df) == 444  # 6 VG, 37 VD, 2 VB
    assert all(df["VB"].unique() == np.array([0.0, -0.9]))
    assert np.allclose(df["VG"].unique(), np.linspace(0.0, 1.8, 6))
    assert np.allclose(df["VD"].unique(), np.linspace(0.0, 1.8, 37))

    req = requests.get(
        "https://raw.githubusercontent.com/google/skywater-pdk-sky130-raw-data/5738bf8753688baf2111d8d1b6a3e51a38a0bbeb/sky130_fd_pr/cells/nfet_g5v0d10v5/sky130_fd_pr__nfet_g5v0d10v5_w0p420u_l0p500u_m1(2618_1_10_IDVD_D3).mdm"
    )
    if req.status_code == requests.codes.ok:
        file_tmp = folder_tmp / "nfet_g5v0d10v5.mdm"
        with open(file_tmp, "w") as tmp_file:
            tmp_file.write(req.text)
        df = read_mdm(file_tmp)
        file_tmp.unlink()
    else:
        raise IOError()

    assert len(df) == 1212  # 6 VG, 101 VD, 2 VB
    assert all(df["VB"].unique() == np.array([0.0, -2.5]))
    assert np.allclose(df["VG"].unique(), np.linspace(0.0, 5.0, 6))
    assert np.allclose(df["VD"].unique(), np.linspace(0.0, 5.0, 101))

    return df


if __name__ == "__main__":
    test_read_mdm()
    df = test_read_skywater_mdm()

    sp_id = specifiers.CURRENT + ["D"]
    sp_ib = specifiers.CURRENT + ["B"]
    sp_ig = specifiers.CURRENT + ["G"]
    sp_vg = specifiers.VOLTAGE + ["G"]
    sp_vd = specifiers.VOLTAGE + ["D"]
    sp_vb = specifiers.VOLTAGE + ["B"]

    plt_id = Plot(
        "ID(VG)",
        x_specifier=sp_vg,
        y_specifier=sp_id,
        legend_location="upper left",
        style="color",
        divide_by_unit=True,
    )
    plt_ib = Plot(
        "IB(VG)",
        x_specifier=sp_vg,
        y_specifier=sp_ib,
        legend_location="lower left",
        style="color",
        divide_by_unit=True,
    )
    plt_ig = Plot(
        "IG(VG)",
        x_specifier=sp_vg,
        y_specifier=sp_ig,
        legend_location="lower left",
        style="color",
        divide_by_unit=True,
    )

    for i_vb, vb, data_vb in df.iter_unique_col("VB"):
        for i_vg, vg, data_vg in data_vb.iter_unique_col("VG"):
            plt_id.add_data_set(
                data_vg["VD"],
                data_vg["ID"],
                label=f"{sp_vb.to_legend_with_value(vb)}, {sp_vg.to_legend_with_value(vg)}",
            )
            plt_ib.add_data_set(
                data_vg["VD"],
                data_vg["IB"],
                label=f"{sp_vb.to_legend_with_value(vb)}, {sp_vg.to_legend_with_value(vg)}",
            )
            plt_ig.add_data_set(
                data_vg["VD"],
                data_vg["IG"],
                label=f"{sp_vb.to_legend_with_value(vb)}, {sp_vg.to_legend_with_value(vg)}",
            )

    plt_id.plot_pyqtgraph(show=False)
    plt_ib.plot_pyqtgraph(show=False)
    plt_ig.plot_pyqtgraph(show=True)
