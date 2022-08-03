""" test ADS simulation and plotting of output data.
"""
import time
from pathlib import Path
import logging
import numpy as np
from DMT.core import SimCon, specifiers, DutType, Sweep, Plot, sub_specifiers
from DMT.hl2 import McHicum, VA_FILES
from DMT.ngspice import DutNgspice
from DMT.ADS import DutAds

sim_ngspice = True
sim_ads = True
show = True
force = False

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_ADS_many_sweeps.log",
    filemode="w",
)


def compare_ngspice_many_sweeps():
    # get HICUM model
    mc_D21 = McHicum(
        va_file=test_path
        / "test_core_no_interfaces"
        / "test_va_code"
        / "hicuml2"
        / "hicumL2V2p4p0_release.va",
        load_model_from_path=test_path
        / "test_core_no_interfaces"
        / "test_modelcards"
        / "IHP_ECE704_03_para_D21.mat",
    )
    mc_D21.va_file = VA_FILES["L2V2.4.0_internal"]
    mc_D21.remove(["betcbar", "ibexs", "mbex", "rx", "version"])

    # turn off (on) self heating for the moment
    flsh = mc_D21["flsh"]
    flsh.value = 1
    mc_D21.set(flsh)
    re = mc_D21["re"]
    re.value = 7
    mc_D21.set(re)
    rth = mc_D21["rth"]
    rth.value = 3e3
    mc_D21.set(rth)
    alrth = mc_D21["alrth"]
    alrth.value = 1e-4
    mc_D21.set(alrth)
    # zetare seems to be the source of evil

    # create DUTs
    dut_ngspice = DutNgspice(None, DutType.npn, mc_D21, nodes="C,B,E,S,T", reference_node="E")
    dut_ads = DutAds(None, DutType.npn, mc_D21, nodes="C,B,E,S,T", reference_node="E")

    # VBE :
    vbe_value_def = [0.7, 1.1, 81]  # from 0 to 1 V in 5 steps
    vbc_value_defs = np.linspace(0.5, -0.5, 5)  # from -0.5 to 0.5 V in 5 steps
    vbc_value_defs = [-0.4, 0, 0.4]

    # dmt for multiple simulations
    dmt = SimCon(t_max=20, n_core=1)

    # sweeps
    outputdef = ["I_C", "I_B"]
    othervar = {"TEMP": 300, "w": 10, "l": 0.25}

    sweeps = []
    for vc_ in vbc_value_defs:
        # create a sweep
        sweepdef = [
            {
                "var_name": specifiers.FREQUENCY,
                "sweep_order": 3,
                "sweep_type": "CONST",
                "value_def": [1e9],
            },
            {
                "var_name": specifiers.VOLTAGE + "B",
                "sweep_order": 2,
                "sweep_type": "LIN",
                "value_def": vbe_value_def,
            },
            {
                "var_name": specifiers.VOLTAGE + "C",
                "sweep_order": 2,
                "sweep_type": "SYNC",
                "master": "V_B",
                "offset": vc_,
            },
            {
                "var_name": specifiers.VOLTAGE + "E",
                "sweep_order": 1,
                "sweep_type": "CON",
                "value_def": [0],
            },
        ]
        sweeps.append(Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar))

    time_ads = 0
    if sim_ads:
        for sweep in sweeps:
            dmt.append_simulation(dut_ads, sweep)

        start = time.time()
        dmt.run_and_read(force=force, remove_simulations=False)
        time_ads = time.time() - start

    time_ngspice = 0
    if sim_ngspice:
        for sweep in sweeps:
            dmt.append_simulation(dut_ngspice, sweep)

        start = time.time()
        dmt.run_and_read(force=force, remove_simulations=False)
        time_ngspice = time.time() - start

    return time_ads, time_ngspice, vbc_value_defs, dut_ads, dut_ngspice


