import types
import numpy as np
from pathlib import Path
from DMT.core import Sweep, SimCon, Plot, specifiers, DutType, MCard
from DMT.core.circuit import Circuit, CircuitElement, HICUML2_HBT, SHORT, VOLTAGE, RESISTANCE
from DMT.xyce import DutXyce
from DMT.ngspice import DutNgspice

# path to DMT test cases
path_test = Path(__file__).resolve().parent.parent.parent.parent / "test"

# load a hicum/L2 modelcard library by loading the corresponding *va code.
modelcard = MCard(
    ["C", "B", "E", "S", "T"],
    default_module_name="",
    default_subckt_name="",
    va_file=path_test / "test_interface_xyce" / "hicuml2v2p4p0_xyce.va",
)
modelcard.load_model_parameters(
    path_test / "test_core_no_interfaces" / "test_modelcards" / "npn_full.lib",
)
modelcard.update_from_vae(remove_old_parameters=True)

# bind the correct get_circuit method in order to make it easily available for simulation
def get_circuit(self):
    """

    Parameter
    ------------
    modelcard : :class:`~DMT.core.MCard`

    Returns
    -------
    circuit : :class:`~DMT.core.circuit.Circuit`

    """
    circuit_elements = []
    # model instance
    circuit_elements.append(
        CircuitElement(
            HICUML2_HBT, "Q_H", [f"n_{node.upper()}" for node in self.nodes_list], parameters=self
        )
    )

    # BASE NODE CONNECTION #############
    # shorts for current measurement
    circuit_elements.append(CircuitElement(SHORT, "I_B", ["n_B", "n_B_FORCED"]))
    # COLLECTOR NODE CONNECTION #############
    circuit_elements.append(CircuitElement(SHORT, "I_C", ["n_C", "n_C_FORCED"]))
    # EMITTER NODE CONNECTION #############
    circuit_elements.append(CircuitElement(SHORT, "I_E", ["n_E", "0"]))
    # add sources and thermal resistance
    circuit_elements.append(
        CircuitElement(
            VOLTAGE, "V_B", ["n_B_FORCED", "0"], parameters=[("Vdc", "V_B"), ("Vac", "1")]
        )
    )
    circuit_elements.append(
        CircuitElement(
            VOLTAGE, "V_C", ["n_C_FORCED", "0"], parameters=[("Vdc", "V_C"), ("Vac", "1")]
        )
    )
    circuit_elements += ["V_B=0", "V_C=0", "ac_switch=0", "V_B_ac=1-ac_switch", "V_C_ac=ac_switch"]

    return Circuit(circuit_elements)


modelcard.get_circuit = types.MethodType(get_circuit, modelcard)

# init an Xyce Dut
dut = DutXyce(None, DutType.npn, modelcard, nodes="C,B,E,S,T", reference_node="E")
# DMT uses the exact same interface for all circuit simulators, e.g. the call for a ngspice simulation would be:
# dut = DutNgspice(None, DutType.npn, modelcard, nodes="C,B,E,S,T", reference_node="E")
# isn't it great?!?

# create a sweep (all DMT Duts can use this!)
# some column names we want to simulate and plot
col_ve = specifiers.VOLTAGE + "E"
col_vb = specifiers.VOLTAGE + "B"
col_vc = specifiers.VOLTAGE + "C"
col_vbe = specifiers.VOLTAGE + ["B", "E"]
col_vcb = specifiers.VOLTAGE + ["C", "B"]
col_vbc = specifiers.VOLTAGE + ["B", "C"]
col_ic = specifiers.CURRENT + "C"
col_freq = specifiers.FREQUENCY
col_ft = specifiers.TRANSIT_FREQUENCY
sweepdef = [
    {"var_name": col_freq, "sweep_order": 4, "sweep_type": "CONST", "value_def": [1e9]},
    {"var_name": col_vb, "sweep_order": 3, "sweep_type": "LIN", "value_def": [0.5, 1, 51]},
    {
        "var_name": col_vc,
        "sweep_order": 3,
        "sweep_type": "SYNC",
        "master": col_vb,
        "offset": col_vcb,
    },
    {"var_name": col_vcb, "sweep_order": 2, "sweep_type": "LIST", "value_def": [-0.5, 0, 0.5]},
    {"var_name": col_ve, "sweep_order": 1, "sweep_type": "CON", "value_def": [0]},
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
data.ensure_specifier_column(col_vbe, ports=["B", "C"])
data.ensure_specifier_column(col_vbc, ports=["B", "C"])
data.ensure_specifier_column(col_ft, ports=["B", "C"])

# Plot and save as pdf
plt_ic = Plot(
    plot_name="J_C(V_BE)",
    x_specifier=col_vbe,
    y_specifier=col_ic,
    y_scale=1e3,
    y_log=True,
    legend_location="lower right",
)
plt_ft = Plot(
    plot_name="F_T(J_C)",
    x_specifier=col_ic,
    x_scale=1e3,
    x_log=True,
    y_specifier=col_ft,
    legend_location="upper left",
)
for i_vbc, vbc, data_vbc in data.iter_unique_col(col_vbc, decimals=3):
    vbc = np.real(vbc)
    plt_ic.add_data_set(
        data_vbc[col_vbe], data_vbc[col_ic], label=col_vbc.to_legend_with_value(vbc)
    )
    plt_ft.add_data_set(data_vbc[col_ic], data_vbc[col_ft], label=col_vbc.to_legend_with_value(vbc))

plt_ic.x_limits = 0.7, 1
plt_ic.y_limits = 1e-2, 1e2
plt_ft.x_limits = 1e-2, 1e2
plt_ft.y_limits = 0, 420

plt_ic.plot_pyqtgraph(show=False)
plt_ft.plot_pyqtgraph()

plt_ic.save_tikz(
    Path(__file__).parent.parent / "_static" / "running_a_simulation",
    standalone=True,
    build=True,
    clean=True,
    width="3in",
)
plt_ft.save_tikz(
    Path(__file__).parent.parent / "_static" / "running_a_simulation",
    standalone=True,
    build=True,
    clean=True,
    width="3in",
)
