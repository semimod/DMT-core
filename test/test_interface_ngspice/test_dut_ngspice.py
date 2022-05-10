""" test ngspice input file generation.
"""
import types
import logging
from pathlib import Path
from DMT.core import DutType, Sweep, specifiers, SimCon, Plot, MCard
from DMT.core.circuit import Circuit, CircuitElement, RESISTANCE, CAPACITANCE, SHORT, VOLTAGE

from DMT.ngspice import DutNgspice
import numpy as np

folder_path = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_ngspice.log",
    filemode="w",
)


def get_circuit(self, use_build_in=False, topology="common_emitter", **kwargs):
    """

    Parameter
    ------------
    circuit_type : str
        For allowed types, see above
    modelcard : :class:`~DMT.hl2.mc_hicum.McHicum`

    Returns
    -------
    circuit : :class:`~DMT.core.circuit.Circuit`

    """
    node_emitter = next(f"n_{node.upper()}" for node in self.nodes_list if "E" in node.upper())
    node_base = next(f"n_{node.upper()}" for node in self.nodes_list if "B" in node.upper())
    node_collector = next(f"n_{node.upper()}" for node in self.nodes_list if "C" in node.upper())
    node_substrate = next(f"n_{node.upper()}" for node in self.nodes_list if "S" in node.upper())
    node_temperature = next(f"n_{node.upper()}" for node in self.nodes_list if "T" in node.upper())

    circuit_elements = []
    # model instance
    circuit_elements.append(
        CircuitElement(
            self.default_module_name,
            "Q_H",
            [f"n_{node.upper()}" for node in self.nodes_list],
            # ["n_C", "n_B", "n_E"],
            parameters=self,
        )
    )

    if topology == "common_emitter":

        # BASE NODE CONNECTION #############
        # metal resistance between contact base point and real collector
        try:
            rbm = self.get("_rbm").value
        except KeyError:
            rbm = 1e-3

        circuit_elements.append(
            CircuitElement(
                RESISTANCE, "Rbm", ["n_B_FORCED", node_base], parameters=[("R", str(rbm))]
            )
        )
        # shorts for current measurement
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_B",
                ["n_BX", "n_B_FORCED"],
            )
        )
        # capacitance since AC already deembeded Rbm
        circuit_elements.append(
            CircuitElement(
                CAPACITANCE, "Cbm", ["n_B_FORCED", node_base], parameters=[("C", str(1))]
            )
        )

        # COLLECTOR NODE CONNECTION #############
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_C",
                ["n_CX", "n_C_FORCED"],
            )
        )
        # metal resistance between contact collector point and real collector
        try:
            rcm = self.get("_rcm").value
        except KeyError:
            rcm = 1e-3

        circuit_elements.append(
            CircuitElement(
                RESISTANCE, "Rcm", ["n_C_FORCED", node_collector], parameters=[("R", str(rcm))]
            )
        )
        # capacitance since AC already deembeded Rcm
        circuit_elements.append(
            CircuitElement(
                CAPACITANCE, "Ccm", ["n_C_FORCED", node_collector], parameters=[("C", str(1))]
            )
        )
        # EMITTER NODE CONNECTION #############
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_E",
                ["n_EX", "n_E_FORCED"],
            )
        )
        # metal resistance between contact emiter point and real emiter
        try:
            rem = self.get("_rem").value
        except KeyError:
            rem = 1e-3

        circuit_elements.append(
            CircuitElement(
                RESISTANCE, "Rem", ["n_E_FORCED", node_emitter], parameters=[("R", str(rem))]
            )
        )
        # capacitance since AC already deembeded Rcm
        circuit_elements.append(
            CircuitElement(
                CAPACITANCE, "Cem", ["n_E_FORCED", node_emitter], parameters=[("C", str(1))]
            )
        )
        # add sources and thermal resistance
        circuit_elements.append(
            CircuitElement(VOLTAGE, "V_B", ["n_BX", "0"], parameters=[("Vdc", "V_B"), ("Vac", "1")])
        )
        circuit_elements.append(
            CircuitElement(VOLTAGE, "V_C", ["n_CX", "0"], parameters=[("Vdc", "V_C"), ("Vac", "1")])
        )
        circuit_elements.append(
            CircuitElement(VOLTAGE, "V_E", ["n_EX", "0"], parameters=[("Vdc", "V_E"), ("Vac", "1")])
        )

        # metal resistance between contact emitter potential and substrate contact
        if len(self.nodes_list) > 3:
            circuit_elements.append(
                CircuitElement(
                    SHORT,
                    "I_S",
                    ["n_SX", node_substrate],
                )
            )
            try:
                rsm = self.get("_rsm").value
            except KeyError:
                rsm = 5
            circuit_elements.append(
                CircuitElement(RESISTANCE, "R_S", ["n_SX", "n_EX"], parameters=[("R", str(rsm))])
            )
        if len(self.nodes_list) > 4:
            circuit_elements.append(
                CircuitElement(
                    RESISTANCE, "R_t", [node_temperature, "0"], parameters=[("R", "1e9")]
                )
            )
        circuit_elements += [
            "V_B=0",
            "V_C=0",
            "V_S=0",
            "V_E=0",
            "ac_switch=0",
            "V_B_ac=1-ac_switch",
            "V_C_ac=ac_switch",
            "V_S_ac=0",
            "V_E_ac=0",
        ]
    else:
        raise IOError("The circuit type " + topology + " is unknown!")

    return Circuit(circuit_elements)