if __name__ == "__main__":
    time_ads, time_ngspice, vbc_value_defs, dut_ads, dut_ngspice = compare_ngspice_many_sweeps()

    # now some plotting
    plt_gummel = Plot(
        "I_C(V_BE)",
        x_label=r"$V_{\mathrm{BE}}/\si{\volt}$",
        x_scale=1,
        y_label=r"$I_{\mathrm{C}}/\si{\milli\ampere}$",
        y_scale=1e3,
        y_log=True,
        legend_location="upper left",
        style="xtraction_color",
    )
    plt_rey21 = Plot(
        "ReY_21(V_BE)",
        x_label=r"$V_{\mathrm{BE}}/\si{\volt}$",
        x_scale=1,
        y_label=r"$\Re\left\{ Y_{\mathrm{21}} \right\}/\si{\milli\siemens}$",
        y_scale=1e3,
        y_log=True,
        legend_location="upper left",
        style="xtraction_color",
    )
    plt_imy21 = Plot(
        "ImY_21(V_BE)",
        x_label=r"$V_{\mathrm{BE}}/\si{\volt}$",
        x_scale=1,
        y_label=r"$\Im\left\{ Y_{\mathrm{21}} \right\}/\si{\milli\siemens}$",
        y_scale=1e3,
        y_log=True,
        legend_location="upper left",
        style="xtraction_color",
    )
    plt_y11 = Plot(
        "Y_11(V_BE)",
        x_label=r"$V_{\mathrm{BE}}/\si{\volt}$",
        x_scale=1,
        y_label=r"$\left| Y_{\mathrm{21}} \right|/\si{\milli\siemens}$",
        y_scale=1e3,
        y_log=True,
        legend_location="upper left",
        style="xtraction_color",
    )
    plt_ft = Plot(
        "f_T(I_C)",
        x_label=r"$I_{\mathrm{C}}/\si{\milli\ampere}$",
        x_scale=1e3,
        y_label=r"$f_{\mathrm{t}}/\si{\giga\hertz}$",
        y_scale=1e-9,
        y_log=False,
        x_log=True,
        legend_location="upper left",
        style="xtraction_color",
    )
    plts = [plt_gummel, plt_rey21, plt_imy21, plt_y11, plt_ft]

    if sim_ads and not sim_ngspice:
        for vbc, key_ads in zip(vbc_value_defs, dut_ads.data.keys()):
            data_ads = dut_ads.data[key_ads]
            data_ads = data_ads.calc_ft("B", "C")

            plt_gummel.add_data_set(
                np.asarray(data_ads["V_B"]),
                np.asarray(abs(data_ads["I_C"])),
                # label=r'$ads\,V_{{BC}} = \SI{' + str(vbc) + r'}{\volt}$',
            )
            plt_rey21.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.real(data_ads[data_ads["FREQ"] == 1e9]["Y_CB"]),
                # label=r'$ads V_{{BC}} = \SI{' + str(vbc) + r'}{\volt}$',
            )
            plt_imy21.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.imag(data_ads[data_ads["FREQ"] == 1e9]["Y_CB"]),
                # label=r'$ads V_{{BC}} = \SI{' + str(vbc) + r'}{\volt}$',
            )
            plt_y11.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["Y_BB"])),
                # label=r'$ads V_{{BC}} = \SI{' + str(vbc) + r'}{\volt}$',
            )
            plt_ft.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["I_C"])),
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9][specifiers.TRANSIT_FREQUENCY])),
                # label=r'$ads V_{{BC}} = \SI{' + str(vbc) + r'}{\volt}$',
            )

    elif sim_ngspice and not sim_ads:
        for vbc, key_ngspice in zip(vbc_value_defs, dut_ngspice.data.keys()):
            data_ngspice = dut_ngspice.data[key_ngspice]
            data_ngspice = data_ngspice.calc_ft("B", "C")
            # data_simu    = dut_simu.data[key_simu]
            plt_gummel.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["I_C"])),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_rey21.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.real(data_ngspice[data_ngspice["FREQ"] == 1e9]["Y_CB"]),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_imy21.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.imag(data_ngspice[data_ngspice["FREQ"] == 1e9]["Y_CB"]),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_y11.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["Y_BB"])),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_ft.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["I_C"])),
                np.asarray(
                    abs(data_ngspice[data_ngspice["FREQ"] == 1e9][specifiers.TRANSIT_FREQUENCY])
                ),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )

    elif sim_ngspice and sim_ads:
        for vbc, key_ngspice, key_ads in zip(
            vbc_value_defs, dut_ngspice.data.keys(), dut_ads.data.keys()
        ):
            data_ngspice = dut_ngspice.data[key_ngspice]
            data_ngspice = data_ngspice.calc_ft("B", "C")
            data_ads = dut_ads.data[key_ads]
            data_ads = data_ads.calc_ft("B", "C")
            # data_simu    = dut_simu.data[key_simu]
            plt_gummel.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["I_C"])),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_gummel.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["I_C"])),
            )
            plt_rey21.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.real(data_ngspice[data_ngspice["FREQ"] == 1e9]["Y_CB"]),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_rey21.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.real(data_ads[data_ads["FREQ"] == 1e9]["Y_CB"]),
            )
            plt_imy21.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.imag(data_ngspice[data_ngspice["FREQ"] == 1e9]["Y_CB"]),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_imy21.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.imag(data_ads[data_ads["FREQ"] == 1e9]["Y_CB"]),
            )
            plt_y11.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["Y_BB"])),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_y11.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["V_B"])),
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["Y_BB"])),
            )
            plt_ft.add_data_set(
                np.asarray(abs(data_ngspice[data_ngspice["FREQ"] == 1e9]["I_C"])),
                np.asarray(
                    abs(data_ngspice[data_ngspice["FREQ"] == 1e9][specifiers.TRANSIT_FREQUENCY])
                ),
                label=r"$V_{{BC}} = \SI{" + str(vbc) + r"}{\volt}$",
            )
            plt_ft.add_data_set(
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9]["I_C"])),
                np.asarray(abs(data_ads[data_ads["FREQ"] == 1e9][specifiers.TRANSIT_FREQUENCY])),
            )

    if sim_ngspice:
        print("time ngspice:" + str(time_ngspice))
    if sim_ads:
        print("time ads    :" + str(time_ads))

    if show:
        for plt in plts[:-1]:
            plt.plot_pyqtgraph(show=False)

        plts[-1].plot_pyqtgraph(show=True)

    else:
        for plt in plts:
            plt.legend_location = "upper right outer"
            plt.save_tikz(
                test_path / "tmp",
                "ngspice_plot_" + plt.name,
                standalone=True,
                build=True,
                mark_repeat=3,
                width="0.4\\textwidth",
                height="0.3\\textwidth",
                fontsize="LARGE",
            )
