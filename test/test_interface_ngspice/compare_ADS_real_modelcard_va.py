""" test ngspice vs ADS using a real modelcard.
"""

import logging
from pathlib import Path
from DMT.config import COMMANDS

COMMANDS["OPENVAF"] = "openvaf"
from DMT.core import SimCon, Plot, DutType, Sweep, specifiers, McParameter
from DMT.core.sweep_def import SweepDefConst, SweepDefLinear, SweepDefLog
from DMT.ngspice import DutNgspice
from DMT.ADS import DutAds
from DMT.hl2 import McHicumL2, VA_FILES

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_ADS_real.log",
    filemode="w",
)

col_vb = specifiers.VOLTAGE + "B"
col_vc = specifiers.VOLTAGE + "C"
col_ve = specifiers.VOLTAGE + "E"
col_vbc = specifiers.VOLTAGE + ["B", "C"]
col_vbe = specifiers.VOLTAGE + ["B", "E"]
col_vce = specifiers.VOLTAGE + ["C", "E"]
col_ib = specifiers.CURRENT + "B"
col_ic = specifiers.CURRENT + "C"


def compare_ngspice_ads_real_mc():
    mc = McHicumL2(
        load_model_from_path=folder_path.parent
        / "test_core_no_interfaces"
        / "test_modelcards"
        / "IHP_ECE704_03_para_D21.mat",
        va_file=VA_FILES["L2V2.4.0_internal"],
    )

    ###### Disable branches
    ## General settings
    mc = mc.get_clean_modelcard()
    mc.set_values(
        {
            # "flcomp": 2.4,
            # "flnqs": 0,
            # "flsh": 1,
            # "alrth": 0,
            # 'rth'   : 3700,
            # 'kavl'  : 0,
            # 'qavl': 10,
            # 'ibcis':0,
            # 'ibcxs':0,
            # 'ibeis':1.3e-18,
            # 'ireis':0,
            # 'ibets':0,
            # 'ibeps':0,
            # 'ireps':0,
            # 'itss'  :0,
            # 'rbx'   :10,
            # 'tr'    :0,
            # 'tbhrec':0,
            # 'rcx'   :1,
        },
        force=True,
    )
    mc.va_file = VA_FILES["L2V2.4.0_internal"]

    rth_de = McParameter(name="rth_de", value=0)
    mc.add(rth_de)

    dut_ads = DutAds(
        None, DutType.npn, mc, nodes="C,B,E,S,T", reference_node="E"
    )  # ADS with VA file

    dut_ngspice = DutNgspice(
        None,
        DutType.npn,
        mc,
        simulator_command="ngspice_osdi",
        nodes="C,B,E,S,T",
        reference_node="E",
        get_circuit_arguments={"use_build_in": False},
    )

    # create a sweep
    sweepdef = [
        SweepDefLog(specifiers.FREQUENCY, start=1, stop=2, steps=11, sweep_order=4),
        SweepDefLinear(col_vb, start=0.5, stop=1, steps=11, sweep_order=3),
        SweepDefConst(col_vc, value_def=1, sweep_order=2),
        SweepDefConst(col_ve, value_def=0, sweep_order=1),
    ]
    outputdef = ["OpVar"]
    othervar = {"TEMP": 300}
    sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

    sim_con = SimCon(n_core=2, t_max=60)
    sim_con.append_simulation(dut=dut_ads, sweep=sweep)
    sim_con.append_simulation(dut=dut_ngspice, sweep=sweep)
    sim_con.run_and_read(force=False)

    data_ngspice = dut_ngspice.get_data(sweep=sweep)
    data_ads = dut_ads.get_data(sweep=sweep)
    return data_ngspice, data_ads


