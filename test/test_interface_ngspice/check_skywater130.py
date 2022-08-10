""" test ngspice skywater130 simulation
"""
import numpy as np
from pathlib import Path
from DMT.core import MCard, DutType, Sweep, specifiers, SimCon, Plot
from DMT.core.sweep_def import SweepDefList
from DMT.core.circuit import Circuit, CircuitElement, RESISTANCE, VOLTAGE

from DMT.ngspice import DutNgspice

folder_path = Path(__file__).resolve().parent

col_vg = specifiers.VOLTAGE + "G"
col_vd = specifiers.VOLTAGE + "D"
col_vs = specifiers.VOLTAGE + "S"
col_vb = specifiers.VOLTAGE + "B"
col_ig = specifiers.CURRENT + "G"
col_id = specifiers.CURRENT + "D"
col_is = specifiers.CURRENT + "S"
col_ib = specifiers.CURRENT + "B"
col_freq = specifiers.FREQUENCY

mcard = MCard(
    nodes_list=["n_D", "n_G", "n_S", "n_B"],
    default_subckt_name="x1",
    default_module_name="sky130_fd_pr__nfet_01v8",
)
mcard.set_values(
    {
        "l": 1,
        "w": 1,
        "nf": 1.0,
        "ad": 0,
        "as": 0,
        "pd": 0,
        "ps": 0,
        "nrd": 0,
        "nrs": 0,
        "sa": 0,
        "sb": 0,
        "sd": 0,
        "mult": 1,
    },
    policy_missing="add",
)
mcard.pdk_path = "/usr/local/share/pdk/sky130B/libs.tech/ngspice/sky130.lib.spice"
mcard.pdk_corner = "tt"

circuit = Circuit(
    [
        CircuitElement(
            "sky130_fd_pr__nfet_01v8", "x1", ["n_D", "n_G", "n_S", "n_B"], parameters=mcard
        ),
        CircuitElement(RESISTANCE, "R_D", ["n_D", "n_DX"], parameters=[("R", "1")]),
        CircuitElement(VOLTAGE, "V_D", ["n_DX", "0"], parameters=[("Vdc", "V_D"), ("Vac", "1")]),
        CircuitElement(VOLTAGE, "V_G", ["n_GX", "0"], parameters=[("Vdc", "V_G"), ("Vac", "1")]),
        CircuitElement(RESISTANCE, "R_G", ["n_GX", "n_G"], parameters=[("R", "1")]),
        CircuitElement(RESISTANCE, "R_S", ["n_S", "0"], parameters=[("R", "0")]),
        CircuitElement(RESISTANCE, "R_B", ["n_B", "0"], parameters=[("R", "0")]),
    ]
)

dut = DutNgspice(None, DutType.n_mos, circuit, nodes="D,G,GX,DX", reference_node="S")

# create a sweep
sweep = Sweep(
    "forward",
    sweepdef=[
        SweepDefList(col_vd, np.linspace(0, 1.8, 19), sweep_order=0),
        SweepDefList(col_vg, np.linspace(0, 1.2, 31), sweep_order=1),
    ],
    outputdef=[col_ig, col_id, col_is, col_ib],
    othervar={"TEMP": 300},
)

sim_con = SimCon(t_max=300)

sim_con.append_simulation(dut=dut, sweep=sweep)
sim_con.run_and_read(force=False, remove_simulations=False)

df = dut.get_data(sweep=sweep)

plt_id_vd = Plot(
    "ID(VD)",
    x_specifier=col_vd,
    y_specifier=col_id,
    legend_location="upper left",
    style="color",
    divide_by_unit=True,
)
plt_id_vg = Plot(
    "ID(VG)",
    x_specifier=col_vg,
    y_specifier=col_id,
    legend_location="lower left",
    style="color",
    divide_by_unit=True,
)

vg_to_plot = np.linspace(0, 1.2, 16)
for i_vg, vg, data_vg in df.iter_unique_col(col_vg, decimals=2):
    if vg in vg_to_plot:
        plt_id_vd.add_data_set(
            data_vg[col_vd],
            data_vg[col_id],
            label=col_vg.to_legend_with_value(vg),
        )
vd_to_plot = np.linspace(0, 1.8, 19)
for i_vd, vd, data_vd in df.iter_unique_col(col_vd, decimals=2):
    if vd in vd_to_plot:
        plt_id_vg.add_data_set(
            data_vd[col_vg],
            data_vd[col_id],
            label=col_vd.to_legend_with_value(vd),
        )

plt_id_vd.plot_pyqtgraph(show=False)
plt_id_vg.plot_pyqtgraph(show=True)


# plt_id_vd.save_tikz(
#     folder_path.parent / "tmp" / "check_skywater130",
#     standalone=True,
#     build=True,
#     clean=True,
#     width="6in",
#     legend_location="upper left",
# )
# plt_id_vg.save_tikz(
#     folder_path.parent / "tmp" / "check_skywater130",
#     standalone=True,
#     build=True,
#     clean=True,
#     width="6in",
#     legend_location="upper left",
# )
