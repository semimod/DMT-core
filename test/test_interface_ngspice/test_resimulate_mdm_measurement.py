"""
Resimulate a mdm measurement with ngspice

Try to read additional data from the measurement (like device variables)
"""

# this file runs an initial ngspice simulation using the IHP HBT models to see if they work in ngspice
from pathlib import Path
from DMT.core import (
    DutType,
    specifiers,
    sub_specifiers,
    SimCon,
    Plot,
    MCard,
    constants,
    read_data,
    get_sweepdef,
    Sweep,
)
from mos_mdm_test_data.get_circuit_mos_psp import get_circuit_psp
from DMT.core.sweep_def import SweepDefConst
from DMT.ngspice import DutNgspice
from DMT.xyce import DutXyce

test_dir = Path(__file__).parent.parent

duts_circuit = [DutNgspice, DutXyce]
show = True  # If True: open plots and visualize them
force = False  # If True: re-run simulations even if the simulation results already exist
flavor = "LV"  # HV or LV MOS flavors
type_channel = "n"
factor_v = 1 if type_channel == "n" else -1

sp_vg = specifiers.VOLTAGE + "G"
sp_vd = specifiers.VOLTAGE + "D"
sp_vb = specifiers.VOLTAGE + "B"
sp_vs = specifiers.VOLTAGE + "S"
sp_id = specifiers.CURRENT + "D"
sp_ig = specifiers.CURRENT + "G"
sp_ib = specifiers.CURRENT + "B"
sp_is = specifiers.CURRENT + "S"


def read_mdm_data_and_clean():
    df = read_data(
        test_dir
        / "test_interface_ngspice"
        / "mos_mdm_test_data"
        / "SG13_nmos~W05u0_L0u13_S542_1~dc_idvd_vbmin~300K.mdm"
    )
    df = df.clean_data(["D", "G", "S", "B"], "S", ac_ports=["D", "G"])

    return df


def get_modelcard(dut_circuit):
    # define a modelcard for the MOS
    mc = MCard(
        ["G", "S", "D", "B"],
        "npn13G2",
        "common_source",
        1.0,
    )

    w = 5e-6
    l = 130e-9
    # TODO possible location for
    # w,l, <other_parameters> = read_mdm_header(
    # test_dir
    # / "test_interface_ngspice"
    # / "mos_mdm_test_data"
    # / "SG13_nmos~W05u0_L0u13_S542_1~dc_idvd_vbmin~300K.mdm")
    # )

    return get_circuit_psp(
        circuit_type="common_source",
        modelcard=mc,
        type_mos="n",
        flavor="LV",
        corner="mos_tt",
        width=w,
        length=l,
        dut_circuit=dut_circuit,
    )


def get_device(dut_circuit):
    modelcard = get_modelcard(dut_circuit)
    # define a device that combines all the previously defined objects
    return dut_circuit(
        None,
        DutType.n_mos,
        modelcard,
        nodes="D,G,S,B",
        command_openvaf="openvaf",
        reference_node="S",
    )


def get_sweep(df_meas):
    # workaround for get_sweepdef with 4 terminals:
    del df_meas[sp_vb]
    sweepdefs = get_sweepdef(df_meas)
    df_meas[sp_vb] = -1.2

    sweepdefs[1].sweep_order = 2
    sweepdefs[2].sweep_order = 3
    sweepdefs.insert(1, SweepDefConst(sp_vb, -1.2, 1))
    return Sweep(
        "resim_meas",
        sweepdef=sweepdefs,
        othervar={specifiers.TEMPERATURE: 300},
    )


def run_simulation(device, sweep):
    sim_con = SimCon(n_core=1)
    sim_con.append_simulation(device, sweep)
    sim_con.run_and_read()


def test_comp_sim_meas():
    data_meas = read_mdm_data_and_clean()
    sweep = get_sweep(data_meas)

    for dut_circuit, desciption in simulators.items():
        device = get_device(dut_circuit)
        run_simulation(device, sweep)
        data_sim = device.get_data(sweep=sweep)
        # asserts not usefull since measurement and simulation data do not agree currently


if __name__ == "__main__":
    # define plots
    plt_idvd = Plot(
        r"idvd",
        x_specifier=sp_vd,
        y_specifier=sp_id,
        style="mix",
        legend_location="upper left",
    )

    simulators = {
        DutNgspice: "ngspice/OSDI",
        # DutXyce: "xyce", # TODO not tested
    }

    data_meas = read_mdm_data_and_clean()

    for i_vg, v_g, data_vg in data_meas.iter_unique_col(sp_vg):
        label = sp_vg.to_legend_with_value(v_g)
        plt_idvd.add_data_set(data_vg[sp_vd], data_vg[sp_id], label="meas @ " + label)

    sweep = get_sweep(data_meas)
    for dut_circuit, desciption in simulators.items():
        device = get_device(dut_circuit)
        run_simulation(device, sweep)
        data_sim = device.get_data(sweep=sweep)

        for i_vg, v_g, data_vg in data_sim.iter_unique_col(sp_vg):
            label = sp_vg.to_legend_with_value(v_g)
            plt_idvd.add_data_set(data_vg[sp_vd], data_vg[sp_id], label=desciption + " @ " + label)

    plt_idvd.plot_pyqtgraph()
