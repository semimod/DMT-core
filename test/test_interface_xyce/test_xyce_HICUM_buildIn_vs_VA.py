""" test ADS input file generation, copy to server, run simulation and copy back
"""
import types
import logging
import numpy as np
from pathlib import Path

from DMT.core import DutType, Sweep, specifiers, SimCon, Plot, MCard
from DMT.core.circuit import (
    Circuit,
    CircuitElement,
    RESISTANCE,
    CAPACITANCE,
    SHORT,
    VOLTAGE,
    HICUML2_HBT,
)

from DMT.xyce import DutXyce

folder_path = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_xyce_hicum.log",
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
    if use_build_in:
        module_name = HICUML2_HBT
    else:
        module_name = self.default_module_name  # should be "hicuml2va" because vae

    node_emitter = next(f"n_{node.upper()}" for node in self.nodes_list if "E" in node.upper())
    node_base = next(f"n_{node.upper()}" for node in self.nodes_list if "B" in node.upper())
    node_collector = next(f"n_{node.upper()}" for node in self.nodes_list if "C" in node.upper())
    node_substrate = next(f"n_{node.upper()}" for node in self.nodes_list if "S" in node.upper())
    node_temperature = next(f"n_{node.upper()}" for node in self.nodes_list if "T" in node.upper())

    circuit_elements = []
    # model instance
    circuit_elements.append(
        CircuitElement(
            module_name,
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


def get_dut_build_in():
    modelcard = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=folder_path / "hicuml2v2p4p0_xyce.va",
    )
    modelcard.load_model_parameters(
        folder_path.parent / "test_core_no_interfaces" / "test_modelcards" / "npn_full.lib",
    )
    modelcard.update_from_vae(remove_old_parameters=True)
    modelcard.get_circuit = types.MethodType(get_circuit, modelcard)
    return DutXyce(
        None,
        DutType.npn,
        modelcard,
        name="Xyce_BI_",
        nodes="C,B,E,S,T",
        copy_va_files=True,
        reference_node="E",
        get_circuit_arguments={"use_build_in": True},
    )


def get_dut_va():
    modelcard = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=folder_path / "hicuml2v2p4p0_xyce.va",
    )
    modelcard.load_model_parameters(
        folder_path.parent / "test_core_no_interfaces" / "test_modelcards" / "npn_full.lib",
    )
    modelcard.update_from_vae(remove_old_parameters=True)
    modelcard.get_circuit = types.MethodType(get_circuit, modelcard)
    return DutXyce(
        None,
        DutType.npn,
        modelcard,
        name="Xyce_VA_",
        nodes="C,B,E,S,T",
        copy_va_files=True,
        reference_node="E",
        get_circuit_arguments={"use_build_in": False},
    )