if __name__ == "__main__":
    data_ngspice, data_ads = compare_ngspice_ads_real_mc()

    # define plots
    plt_gummel = Plot(
        r"$I(V_{\mathrm{BE}})$",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CURRENT + "C",
        y_log=True,
        style="markers_lines",
        legend_location="upper left",
    )
    plt_ibei = Plot(
        r"$IBEI(V_{\mathrm{BE}})$",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CURRENT + "B",
        y_log=True,
        style="markers_lines",
    )
    plt_ibci = Plot(
        r"$IBCI(V_{\mathrm{BE}})$",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CURRENT + "B",
        y_log=True,
        style="markers_lines",
    )
    plt_it = Plot(
        r"IT(VBE)",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CURRENT + "C",
        y_log=True,
        style="markers_lines",
    )
    plt_temp = Plot(
        r"$dT(VBE)$",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.TEMPERATURE,
        style="markers_lines",
    )
    plt_ft = Plot(
        r"FT(VBE)",
        x_specifier=specifiers.CURRENT + "C",
        y_specifier=specifiers.TRANSIT_FREQUENCY,
        x_log=True,
        style="markers_lines",
    )
    plt_vbici = Plot(
        r"VBICI(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.VOLTAGE + "Bi" + "Ci",
        style="markers_lines",
    )
    plt_vbiei = Plot(
        r"VBIEI(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.VOLTAGE + "Bi" + "Ei",
        style="markers_lines",
    )
    # end define plots

    # fill plots
    # gummel
    plt_gummel.add_data_set(data_ngspice["V_B"], data_ngspice["I_C"], label="ngspice $I_C$")
    plt_gummel.add_data_set(data_ads["V_B"], data_ads["I_C"], label="ADS $I_C$")
    plt_gummel.add_data_set(
        data_ngspice["V_B"],
        data_ngspice["I_B"],  # IB from ngspice short is wrong
        # data_ngspice['VBBP']/mc['rbx'].value,
        label="ngspice $I_B$",
    )
    # plt_gummel.add_data_set(
    #     data_ngspice['V_B'],
    #     data_ngspice['IBEI'], #IB from ngspice short is wrong
    #     #data_ngspice['VBBP']/mc['rbx'].value,
    #     label='ngspice $IBEI$'
    # )
    plt_gummel.add_data_set(data_ads["V_B"], data_ads["I_B"], label="ADS $I_B$")

    # ibei
    plt_ibei.add_data_set(data_ngspice["V_B"], data_ngspice["IBIEI"], label="ngspice ibei")
    plt_ibei.add_data_set(data_ads["V_B"], data_ads["IBIEI"], label="ADS ibei")
    # ibci
    plt_ibci.add_data_set(data_ngspice["V_B"], data_ngspice["IBICI"], label="ngspice ibci")
    plt_ibci.add_data_set(data_ads["V_B"], data_ads["IBICI"], label="ADS ibci")
    # it
    plt_it.add_data_set(data_ngspice["V_B"], data_ngspice["IT"], label="ngspice it")
    plt_it.add_data_set(data_ads["V_B"], data_ads["IT_"], label="ADS it")
    # temp
    plt_temp.add_data_set(data_ngspice["V_B"], data_ngspice["DTSH"], label="ngspice vt")
    plt_temp.add_data_set(data_ads["V_B"], data_ads["DTSH"], label="ADS it")
    # ft
    plt_ft.add_data_set(data_ngspice["I_C"], data_ngspice["FT"], label="ngspice ")
    plt_ft.add_data_set(data_ads["I_C"], data_ads["FT"], label="ADS ")
    # # vbici
    # plt_vbici.add_data_set(
    #     data_ngspice["V_B"], data_ngspice["_V_BiE"] - data_ngspice["_V_CiE"], label="ngspice "
    # )
    # plt_vbici.add_data_set(data_ads["V_B"], data_ads["_V_BiE"] - data_ads["_V_CiE"], label="ADS ")
    # # vbiei
    # plt_vbiei.add_data_set(
    #     data_ngspice["V_B"], data_ngspice["_V_BiE"] - data_ngspice["_V_EiE"], label="ngspice "
    # )
    # plt_vbiei.add_data_set(data_ads["V_B"], data_ads["_V_BiE"] - data_ads["_V_EiE"], label="ADS ")

    plt_vbiei.plot_pyqtgraph(show=False)
    plt_vbici.plot_pyqtgraph(show=False)
    plt_ft.plot_pyqtgraph(show=False)
    plt_temp.plot_pyqtgraph(show=False)
    plt_it.plot_pyqtgraph(show=False)
    plt_ibci.plot_pyqtgraph(show=False)
    plt_ibei.plot_pyqtgraph(show=False)
    plt_gummel.plot_pyqtgraph(show=True)
