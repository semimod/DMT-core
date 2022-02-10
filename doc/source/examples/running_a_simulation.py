from DMT.core import Sweep, SimCon, Plot, specifiers, DutType
from DMT.hl2 import McHicum
from DMT.ngspice import DutNgspice
import os

# load a hicum modelcard library and define the corresponding *va code.
mc_D21 = McHicum(
    va_file=VA_FILES["L2V2.4.0_release"],
    load_model_from_path="test/test_core_no_interfaces/test_modelcards/IHP_ECE704_03_para_D21.mat",
)

# init an Ngspice Dut
dut = DutNgspice(None, DutType.npn, mc_D21, nodes="C,B,E,S,T", reference_node="E")
# DMT uses the exact same interface for all circuit simulators, e.g. the call for an ADS simulation would be:
# dut = DutADS(None, DutType.npn, mc_D21, nodes='C,B,E,S,T', reference_node='E')
# isn't it great?!?

# create a sweep (all DMT Duts can use this!)
sweepdef = [
    {"var_name": specifiers.FREQUENCY, "sweep_order": 4, "sweep_type": "CONST", "value_def": [1e9]},
    {
        "var_name": specifiers.VOLTAGE + "B",
        "sweep_order": 3,
        "sweep_type": "LIN",
        "value_def": [0.5, 1, 51],
    },
    {"var_name": specifiers.VOLTAGE + "C", "sweep_order": 2, "sweep_type": "CON", "value_def": [1]},
    {"var_name": specifiers.VOLTAGE + "E", "sweep_order": 1, "sweep_type": "CON", "value_def": [0]},
]
outputdef = ["I_C", "I_B"]
othervar = {"TEMP": 300}
sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

# The simulation controller can control all simulators implemented in DMT!
sim_con = SimCon()

# Add the desired simulation to the queue and start the simulation
sim_con.append_simulation(dut=dut, sweep=sweep)
sim_con.run_and_read(force=True, remove_simulations=False)

# Read back the iv data of the circuit simulator
data = dut.get_data(sweep=sweep)
# Ensure derived quantities, e.g. the circuit simulator only gives you S parameters
data.ensure_specifier_column(specifiers.TRANSIT_FREQUENCY, ports=["B", "C"])

# Plot and save as pdf
plt_ft = Plot(
    plot_name="F_T(J_C)",
    x_label=r"$I_{\mathrm{C}}\left(\si{\milli\ampere}\right)$",
    x_scale=1e3,
    y_specifier=specifiers.TRANSIT_FREQUENCY,
    x_log=True,
)
plt_ft.add_data_set(
    data[specifiers.CURRENT + "C"],
    data[specifiers.TRANSIT_FREQUENCY],
)
plt_ft.x_limits = 1e-3, None
plt_ft.y_limits = 0, None

plt_ft.save_tikz("doc/source/_static/", standalone=True, build=True, clean=True, width="3in")