def test_ngspice():
    col_vb = specifiers.VOLTAGE + "B"
    col_ib = specifiers.CURRENT + "B"
    col_ic = specifiers.CURRENT + "C"

    mc_D21 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=folder_path.parent / "test_core_no_interfaces" / "hicumL2V2p4p0_release.va",
    )
    mc_D21.load_model_parameters(
        folder_path.parent
        / "test_core_no_interfaces"
        / "test_modelcards"
        / "IHP_ECE704_03_para_D21.mat",
    )
    mc_D21.update_from_vae(remove_old_parameters=True)
    mc_D21.get_circuit = types.MethodType(get_circuit, mc_D21)

    dut = DutNgspice(None, DutType.npn, mc_D21, nodes="C,B,E,S,T", reference_node="E")
    # dut = DutXyce(None, DutType.npn, mc_D21, nodes="C,B,E,S,T", reference_node="E")
    duts = [dut]

    # create a sweep
    sweepdef = [
        {
            "var_name": specifiers.FREQUENCY,
            "sweep_order": 4,
            "sweep_type": "LOG",
            "value_def": [1, 2, 11],
        },
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0.5, 1, 11],
        },
        {
            "var_name": specifiers.VOLTAGE + "C",
            "sweep_order": 2,
            "sweep_type": "CON",
            "value_def": [1],
        },
        {
            "var_name": specifiers.VOLTAGE + "E",
            "sweep_order": 1,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    outputdef = ["I_C", "I_B"]
    othervar = {"TEMP": 300}
    sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

    sim_con = SimCon()

    sim_con.append_simulation(dut=dut, sweep=sweep)
    sim_con.run_and_read(force=True, remove_simulations=False)

    df = dut.get_data(sweep=sweep)
    df = df[np.isclose(df[specifiers.FREQUENCY], 100)]
    vb = np.real(df[col_vb].to_numpy())
    ic = np.real(df[col_ic].to_numpy())
    ib = np.real(df[col_ib].to_numpy())

    assert np.isclose(
        vb,
        np.array(
            [
                0.5,
                0.55,
                0.6,
                0.65,
                0.7,
                0.75,
                0.799999998,
                0.849999988,
                0.899999936,
                0.949999737,
                0.999998983,
            ]
        ),
    ).all()
    assert np.isclose(
        ic,
        np.array(
            [
                1.14418981e-08,
                7.72463409e-08,
                5.2127632e-07,
                3.51490644e-06,
                2.36611728e-05,
                0.000158456473,
                0.00102887822,
                0.00566126767,
                0.0207667184,
                0.0484566543,
                0.06658047,
            ]
        ),
    ).all()
    assert np.isclose(
        ib,
        np.array(
            [
                3.81987775e-11,
                1.86560101e-10,
                1.10651399e-09,
                7.04358172e-09,
                4.57921487e-08,
                2.99428393e-07,
                1.95696248e-06,
                1.22903099e-05,
                6.44306933e-05,
                0.000262592983,
                0.00101685885,
            ]
        ),
    ).all()

    return duts, sweep


if __name__ == "__main__":
    duts, sweep = test_ngspice()

    col_vbc = specifiers.VOLTAGE + ["B", "C"]
    col_vbe = specifiers.VOLTAGE + ["B", "E"]
    col_vce = specifiers.VOLTAGE + ["C", "E"]
    col_ib = specifiers.CURRENT + "B"
    col_ic = specifiers.CURRENT + "C"

    plt_gummel = Plot(
        r"$I_{\mathrm{C}}(V_{\mathrm{BE}})$",
        x_label=r"$V_{\mathrm{BE}}$",
        y_label=r"$I_{\mathrm{C}}$",
        y_log=True,
        style="bw",
    )
    plt_ib = Plot(
        r"$I_{\mathrm{B}}(V_{\mathrm{BE}})$",
        x_label=r"$V_{\mathrm{BE}}$",
        y_label=r"$I_{\mathrm{B}}$",
        y_log=True,
        style="bw",
    )

    for dut in duts:
        dut_name = dut.name[5:7]
        df = dut.get_data(sweep=sweep)

        df.ensure_specifier_column(col_vbe, ports=dut.nodes)
        df.ensure_specifier_column(col_vbc, ports=dut.nodes)
        df.ensure_specifier_column(col_vce, ports=dut.nodes)

        for _index, vce, data in df.iter_unique_col(col_vce, decimals=3):
            data = data[np.isclose(data[specifiers.FREQUENCY], 100)]

            plt_gummel.add_data_set(
                np.real(data[col_vbe].to_numpy()),
                np.real(data[col_ic].to_numpy()),
                label=dut_name + " $V_{{CE}} = {0:1.2f} V$".format(np.real(vce)),
            )
            plt_ib.add_data_set(
                np.real(data[col_vbe].to_numpy()),
                np.real(data[col_ib].to_numpy()),
                label=dut_name + " $V_{{CE}} = {0:1.2f} V$".format(np.real(vce)),
            )

    # plt_ib.plot_pyqtgraph(show=False)
    # plt_gummel.plot_pyqtgraph(show=True)
    plt_ib.plot_py(show=False, use_tex=True)
    plt_gummel.plot_py(show=True, use_tex=False)
