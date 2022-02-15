import types
from pathlib import Path
from DMT.core import Sweep, SimCon, Plot, specifiers, DutType, MCard
from DMT.core.circuit import Circuit, CircuitElement, HICUML2_HBT, SHORT, VOLTAGE, RESISTANCE
from DMT.xyce import DutXyce
from DMT.ngspice import DutNgspice

# path to DMT test cases
path_test = Path("test")

# load a hicum/L2 modelcard library by loading the corresponding *va code.
modelcard = MCard(
    ["C", "B", "E", "S", "T"],
    default_module_name="",
    default_subckt_name="",
    va_file=path_test / "test_interface_xyce" / "hicuml2v2p4p0_xyce.va",
)
modelcard.load_model(
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

    # metal resistance between substrate contact and ground
    circuit_elements.append(
        CircuitElement(RESISTANCE, "R_S", ["n_S", "0"], parameters=[("R", "0.1")])
    )
    # thermal node resistance
    circuit_elements.append(
        CircuitElement(RESISTANCE, "R_t", ["n_T", "0"], parameters=[("R", "1e9")])
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
    x_specifier=specifiers.CURRENT + "C",
    x_scale=1e3,
    x_log=True,
    y_specifier=specifiers.TRANSIT_FREQUENCY,
)
plt_ft.add_data_set(data[specifiers.CURRENT + "C"], data[specifiers.TRANSIT_FREQUENCY])
plt_ft.x_limits = 1e-2, 1e2
plt_ft.y_limits = 0, 420

plt_ft.plot_pyqtgraph()
plt_ft.save_tikz(
    Path(__file__).parent.parent / "_static",
    standalone=True,
    build=True,
    clean=True,
    width="3in",
)