def get_sweep():
    sweepdef = [
        {"var_name": "FREQ", "sweep_order": 4, "sweep_type": "LOG", "value_def": [8, 9, 2]},
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0, 1, 11],
        },
        {
            "var_name": specifiers.VOLTAGE + "C",
            "sweep_order": 3,
            "sweep_type": "SYNC",
            "master": specifiers.VOLTAGE + "B",
            "offset": specifiers.VOLTAGE + ["C", "B"],
        },
        {
            "var_name": specifiers.VOLTAGE + ["C", "B"],
            "sweep_order": 2,
            "sweep_type": "LIST",
            # "value_def": [0.3, 0, -0.3],
            "value_def": [0],
        },
        {
            "var_name": specifiers.VOLTAGE + "E",
            "sweep_order": 1,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    return Sweep(
        "gummel",
        sweepdef=sweepdef,
        outputdef=[specifiers.CURRENT + "C", specifiers.CURRENT + "B"],
        othervar={"TEMP": 300},
    )


def test_run_and_read():

    col_vbc = specifiers.VOLTAGE + ["B", "C"]
    col_vbe = specifiers.VOLTAGE + ["B", "E"]
    col_ib = specifiers.CURRENT + "B"
    col_ic = specifiers.CURRENT + "C"

    duts_test = []
    duts_test.append(get_dut_build_in())
    duts_test.append(get_dut_va())
    sweep_test = get_sweep()

    sim_con = SimCon(t_max=80)  # damn VA-Compile time
    sim_con.append_simulation(dut=duts_test, sweep=sweep_test)
    sim_con.run_and_read(force=True)

    for dut in duts_test:
        dut_name = dut.name[5:7]
        df = dut.get_data(sweep=sweep_test)

        df.ensure_specifier_column(col_vbe, ports=dut.nodes)
        df.ensure_specifier_column(col_vbc, ports=dut.nodes)

        for _index, vbc, data in df.iter_unique_col(col_vbc, decimals=3):
            data = data[data[specifiers.FREQUENCY] == 1e8]

            if "BI" in dut_name:
                vbe_test = np.array(
                    [
                        4.05656424e-26,
                        1.00000000e-01,
                        2.00000000e-01,
                        3.00000000e-01,
                        4.00000000e-01,
                        5.00000000e-01,
                        5.99999999e-01,
                        6.99999968e-01,
                        7.99998848e-01,
                        8.99985196e-01,
                        9.99951196e-01,
                    ]
                )
                ic_test = np.array(
                    [
                        4.05656424e-23,
                        1.04081409e-13,
                        3.92389201e-13,
                        9.13378816e-12,
                        4.02247275e-10,
                        1.80135598e-08,
                        7.84515642e-07,
                        3.20487174e-05,
                        1.14591374e-03,
                        1.47021196e-02,
                        4.81396797e-02,
                    ]
                )
                ib_test = np.array(
                    [
                        -4.05656424e-23,
                        3.25146606e-13,
                        2.20917953e-12,
                        1.66059841e-11,
                        1.32908623e-10,
                        1.10771760e-09,
                        1.02658644e-08,
                        1.34358642e-07,
                        3.03175108e-06,
                        5.07913940e-05,
                        3.31963182e-04,
                    ]
                )
            elif "VA" in dut_name:
                vbe_test = np.array(
                    [
                        4.05656424e-26,
                        1.00000000e-01,
                        2.00000000e-01,
                        3.00000000e-01,
                        4.00000000e-01,
                        5.00000000e-01,
                        5.99999999e-01,
                        6.99999968e-01,
                        7.99998848e-01,
                        8.99985196e-01,
                        9.99951196e-01,
                    ]
                )
                ic_test = np.array(
                    [
                        4.05656424e-23,
                        1.04081409e-13,
                        3.92389201e-13,
                        9.13378816e-12,
                        4.02247275e-10,
                        1.80135598e-08,
                        7.84515642e-07,
                        3.20487174e-05,
                        1.14591374e-03,
                        1.47021196e-02,
                        4.81396797e-02,
                    ]
                )
                ib_test = np.array(
                    [
                        -4.05656424e-23,
                        3.25146606e-13,
                        2.20917953e-12,
                        1.66059841e-11,
                        1.32908623e-10,
                        1.10771760e-09,
                        1.02658644e-08,
                        1.34358642e-07,
                        3.03175108e-06,
                        5.07913940e-05,
                        3.31963182e-04,
                    ]
                )
            else:
                raise NotImplementedError

            assert np.isclose(np.real(data[col_vbe]), vbe_test).all()
            assert np.isclose(np.real(data[col_ic]), ic_test).all()
            assert np.isclose(np.real(data[col_ib]), ib_test).all()

    return duts_test, sweep_test


if __name__ == "__main__":
    duts, sweep = test_run_and_read()

    col_vbc = specifiers.VOLTAGE + ["B", "C"]
    col_vbe = specifiers.VOLTAGE + ["B", "E"]
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

        for _index, vbc, data in df.iter_unique_col(col_vbc, decimals=3):
            data = data[np.isclose(data[specifiers.FREQUENCY], 1e8)]

            plt_gummel.add_data_set(
                np.real(data[col_vbe].to_numpy()),
                np.real(data[col_ic].to_numpy()),
                label=dut_name + " $V_{{BC}} = {0:1.2f} V$".format(data[col_vbc].to_numpy()[0]),
            )
            plt_ib.add_data_set(
                np.real(data[col_vbe].to_numpy()),
                np.real(data[col_ib].to_numpy()),
                label=dut_name + " $V_{{BC}} = {0:1.2f} V$".format(data[col_vbc].to_numpy()[0]),
            )

    plt_ib.plot_pyqtgraph(show=False)
    plt_gummel.plot_pyqtgraph(show=True)
