from DMT.core import Plot, specifiers, Sweep, SimCon, DutType, Plot2YAxis, read_data
from DMT.Hdev import DutCOOS, get_coos_dfs, getITRSHBT, n3_hbt, n1_hbt, n2_hbt, n4_hbt, n5_hbt
import os

# specify which HBT profile you would like to see
hbt_type = "n5"

profiles = {
    "n1": lambda: n1_hbt("1_21", spring=True),
    "n2": lambda: n2_hbt("1_21", spring=True),
    "n3": lambda: n3_hbt("1_21", spring=True),
    "n4": lambda: n4_hbt("1_21", spring=True),
    "n5": lambda: n5_hbt("1_21", spring=True),
}

hbt_fun = profiles[hbt_type]

# equilibrium simulation
sweepdef = [
    {
        "var_name": specifiers.VOLTAGE + "E",
        "sweep_order": 2,
        "sweep_type": "CON",
        "value_def": [0],
    },
    {
        "var_name": specifiers.VOLTAGE + "C",
        "sweep_order": 1,
        "sweep_type": "SYNC",
        "master": "V_B",
        "offset": 0,
    },
    {
        "var_name": specifiers.VOLTAGE + "B",
        "sweep_order": 1,
        "sweep_type": "CON",
        "value_def": [0],
    },
]
outputdef = []
othervar = {"TEMP": 300}
sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

dut_hdev = getITRSHBT(hbt_fun=hbt_fun, fermi=False, nl=False, sat=False, tn=True)

simcon = SimCon(n_core=4, t_max=30)
simcon.append_simulation(dut_hdev, sweep)
simcon.run_and_read(force=True)

df_iv, df_inqu = get_coos_dfs(dut_hdev, sweep)

plt_band_diagram = Plot(
    hbt_type + "_equilibrium_band_diagram",
    x_label=r"$x\left( \si{\nano\meter}\right)$",
    x_scale=1e9,
    y_label=r"$E\left(\si{\eV} \right)$",
    y_log=False,
    y_scale=1,
)
plt_dop = Plot(
    "dop_simplified",
    x_label=r"$x\left( \si{\nano\meter}\right)$",
    x_scale=1e9,
    y_label=r"$N_{\mathrm{net}}\left( \si{\per\cubic\centi\meter} \right) $",
    y_scale=1e-6,
    y_log=True,
    style="mix",
)
plt_dop.y_limits = (1e16, 1e21)
plt_grading = Plot(
    "grading_simplified",
    x_label=r"$x\left( \si{\nano\meter}\right)$",
    x_scale=1e9,
    y_label=r"$C\left(\si{\percent} \right)$",
    y_log=False,
    y_scale=1e2,
)
plt_profile = Plot2YAxis("n1_profile_", plt_dop, plt_grading, legend_location="upper right outer")


df_iv, df_inqu = get_coos_dfs(dut_hdev, sweep)

plt_band_diagram.add_data_set(df_inqu["X"], df_inqu["EC"], style="-r", label=r"$E_{\mathrm{C}}$")
plt_band_diagram.add_data_set(df_inqu["X"], df_inqu["EV"], style="-b", label=r"$E_{\mathrm{V}}$ ")

plt_dop.add_data_set(df_inqu["X"], df_inqu["NNET"], style="-r", label=r"$N_{\mathrm{net}}$")
plt_grading.add_data_set(df_inqu["X"], df_inqu["MOL"], style="--k", label="$C$")

plt_band_diagram.plot_py(show=False)
plt_profile.plot_py(show=True)
