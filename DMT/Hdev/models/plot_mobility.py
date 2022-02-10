""" Shows how to plot mobility of a given Semiconductor in Hdev.
"""
from DMT.core import Plot
from DMT.Hdev import get_mobility, GaAs, get_velocity
import numpy as np

eabs = np.linspace(1, 30 * 1e3 / 1e-2)
mob = get_mobility(GaAs, "G", eabs, 1e20, 300)
velo = get_velocity(GaAs, "G", eabs, 1e20, 300)

plt_mob_e = Plot(
    "mu(eabs)",
    style="color",
    x_log=False,
    y_scale=1e4,
    y_label=r"$\mu(\si{\square\centi\meter\per\volt\second})$",
    x_label=r"$E(\si{\kilo\volt\per\centi\meter})$",
    x_scale=1 / (1e3 / 1e-2),
)
plt_mob_e.add_data_set(
    eabs,
    mob,
    label="mob Hdev",
)
plt_mob_e.plot_py(show=False)

plt_v_e = Plot(
    "V(eabs)",
    style="color",
    x_log=False,
    y_scale=(1 / (1e7 * 1e-2)),
    y_label=r"$v(1e7\si{\centi\meter\per\second})$",
    x_label=r"$E(\si{\kilo\volt\per\centi\meter})$",
    x_scale=1e-5,
)
plt_v_e.add_data_set(
    eabs,
    velo,
    label="mob Hdev",
)
plt_v_e.plot_py(show=False)

imp = np.logspace(21, 26, 51)
mob = get_mobility(GaAs, "G", 1, imp, 300)

plt_mob_imp = Plot(
    "mu(N)",
    style="color",
    x_log=True,
    y_scale=1e4,
    y_label=r"$\mu(\si{\square\centi\meter\per\volt\second})$",
    x_label=r"$N(\si{\per\cubic\centi\meter})$",
    x_scale=1e-6,
)
plt_mob_imp.add_data_set(
    imp,
    mob,
    label="mob Hdev",
)
plt_mob_imp.plot_py(show=True)
