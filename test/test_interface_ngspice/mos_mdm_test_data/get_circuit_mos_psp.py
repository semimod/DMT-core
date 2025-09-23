from pathlib import Path
from DMT.core import Circuit, CircuitElement
from DMT.core.circuit import RESISTANCE, VOLTAGE, SHORT, CAPACITANCE, SUBCIRCUIT
from DMT.ngspice import DutNgspice
from DMT.xyce import DutXyce


def get_circuit_psp(
    circuit_type,
    modelcard,
    corner="mos_tt",
    flavor="LV",
    type_mos="n",
    width=0.35e-6,
    length=0.13e-6,
    dut_circuit=None,
):
    """
    Currently implemented:

    * 'common_source' : Common source configuration of a PSP MOSFET with temperature and bulk nodes and resistors that represents the parasitic connections to the transistor.

    Parameters
    ----------
    circuit_type : str
        For allowed types, see above
    modelcard : :class:`~DMT.psp.mc_psp.McPsp`
    corner : str, ["mos_tt", "mos_sf", "mos_fs", "mos_ss", "mos_ff"]
        The different corners supported by the PSP model for the IHP pdk.
    flavor : str, ["LV", "HV"]
        Selects between high voltage and low voltage mos flavors.
    type_mos : str, ["n", "p"]
        Selects between nmos and pmos.
    width : float, 0.35e-6
        The MOSFET width in [m].

    Returns
    -------
    circuit : :class:`~DMT.core.circuit.Circuit`
        A circuit that can be simulated with the DMT.DutNgspice interface.

    """
    circuit_elements = []
    circuit_elements.append(f".lib ./cornerMOS{flavor.lower()}_psp.lib {corner}\n")

    dev_str = "nmos"
    if type_mos == "p":
        dev_str = "pmos"

    if circuit_type == "common_source":
        # model instance
        circuit_elements.append(
            CircuitElement(
                SUBCIRCUIT,
                dev_str,
                [
                    "n_D",
                    "n_G",
                    "n_S",
                    "n_B",
                ],
                parameters=[
                    f"sg13_{flavor.lower()}_{dev_str}",
                    ("l", "{0:1.2f}u".format(length * 1e6)),
                    ("w", "{0:1.2f}u".format(width * 1e6)),
                    # TODO add other nmos parameters
                    ("as", "0"),
                    ("ng", "1"),
                    ("m", "1"),
                    ("rfmode", "0"),
                    ("pre_layout", "1"),
                ],
            )
        )

        # GATE NODE CONNECTION #############
        # metal resistance between contact gate and real gate
        try:
            rgm = modelcard.get("_rgm").value
        except KeyError:
            rgm = 1e-3

        circuit_elements.append(
            CircuitElement(RESISTANCE, "Rgm", ["n_G_FORCED", "n_G"], parameters=[("R", str(rgm))])
        )
        # shorts for current measurement
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_G",
                ["n_GX", "n_G_FORCED"],
            )
        )
        # capacitance since AC measurement already removed Rgm
        circuit_elements.append(
            CircuitElement(CAPACITANCE, "Cgm", ["n_G_FORCED", "n_G"], parameters=[("C", str(1e-6))])
        )

        # DRAIN NODE CONNECTION #############
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_D",
                ["n_DX", "n_D_FORCED"],
            )
        )
        # metal resistance between drain contact point and real drain at device level
        try:
            rdm = modelcard.get("_rdm").value
        except KeyError:
            rdm = 1e-3

        circuit_elements.append(
            CircuitElement(RESISTANCE, "Rdm", ["n_D_FORCED", "n_D"], parameters=[("R", str(rdm))])
        )
        # capacitance since AC already removed Rdm
        circuit_elements.append(
            CircuitElement(CAPACITANCE, "Cdm", ["n_D_FORCED", "n_D"], parameters=[("C", str(1e-6))])
        )
        # SOURCE NODE CONNECTION #############
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_S",
                ["n_SX", "n_S_FORCED"],
            )
        )
        # metal resistance between source contact point and real source at device level
        try:
            rsm = modelcard.get("_rsm").value
        except KeyError:
            rsm = 1e-3

        circuit_elements.append(
            CircuitElement(RESISTANCE, "Rsm", ["n_S_FORCED", "n_S"], parameters=[("R", str(rsm))])
        )
        # capacitance since AC already removed Rsm
        circuit_elements.append(
            CircuitElement(CAPACITANCE, "Csm", ["n_S_FORCED", "n_S"], parameters=[("C", str(1e-6))])
        )
        # BULK NODE CONNECTION #############
        circuit_elements.append(
            CircuitElement(
                SHORT,
                "I_B",
                ["n_BX", "n_B_FORCED"],
            )
        )
        # metal resistance between bulk contact point and bulk on device level
        try:
            rbm = modelcard.get("_rbm").value
        except KeyError:
            rbm = 1e-3

        circuit_elements.append(
            CircuitElement(RESISTANCE, "Rbm", ["n_B_FORCED", "n_B"], parameters=[("R", str(rbm))])
        )
        # capacitance since AC already removed Rbm
        circuit_elements.append(
            CircuitElement(CAPACITANCE, "Cbm", ["n_B_FORCED", "n_B"], parameters=[("C", str(1e-6))])
        )
        # VOLTAGE SOURCES ##################
        circuit_elements.append(
            CircuitElement(
                VOLTAGE,
                "V_G",
                ["n_GX", "0"],
                parameters=[("Vdc", "V_G"), ("Vac", "V_G_ac")],
            )
        )
        circuit_elements.append(
            CircuitElement(
                VOLTAGE,
                "V_D",
                ["n_DX", "0"],
                parameters=[("Vdc", "V_D"), ("Vac", "V_D_ac")],
            )
        )
        circuit_elements.append(
            CircuitElement(
                VOLTAGE,
                "V_S",
                ["n_SX", "0"],
                parameters=[("Vdc", "V_S"), ("Vac", "V_S_ac")],
            )
        )
        circuit_elements.append(
            CircuitElement(
                VOLTAGE,
                "V_B",
                ["n_BX", "0"],
                parameters=[("Vdc", "V_B"), ("Vac", "V_B_ac")],
            )
        )

        circuit_elements += [
            "V_G=0",
            "V_D=0",
            "V_S=0",
            "V_B=0",
            "ac_switch=0",
            "V_G_ac=1-ac_switch",
            "V_D_ac=ac_switch",
            "V_B_ac=0",
            "V_S_ac=0",
        ]
    else:
        raise IOError("The circuit type " + circuit_type + " is unknown!")

    file_dir = Path(__file__).parent
    model_files_dir = (
        file_dir
        / "ihp_sg13g2_compact_models-main-model_files"
        / {DutNgspice: "ngspice", DutXyce: "xyce"}[dut_circuit]
    )
    pdk_parameter_files = [
        model_files_dir / f"MOS{flavor}" / f"sg13g2_mos{flavor.lower()}_psp_mod.lib",
        model_files_dir / f"MOS{flavor}" / f"sg13g2_mos{flavor.lower()}_psp_parm_nmos.scs",
        model_files_dir / f"MOS{flavor}" / f"sg13g2_mos{flavor.lower()}_psp_parm_pmos.scs",
        model_files_dir / f"MOS{flavor}" / f"sg13g2_mos{flavor.lower()}_psp_stat.scs",
        model_files_dir / f"MOS{flavor}" / f"cornerMOS{flavor.lower()}_psp.lib",
    ]

    va_root_files = []
    if dut_circuit == DutNgspice:
        va_root_files.append(file_dir / "va_code_psp103p6" / "psp103_nqs.va")
    return Circuit(
        circuit_elements,
        lib_files=pdk_parameter_files,
        va_root_files=va_root_files,
    )
