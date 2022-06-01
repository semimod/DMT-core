""" Python script which is explained in detail in the introduction.
Here the commands are repeated to be able to test them.
"""
from pathlib import Path
from DMT import core


path_data = Path(__file__).resolve().parent.parent / "_static" / "intro"

dut_meas = core.DutMeas(
    database_dir=None,  # Use dir from config
    dut_type=core.DutType.npn,  # it is a BJT-npn
    width=float(1e-6),
    length=float(2e-6),
    name="dut_meas_npn",  # name and width/length for documentation
    reference_node="E",  # defines configuration
)
key_saved = "300K/iv"
dut_meas.add_data(path_data / "meas_data_300K.csv", key=key_saved)
dut_meas.clean_data(fallback={"E_": "E"})

print(dut_meas.data[key_saved].columns)
# V_c, V_E, V_B, I_E_, I_C, I_b, FREQ, Y_21, Y_11, Y22, Y_12

modelcard = core.MCard(
    ["c", "b", "e", "s"],
    "QSGP1",
    core.circuit.SGP_BJT,
    1.0,
    va_file=path_data / "sgp_v1p0.va",
)
modelcard.load_model_parameters(path_data / "bjt.lib")


def get_circuit(self):
    """Returns a circuit which uses the modelcard to which the method is attached.

    Returns
    -------
    circuit : :class:`~DMT.core.circuit.Circuit`

    """
    circuit_elements = []
    # model instance
    circuit_elements.append(
        core.circuit.CircuitElement(
            self.default_module_name,
            self.default_subckt_name,
            [f"n_{node.upper()}" for node in self.nodes_list],
            # ["n_C", "n_B", "n_E"],
            parameters=self,
        )
    )

    # BASE NODE CONNECTION #############
    # shorts for current measurement
    circuit_elements.append(
        core.circuit.CircuitElement(core.circuit.SHORT, "I_B", ["n_B_FORCED", "n_B"])
    )
    # COLLECTOR NODE CONNECTION #############
    circuit_elements.append(
        core.circuit.CircuitElement(core.circuit.SHORT, "I_C", ["n_C_FORCED", "n_C"])
    )
    # EMITTER NODE CONNECTION #############
    circuit_elements.append(
        core.circuit.CircuitElement(core.circuit.SHORT, "I_E", ["n_E_FORCED", "n_E"])
    )
    # add sources
    circuit_elements.append(
        core.circuit.CircuitElement(
            core.circuit.VOLTAGE,
            "V_B",
            ["n_B_FORCED", "0"],
            parameters=[("Vdc", "V_B"), ("Vac", "V_B_ac")],
        )
    )
    circuit_elements.append(
        core.circuit.CircuitElement(
            core.circuit.VOLTAGE,
            "V_C",
            ["n_C_FORCED", "0"],
            parameters=[("Vdc", "V_C"), ("Vac", "V_C_ac")],
        )
    )
    circuit_elements.append(
        core.circuit.CircuitElement(
            core.circuit.VOLTAGE,
            "V_E",
            ["n_E_FORCED", "0"],
            parameters=[("Vdc", "V_E"), ("Vac", "V_E_ac")],
        )
    )

    # metal resistance between contact emitter potential and substrate contact
    circuit_elements.append(
        core.circuit.CircuitElement(
            core.circuit.RESISTANCE, "R_S", ["n_S", "n_E_FORCED"], parameters=[("R", str(0.5))]
        )
    )

    # some variables used in this circuit
    circuit_elements += [
        "V_B=0",
        "V_C=0",
        "V_E=0",
        "ac_switch=0",
        "V_B_ac=1-ac_switch",
        "V_C_ac=ac_switch",
        "V_E_ac=0",
    ]

    return core.circuit.Circuit(circuit_elements)


import types

modelcard.get_circuit = types.MethodType(get_circuit, modelcard)


from DMT.xyce import DutXyce

dut_sim = DutXyce(
    None,
    core.DutType.npn,
    modelcard,
    nodes="B,C,E",
    reference_node="E",
)

# from DMT.ngspice import DutNgspice

# dut_sim = DutNgspice(
#     None,
#     core.DutType.npn,
#     modelcard,
#     nodes="B,C,E",
#     reference_node="E",
# )


sweep = core.Sweep.get_sweep_from_dataframe(dut_meas.data[key_saved], temperature=300)


sim_con = core.SimCon()
sim_con.append_simulation(dut=dut_sim, sweep=sweep)
sim_con.run_and_read()

data_meas = dut_meas.data[key_saved]
data_sim = dut_sim.get_data(sweep=sweep)

col_vbe = core.specifiers.VOLTAGE + ["B", "E"]
col_vbc = core.specifiers.VOLTAGE + ["B", "C"]
col_ic = core.specifiers.CURRENT + "C"
col_freq = core.specifiers.FREQUENCY
col_ft = core.specifiers.TRANSIT_FREQUENCY
col_y21_real = core.specifiers.SS_PARA_Y + ["C", "B"] + core.sub_specifiers.REAL

for dut, data in zip([dut_meas, dut_sim], [data_meas, data_sim]):
    data.ensure_specifier_column(col_vbe)
    data.ensure_specifier_column(col_vbc)
    data.ensure_specifier_column(col_ft, ports=dut.ac_ports)
    data.ensure_specifier_column(col_y21_real, ports=dut.ac_ports)

# Plot and save as pdf
plt_ic = core.Plot(
    plot_name="I_C(V_BE)",
    x_specifier=col_vbe,
    y_specifier=col_ic,
    y_scale=1e3,
    y_log=True,
    legend_location="lower right",
)
plt_y21 = core.Plot(
    plot_name="Y_21(I_C)",
    x_specifier=col_ic,
    x_scale=1e3,
    x_log=True,
    y_specifier=col_y21_real,
    y_scale=1e3,
    y_log=True,
    legend_location="lower right",
)
plt_ft = core.Plot(
    plot_name="F_T(I_C)",
    x_specifier=col_ic,
    x_scale=1e3,
    x_log=True,
    y_specifier=col_ft,
    legend_location="upper left",
)

import numpy as np

for source, data in zip(["meas", "sim"], [data_meas, data_sim]):
    for i_vbc, vbc, data_vbc in data.iter_unique_col(col_vbc, decimals=3):
        data_freq = data_vbc[np.isclose(data_vbc[col_freq], 1e7)]
        plt_ic.add_data_set(
            data_freq[col_vbe],
            data_freq[col_ic],
            label=source + " " + col_vbc.to_legend_with_value(vbc),
        )
        plt_y21.add_data_set(
            data_freq[col_ic],
            data_freq[col_y21_real],
            label=source + " " + col_vbc.to_legend_with_value(vbc),
        )
        plt_ft.add_data_set(
            data_freq[col_ic],
            data_freq[col_ft],
            label=source + " " + col_vbc.to_legend_with_value(vbc),
        )

plt_ic.plot_pyqtgraph(show=False)
plt_y21.plot_pyqtgraph(show=False)
plt_ft.plot_pyqtgraph(show=True)

# plt_ic.plot_py(show=False, use_tex=False)
# plt_y21.plot_py(show=False, use_tex=False)
# plt_ft.plot_py(show=True, use_tex=False)

# plt_ic.save_tikz(path_data, standalone=True, build=True, clean=True, width="3in")
# plt_y21.save_tikz(path_data, standalone=True, build=True, clean=True, width="3in")
# plt_ft.save_tikz(path_data, standalone=True, build=True, clean=True, width="3in")
