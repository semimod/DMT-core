""" test ADS input file generation, copy to server, run simulation and copy back

USING VerilogAE to obtain the SPG modelcard!
-> needs to be installed and call:

verilogae install --module-name sgp_v1p0 DMT_other/DMT/hl2/sgp_v1p0_vae.va

"""
import types
import logging

from pathlib import Path
from DMT.core import DutType, Sweep, specifiers, SimCon, Plot, MCard
from DMT.core.circuit import SGP_BJT
from DMT.hl2 import VA_FILES, sgp_default_circuits
from DMT.xyce import DutXyce
from DMT.spectre import DutSpectre

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_xyce_vs_spectre.log",
    filemode="w",
)


def get_circuit(self):
    return sgp_default_circuits.get_circuit(self.default_circuit, self)


def get_spg_mc():
    modelcard = MCard(
        sgp_v1p0.nodes,
        "QSGP",
        SGP_BJT,
        1.1,
        vae_module=sgp_v1p0,
        default_circuit="common_emitter",
    )
    modelcard.default_module_name = SGP_BJT  # it is set from the vae_module to something different :/ -> this is intentional and usually pretty good
    modelcard.get_circuit = types.MethodType(
        get_circuit, modelcard
    )  # we need to bind here, this is a little tricky -.-
    modelcard.load_model_parameters(folder_path / "bjt.lib")

    # modelcard.set_values(
    #     {"is": 1e-16,}
    # )

    return modelcard


def get_dut_xyce_build_in():
    modelcard = get_spg_mc()

    return DutXyce(
        None,
        DutType.npn,
        modelcard,
        name="Xyce_BI_",
        nodes="C,B,E",
        copy_va_files=False,
        reference_node="E",
    )


def get_dut_xyce_va():
    modelcard = get_spg_mc()
    modelcard.va_file = VA_FILES["SGPV1.0"]
    modelcard.vae_module = sgp_v1p0  # parse!
    return DutXyce(
        None,
        DutType.npn,
        modelcard,
        name="Xyce_VA_",
        nodes="C,B,E",
        copy_va_files=True,
        reference_node="E",
    )


def get_dut_spectre_build_in():
    modelcard = get_spg_mc()
    return DutSpectre(
        None,
        DutType.npn,
        modelcard,
        name="Spec_BI_",
        nodes="C,B,E",
        copy_va_files=False,
        reference_node="E",
        simulate_on_server=True,
    )


def get_dut_spectre_va():
    modelcard = get_spg_mc()
    modelcard.va_file = VA_FILES["SGPV1.0"]
    modelcard.vae_module = sgp_v1p0  # parse!
    return DutSpectre(
        None,
        DutType.npn,
        modelcard,
        name="Spec_VA_",
        nodes="C,B,E",
        copy_va_files=True,
        reference_node="E",
        simulate_on_server=True,
    )


def get_sweep():
    sweepdef = [
        {"var_name": "FREQ", "sweep_order": 4, "sweep_type": "LOG", "value_def": [8, 9, 2]},
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0, 1, 21],
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
            "value_def": [0.3, 0, -0.3],
            # "value_def": [0],
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


def run_and_read(dut_test, sweep_test):
    sim_con = SimCon(t_max=80)  # damn VA-Compile time
    sim_con.append_simulation(dut=dut_test, sweep=sweep_test)
    sim_con.run_and_read(force=True)


if __name__ == "__main__":
    duts = []
    duts.append(get_dut_spectre_build_in())
    # duts.append(get_dut_xyce_build_in())
    # duts.append(get_dut_xyce_va())
    duts.append(get_dut_spectre_va())
    sweep = get_sweep()

    run_and_read(duts, sweep)

    col_vbc = specifiers.VOLTAGE + ["B", "C"]
    col_vbe = specifiers.VOLTAGE + ["B", "E"]
    col_ib = specifiers.CURRENT + "B"
    col_ic = specifiers.CURRENT + "C"

    plt_gummel = Plot(
        r"$I_{\mathrm{C}}(V_{\mathrm{BE}})$",
        x_label=r"$V_{\mathrm{BE}}$",
        y_label=r"$I_{\mathrm{C}}$",
        y_log=True,
        style="xtraction_color",
    )
    plt_ib = Plot(
        r"$I_{\mathrm{B}}(V_{\mathrm{BE}})$",
        x_label=r"$V_{\mathrm{BE}}$",
        y_label=r"$I_{\mathrm{B}}$",
        y_log=True,
        style="xtraction_color",
    )

    for dut in duts:
        dut_name = dut.name[:7]
        df = dut.get_data(sweep=sweep)

        df.ensure_specifier_column(col_vbe, ports=dut.nodes)
        df.ensure_specifier_column(col_vbc, ports=dut.nodes)

        for _index, vbc, data in df.iter_unique_col(col_vbc, decimals=3):
            data = data[data[specifiers.FREQUENCY] == 1e8]

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
