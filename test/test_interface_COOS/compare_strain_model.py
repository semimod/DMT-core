from DMT.Hdev import get_sweep, get_coos_dfs, n3_hbt, set_force, DutCOOS, sige_hbt
from DMT.core import DutType, SimCon, specifiers, sub_specifiers, Plot
from DMT.config import DATA_CONFIG
import os

simcon = SimCon(n_core=4, t_max=200)
sweep = get_sweep(vbe=[0.7, 1.1, 121], vbc=0)

duts = []
paras = ["none", "sige"]
for para in paras:
    inp = n3_hbt(3.17, fermi=True)
    inp = set_force(inp, "phi")
    index_sige = next(i for i, param in enumerate(inp["SEMI"]) if param["mod_name"] == "SiGe")
    inp["SEMI"][index_sige]["strain"] = para
    for mob_model in inp["MOB_DEF"]:
        mob_model["beta"] = 1.4

    dut = DutCOOS(os.path.join("test/tmp"), DutType.npn, inp, reference_node="E")
    duts.append(dut)

for dut in duts:
    simcon.append_simulation(dut, sweep)

simcon.run_and_read(force=True)

# generate Band Diagram, ft and Jc
plt_ft = Plot(
    plot_name="F_T(J_C)",
    x_label=r"$J_{\mathrm{C}}\left(\si{\milli\ampere\per\square\micro\meter}\right)$",
    x_scale=1e3 / 1e6 / 1e6,
    y_specifier=specifiers.TRANSIT_FREQUENCY,
    x_log=True,
)
plt_jc = Plot(
    plot_name="J_C(V_BE)",
    y_label=r"$J_{\mathrm{C}}\left(\si{\milli\ampere\per\square\micro\meter}\right)$",
    y_scale=1e3 / 1e6 / 1e6,
    x_specifier=specifiers.VOLTAGE + "B" + "E",
    y_log=True,
)
for dut, para in zip(duts, paras):
    df_iv, df_inqu = get_coos_dfs(dut, sweep, index=1)
    plt_ft.add_data_set(
        df_iv[specifiers.CURRENT + "C"], df_iv[specifiers.TRANSIT_FREQUENCY], label=str(para)
    )
    plt_jc.add_data_set(
        df_iv[specifiers.VOLTAGE + "B"], df_iv[specifiers.CURRENT + "C"], label=str(para)
    )
plt_jc.plot_py(show=False)
plt_ft.plot_py(show=True)
