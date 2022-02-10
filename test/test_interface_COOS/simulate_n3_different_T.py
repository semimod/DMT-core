# this script demonstrates the simulation of the N3 SiGe HBT at different temps
from DMT.core import (
    Plot,
    specifiers,
    SimCon,
)
from DMT.Hdev import (
    get_coos_dfs,
    getITRSHBT,
    n3_hbt,
    get_sweep,
)
import numpy as np

# script settings:
hbt_fun = lambda: n3_hbt("1_21", spring=True)

# sweep for gummels @Vce=0.8V:
vbe_range = [0.7, 1, 61]
# vbe_range = [0.6, 0.7, 11]
vce = 0.8

plts = []
plt_iv = Plot(
    "n3" + "_" + "I_C(V_BE)",
    x_specifier=specifiers.VOLTAGE + "B" + "E",
    y_label=r"$J_{\mathrm{C}}\left(\si{\milli\ampere\per\square\micro\meter}\right)$",
    y_scale=1e3 / (1e6 * 1e6),
    y_log=True,
    style="mix",
    legend_location="upper left",
)
plt_iv.x_limits = (0.7, 1)
plts.append(plt_iv)
plt_ft = Plot(
    "n3" + "_" + "F_T(V_BE)",
    x_label=r"$J_{\mathrm{C}}\left(\si{\milli\ampere\per\square\micro\meter}\right)$",
    x_scale=1e3 / (1e6 * 1e6),
    y_specifier=specifiers.TRANSIT_FREQUENCY,
    y_scale=1e-9,
    x_log=True,
    style="mix",
    legend_location="upper left",
)
plt_ft.x_limits = (1e-2, None)
plts.append(plt_ft)

for temp in [350, 400, [300, 400, 3]]:
    sweep = get_sweep(vbe=vbe_range, vce=vce, ac=True, freq=10e9, temp=temp)
    dut_hdev = getITRSHBT(hbt_fun=hbt_fun, fermi=False, nl=False, sat=True, tn=True)  # ET transport

    simcon = SimCon(n_core=4, t_max=90)
    simcon.append_simulation(dut_hdev, sweep)
    simcon.run_and_read(force=True)

    # plot characteristics
    df_iv, df_inqu = get_coos_dfs(dut_hdev, sweep)

    if isinstance(temp, list):
        temps_in_data = np.unique(df_iv["T_LATTICE"].to_numpy())
        for temp_in_data in temps_in_data:
            df_at_temp = df_iv[df_iv["T_LATTICE"] == temp_in_data]
            label = str(temp_in_data)
            plt_iv.add_data_set(
                df_at_temp["V_B"],
                df_at_temp["I_C"],
                label=label,
            )
            plt_ft.add_data_set(
                df_at_temp["I_C"],
                df_at_temp["F_T"],
                label=label,
            )
        # get inqu at first op at 350K
        temps_in_data = df_iv["T_LATTICE"].to_numpy()
        index = np.nonzero(temps_in_data == 400)[0][0]
        _df_iv, df_inqu_400_t_swept = get_coos_dfs(dut_hdev, sweep, index + 1)
    else:
        if temp == 400:
            df_inqu_400 = df_inqu
        label = str(temp)
        plt_iv.add_data_set(
            df_iv["V_B"],
            df_iv["I_C"],
            label=label,
        )
        plt_ft.add_data_set(
            df_iv["I_C"],
            df_iv["F_T"],
            label=label,
        )

plt_band = Plot(
    "n3" + "_" + "bands",
    x_label=r"$E\left(\si{\kelvin}\right)$",
    x_scale=1e9,
    y_specifier=specifiers.ENERGY,
    style="mix",
    legend_location="upper left",
)
plts.append(plt_band)
plt_eg = Plot(
    "n3" + "_" + "eg",
    x_label=r"$E_{\mathrm{G}}\left(\si{\kelvin}\right)$",
    x_scale=1e9,
    y_specifier=specifiers.ENERGY,
    style="mix",
    legend_location="upper left",
)
plts.append(plt_eg)
plt_mu = Plot(
    "n3" + "_" + "mu",
    y_label=r"$J_{\mathrm{n}}\left(\si{\milli\ampere\per\square\micro\meter}\right)$",
    y_scale=1e3 / 1e12,
    x_label=r"$E\left(\si{\kelvin}\right)$",
    x_scale=1e9,
    style="mix",
    legend_location="upper left",
)
plts.append(plt_mu)
plt_band.add_data_set(df_inqu_400["X"], df_inqu_400["EC"], label="single T Ec")
plt_band.add_data_set(df_inqu_400["X"], df_inqu_400["EV"], label="single T Ev")
plt_band.add_data_set(df_inqu_400["X"], df_inqu_400["PHI|N"], label="single T phin")
plt_band.add_data_set(df_inqu_400["X"], df_inqu_400["PHI|P"], label="single T phip")
plt_band.add_data_set(df_inqu_400_t_swept["X"], df_inqu_400_t_swept["EC"])
plt_band.add_data_set(df_inqu_400_t_swept["X"], df_inqu_400_t_swept["EV"])
plt_band.add_data_set(df_inqu_400["X"], df_inqu_400_t_swept["PHI|N"])
plt_band.add_data_set(df_inqu_400["X"], df_inqu_400_t_swept["PHI|P"], label="phip")

plt_eg.add_data_set(df_inqu_400["X"], df_inqu_400["EC"] - df_inqu_400["EV"], label="single T Ec")
plt_eg.add_data_set(df_inqu_400["X"], df_inqu_400_t_swept["EC"] - df_inqu_400_t_swept["EV"])

plt_mu.add_data_set(df_inqu_400["X"], df_inqu_400["J|N|XDIR"], label="single T phip")
plt_mu.add_data_set(df_inqu_400_t_swept["X"], df_inqu_400_t_swept["J|N|XDIR"])

for plt in plts[:-1]:
    plt.plot_py(show=False)

plts[-1].plot_py(show=True)
