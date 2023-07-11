"""

1D schalten mit HICUM
Konvergenz bei vergleich von flnqs = 0/1

"""
import copy
import types
import logging
import numpy as np
from pathlib import Path
from DMT.config import COMMANDS

COMMANDS["OPENVAF"] = "openvaf"
from DMT.core import specifiers, DutType, SimCon, Sweep, Plot, MCard
from DMT.core.sweep_def import (
    SweepDefConst,
    SweepDefSync,
    SweepDefTransSinus,
    SweepDefTransRamp,
)
from DMT.core.circuit import (
    Circuit,
    CircuitElement,
    RESISTANCE,
    CAPACITANCE,
    SHORT,
    VOLTAGE,
    HICUML2_HBT,
)

from DMT.ngspice import DutNgspice

folder_path = Path(__file__).resolve().parent


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
    mcard = copy.deepcopy(self)
    if use_build_in:
        mcard._va_codes = None
        mcard.default_module_name = HICUML2_HBT

    node_emitter = next(f"n_{node.upper()}" for node in mcard.nodes_list if "E" in node.upper())
    node_base = next(f"n_{node.upper()}" for node in mcard.nodes_list if "B" in node.upper())
    node_collector = next(f"n_{node.upper()}" for node in mcard.nodes_list if "C" in node.upper())
    node_substrate = next(f"n_{node.upper()}" for node in mcard.nodes_list if "S" in node.upper())
    node_temperature = next(f"n_{node.upper()}" for node in mcard.nodes_list if "T" in node.upper())

    circuit_elements = []
    # model instance
    circuit_elements.append(
        CircuitElement(
            mcard.default_module_name,
            "Q_H",
            [f"n_{node.upper()}" for node in mcard.nodes_list],
            # ["n_C", "n_B", "n_E"],
            parameters=mcard,
        )
    )

    if topology == "common_emitter":
        # BASE NODE CONNECTION #############
        # metal resistance between contact base point and real collector
        try:
            rbm = mcard.get("_rbm").value
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
            rcm = mcard.get("_rcm").value
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
            rem = mcard.get("_rem").value
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
        if len(mcard.nodes_list) > 3:
            circuit_elements.append(
                CircuitElement(
                    SHORT,
                    "I_S",
                    ["n_SX", node_substrate],
                )
            )
            try:
                rsm = mcard.get("_rsm").value
            except KeyError:
                rsm = 5
            circuit_elements.append(
                CircuitElement(RESISTANCE, "R_S", ["n_SX", "n_EX"], parameters=[("R", str(rsm))])
            )
        if len(mcard.nodes_list) > 4:
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


col_time = specifiers.TIME
col_vb = specifiers.VOLTAGE + "B"
col_vc = specifiers.VOLTAGE + "C"
col_ve = specifiers.VOLTAGE + "E"


def get_dut():
    mc_D21 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=folder_path.parent
        / "test_core_no_interfaces"
        / "test_va_code"
        / "hicuml2"
        / "hicumL2V2p4p0_release.va",
    )
    mc_D21.load_model_parameters(
        folder_path.parent
        / "test_core_no_interfaces"
        / "test_modelcards"
        / "IHP_ECE704_03_para_D21.mat",
    )
    mc_D21.update_from_vae(remove_old_parameters=True)
    mc_D21.get_circuit = types.MethodType(get_circuit, mc_D21)

    return DutNgspice(
        None,
        DutType.npn,
        input_circuit=mc_D21,
        reference_node="E",
        copy_va_files=True,
        simulator_command="ngspice",
    )


def get_sweep():
    frequencies = 1e9 * np.array([1])
    return Sweep(
        "test",
        sweepdef=[
            SweepDefTransSinus(
                value_def=frequencies, amp=25e-3, phase=0, contact="B", sweep_order=2
            ),
            SweepDefSync(col_vc, master=col_vb, offset=0, sweep_order=1),
            SweepDefConst(col_vb, value_def=0.87, sweep_order=1),
            SweepDefConst(col_ve, value_def=0, sweep_order=0),
        ],
        outputdef=["OpVar"],
        othervar={specifiers.TEMPERATURE: 300},
    )


if __name__ == "__main__":
    dut_HICUM = get_dut()
    sweep = get_sweep()

    sim_con = SimCon(n_core=1, t_max=1000)
    sim_con.append_simulation(dut=dut_HICUM, sweep=sweep)
    sim_con.run_and_read(force=True)

    i_op = 0
    i_freq = 0
    df = dut_HICUM.get_data(sweep=sweep, key=f"tr_{i_op}_{i_freq}")

    plt = Plot("i_c(t)")
    plt.add_data_set(df[specifiers.TIME], df[specifiers.VOLTAGE + "B"], label="V_B")
    plt.add_data_set(df[specifiers.TIME], df[specifiers.CURRENT + "C"], label="I_C")

    plt.plot_pyqtgraph()
