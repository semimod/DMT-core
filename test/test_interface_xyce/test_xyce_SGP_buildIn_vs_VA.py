""" test ADS input file generation, copy to server, run simulation and copy back

"""
import types
import logging
import numpy as np
from pathlib import Path

from DMT.core import DutType, Sweep, specifiers, SimCon, Plot, MCard, VAFile
from DMT.core.circuit import (
    Circuit,
    CircuitElement,
    RESISTANCE,
    CAPACITANCE,
    SHORT,
    VOLTAGE,
    SGP_BJT,
)
from DMT.xyce import DutXyce


folder_path = Path(__file__).resolve().parent
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_xyce_sgp.log",
    filemode="w",
)


def get_circuit(self, use_build_in=False, **kwargs):
    """Returns a circuit which uses the modelcard to which the method is attached.

    Parameter
    ------------
    use_build_in : bool
        Choose which model to use.

    Returns
    -------
    circuit : :class:`~DMT.core.circuit.Circuit`

    """
    if use_build_in:
        module_name = SGP_BJT
    else:
        module_name = self.default_module_name  # should be "bjtn" because vae

    node_emitter = next(f"n_{node.upper()}" for node in self.nodes_list if "E" in node.upper())
    node_base = next(f"n_{node.upper()}" for node in self.nodes_list if "B" in node.upper())
    node_collector = next(f"n_{node.upper()}" for node in self.nodes_list if "C" in node.upper())

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

    # BASE NODE CONNECTION #############
    # metal resistance between contact base point and real collector
    try:
        rbm = self.get("_rbm").value
    except KeyError:
        rbm = 1e-3

    circuit_elements.append(
        CircuitElement(RESISTANCE, "Rbm", ["n_B_FORCED", node_base], parameters=[("R", str(rbm))])
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
        CircuitElement(CAPACITANCE, "Cbm", ["n_B_FORCED", node_base], parameters=[("C", str(1))])
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
        CircuitElement(CAPACITANCE, "Cem", ["n_E_FORCED", node_emitter], parameters=[("C", str(1))])
    )
    # add sources and thermal resistance
    circuit_elements.append(
        CircuitElement(
            VOLTAGE, "V_B", ["n_BX", "0"], parameters=[("Vdc", "V_B"), ("Vac", "V_B_ac")]
        )
    )
    circuit_elements.append(
        CircuitElement(
            VOLTAGE, "V_C", ["n_CX", "0"], parameters=[("Vdc", "V_C"), ("Vac", "V_C_ac")]
        )
    )
    circuit_elements.append(
        CircuitElement(
            VOLTAGE, "V_E", ["n_EX", "0"], parameters=[("Vdc", "V_E"), ("Vac", "V_E_ac")]
        )
    )

    # metal resistance between contact emitter potential and substrate contact
    if len(self.nodes_list) > 3:
        node_substrate = next(
            f"n_{node.upper()}" for node in self.nodes_list if "S" in node.upper()
        )

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
    circuit_elements += [
        "V_B=0",
        "V_C=0",
        "V_E=0",
        "ac_switch=0",
        "V_B_ac=1-ac_switch",
        "V_C_ac=ac_switch",
        "V_E_ac=0",
    ]

    return Circuit(circuit_elements)


def get_dut_build_in():
    modelcard = MCard(
        ["c", "b", "e", "s"],
        "QSGP1",
        SGP_BJT,
        1.0,
        va_file=folder_path / "sgp_v1p0.va",
    )
    modelcard.default_module_name = SGP_BJT
    modelcard.get_circuit = types.MethodType(get_circuit, modelcard)
    modelcard.load_model_parameters(folder_path / "bjt.lib")
    return DutXyce(
        None,
        DutType.npn,
        modelcard,
        name="Xyce_BI_",
        nodes="C,B,E",
        copy_va_files=True,
        reference_node="E",
        get_circuit_arguments={"use_build_in": True},
    )


def get_dut_va():
    modelcard = MCard(
        ["c", "b", "e", "s"],
        "QSGP2",
        SGP_BJT,
        1.0,
        va_file=folder_path / "sgp_v1p0.va",
    )
    modelcard.get_circuit = types.MethodType(get_circuit, modelcard)
    modelcard.load_model_parameters(folder_path / "bjt.lib")
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
        {"var_name": "FREQ", "sweep_order": 4, "sweep_type": "LOG", "value_def": [6, 7, 11]},
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
            data = data[data[specifiers.FREQUENCY] == 1e7]

            if "BI" in dut_name:
                vbe_test = np.array(
                    [
                        5.58161701e-41,
                        1.00000000e-01,
                        2.00000000e-01,
                        3.00000000e-01,
                        4.00000000e-01,
                        5.00000000e-01,
                        6.00000000e-01,
                        6.99999997e-01,
                        7.99999882e-01,
                        8.99996453e-01,
                        9.99979245e-01,
                    ]
                )
                ic_test = np.array(
                    [
                        -1.46936794e-39,
                        9.72598538e-14,
                        2.00083790e-13,
                        8.32249178e-13,
                        2.62352010e-11,
                        1.19704585e-09,
                        5.52532891e-08,
                        2.54706085e-06,
                        1.15610970e-04,
                        3.46916517e-03,
                        2.00870352e-02,
                    ]
                )
                ib_test = np.array(
                    [
                        -2.71176588e-38,
                        5.56179733e-15,
                        3.10153077e-14,
                        1.62060498e-13,
                        1.02019426e-12,
                        1.45616330e-11,
                        5.22082372e-10,
                        2.40877044e-08,
                        1.13533053e-06,
                        3.87381699e-05,
                        3.34227460e-04,
                    ]
                )
            elif "VA" in dut_name:
                vbe_test = np.array(
                    [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.79999988, 0.89999645, 0.99997925]
                )
                ic_test = np.array(
                    [
                        0.00000000e00,
                        1.00254762e-13,
                        2.12063425e-13,
                        8.59203354e-13,
                        2.62831194e-11,
                        1.19712072e-09,
                        5.52533967e-08,
                        2.54706098e-06,
                        1.15610969e-04,
                        3.46915636e-03,
                        2.00867109e-02,
                    ]
                )
                ib_test = np.array(
                    [
                        0.00000000e00,
                        1.04817715e-13,
                        2.29527142e-13,
                        4.59828250e-13,
                        1.41721793e-12,
                        1.50579126e-11,
                        5.22677906e-10,
                        2.40883991e-08,
                        1.13533131e-06,
                        3.87380622e-05,
                        3.34219784e-04,
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
            data = data[data[specifiers.FREQUENCY] == 1e7]

            plt_gummel.add_data_set(
                data[col_vbe],
                data[col_ic],
                label=dut_name + " $V_{{BC}} = {0:1.2f} V$".format(data[col_vbc].to_numpy()[0]),
            )
            plt_ib.add_data_set(
                data[col_vbe],
                data[col_ib],
                label=dut_name + " $V_{{BC}} = {0:1.2f} V$".format(data[col_vbc].to_numpy()[0]),
            )

    plt_ib.plot_pyqtgraph(show=False)
    plt_gummel.plot_pyqtgraph(show=True)
