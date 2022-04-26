""" test ngspice vs ADS using a real modelcard in a systematic way.
"""
import numpy as np
import copy
import logging
from pathlib import Path
from DMT.core import SimCon, Plot, DutType, Sweep, specifiers, McParameter, sub_specifiers
from DMT.ngspice import DutNgspice
from DMT.ADS import DutAds
from DMT.hl2 import McHicum, Hl2Model, VA_FILES


folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_ADS_systematic.log",
    filemode="w",
)


def compare_ngspice_ads_real_mc(mc):

    rth_de = McParameter(name="rth_de", value=0)
    try:
        mc.add(rth_de)
    except:
        pass

    # mc = McHicum(
    #     load_model_from_path=os.path.join('test', 'test_interface_ngspice', 'dietmar_output.lib'),
    # )
    # mc.va_file = VA_FILES['L2V2.4.0_internal']
    # mc.set_values({
    #     'alrth':0,
    #     'flsh':0,
    # })

    dut_ads = DutAds(
        None, DutType.npn, mc, nodes="C,B,E,S,T", reference_node="E"
    )  # ADS with VA file

    # create a sweep with ONE operating point
    sweepdef = [
        {
            "var_name": specifiers.FREQUENCY,
            "sweep_order": 4,
            "sweep_type": "CON",
            "value_def": [1e9],
        },
        # {'var_name':specifiers.VOLTAGE + 'B',  'sweep_order':3, 'sweep_type':'CON' , 'value_def':[0.85]},
        # {'var_name':specifiers.VOLTAGE + 'B',  'sweep_order':3, 'sweep_type':'CON' , 'value_def':[-2.0]},
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0.3, 1, 91],
        },
        # {'var_name':specifiers.VOLTAGE + 'B',  'sweep_order':3, 'sweep_type':'CON' , 'value_def':[0.9]},
        {
            "var_name": specifiers.VOLTAGE + "C",
            "sweep_order": 2,
            "sweep_type": "CON",
            "value_def": [2],
        },
        {
            "var_name": specifiers.VOLTAGE + "E",
            "sweep_order": 1,
            "sweep_type": "CON",
            "value_def": [0],
        },
        # {'var_name':specifiers.VOLTAGE + 'B',  'sweep_order':3, 'sweep_type':'CON' , 'value_def':[0.9]},
        # {'var_name':specifiers.VOLTAGE + 'C',  'sweep_order':2, 'sweep_type':'CON' , 'value_def':[2.]},
        # {'var_name':specifiers.VOLTAGE + 'E',  'sweep_order':1, 'sweep_type':'CON' , 'value_def':[0]},
    ]
    outputdef = ["I_C", "I_B"]
    othervar = {specifiers.TEMPERATURE: 398}
    sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

    # first simulate ADS
    sim_con = SimCon(n_core=1, t_max=30)
    sim_con.append_simulation(dut=dut_ads, sweep=sweep)
    sim_con.run_and_read(force=True)

    # read initial conditions
    data_ads = dut_ads.get_data(sweep=sweep)
    ve = 0
    vb = data_ads["VBE"].to_numpy()[0]
    vc = data_ads["VCE"].to_numpy()[0]
    vbi = data_ads["VBiE"].to_numpy()[0]
    vbp = data_ads["VBpE"].to_numpy()[0]
    vci = data_ads["VCiE"].to_numpy()[0]
    vei = data_ads["VEiE"].to_numpy()[0]
    vt = data_ads["DTSH"].to_numpy()[0]
    delta = 1
    initial_conditions = {
        "icVE": ve * delta,
        "icVEi": vei * delta,
        "icVC": vc * delta,
        "icVCi": vci * delta,
        "icVB": vb * delta,
        "icVBi": vbi * delta,
        "icVBp": vbp * delta,
        "icVt": vt * delta,
    }

    # get rth stuff from ads
    rth_t = data_ads["rth_t"].to_numpy()
    pterm = data_ads["pterm"].to_numpy()
    dT = rth_t * pterm

    assert np.isclose(vt, dT[0], rtol=1e-3)

    # simulate ngspice using initial condition from ADS
    dut_ngspice = DutNgspice(
        None,
        DutType.npn,
        mc,
        nodes="C,B,E,S,T",
        reference_node="E",
        copy_va_files=False,  # ngspice without VA file! -> use internal
        simulator_command="ngspice",
        initial_conditions=initial_conditions,
        simulator_options={"GMIN": 1e-18, "ABSTOL": 1e-15},
    )
    sim_con.append_simulation(dut=dut_ngspice, sweep=sweep)
    sim_con.run_and_read(force=True)

    data_ngspice = dut_ngspice.get_data(sweep=sweep)

    # ngspice operating point
    vbiei = data_ngspice["VBIEI"].to_numpy()
    vbici = data_ngspice["VBICI"].to_numpy()
    vciei = data_ngspice["VCIEI"].to_numpy()
    temp = data_ngspice["TK"].to_numpy()
    # ngspice currents
    ibei_ngspice = data_ngspice["IBEI"].to_numpy()
    ibei_ads = data_ads["IBIEI"].to_numpy()
    it_ngspice = data_ngspice["IT"].to_numpy()
    it_ads = data_ads["IT_"].to_numpy()

    # ensure some stuff
    ensure = [
        specifiers.TRANSIT_FREQUENCY,
        specifiers.CAPACITANCE + "B" + "E",
        specifiers.CAPACITANCE + "B" + "C",
        specifiers.CAPACITANCE + "C" + "E",
        specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.IMAG,
        specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.REAL,
        specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
        specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.IMAG,
        specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.REAL,
        specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.IMAG,
        specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.REAL,
        specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.IMAG,
    ]
    for speci in ensure:
        data_ngspice.ensure_specifier_column(speci, ports=["B", "C"])
        data_ads.ensure_specifier_column(speci, ports=["B", "C"])

    for col in data_ngspice.columns:
        col_data = data_ngspice[col].to_numpy()
        if np.all(np.imag(col_data) == 0):
            data_ngspice[col] = data_ngspice[col].astype(float)

    return data_ngspice, data_ads


if __name__ == "__main__":
    show = True  # If True, plot in maptplotlib, else generate Tex

    # load a modelcard
    mc = McHicum(load_model_from_path=folder_path / "hicum_test_modelcard.lib")

    mc = mc.get_clean_modelcard()
    mc.set_values(
        {"flcomp": 2.4, "flnqs": 1, "flsh": 1, "alrth": 0, "cscp0": 2e-15, "cth": 1, "rbi0": 0},
        force=True,
    )
    mc.va_file = VA_FILES["L2V2.4.0_internal"]
    # end load modelcard

    # define plots
    plt_gummel = Plot(
        r"$I(V_{\mathrm{BE}})$",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CURRENT + "C",
        y_log=True,
        style="comparison_4",
    )
    plt_it = Plot(
        r"IT(VBE)",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CURRENT + "C",
        y_log=True,
        style="xtraction_color",
    )
    plt_temp = Plot(
        r"$dT(VBE)$",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.TEMPERATURE,
        style="xtraction_color",
    )
    plt_ft = Plot(
        r"FT(VBE)",
        x_specifier=specifiers.CURRENT + "C",
        y_specifier=specifiers.TRANSIT_FREQUENCY,
        x_log=True,
        y_scale=1e-9,
        style="xtraction_color",
    )
    plt_ft.x_limits = (1e-5, 1e-1)
    plt_ft.y_limits = (0, 700)
    plt_cbe = Plot(
        r"CBE(VBE)",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CAPACITANCE + "B" + "E",
        y_scale=1e15,
        style="xtraction_color",
    )
    plt_cbc = Plot(
        r"CBC(VBE)",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CAPACITANCE + "B" + "C",
        y_scale=1e15,
        style="xtraction_color",
    )
    plt_cce = Plot(
        r"CCE(VBE)",
        x_specifier=specifiers.VOLTAGE + "B" + "E",
        y_specifier=specifiers.CAPACITANCE + "C" + "E",
        y_scale=1e15,
        style="xtraction_color",
    )
    plt_vbici = Plot(
        r"VBICI(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.VOLTAGE + "Bi" + "Ci",
        style="xtraction_color",
    )
    plt_rbi = Plot(
        r"rbi(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_label=r"$r_{\mathrm{rbi}}$",
        style="xtraction_color",
    )
    plt_rey11 = Plot(
        r"ReY11(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.REAL,
        style="xtraction_color",
    )
    plt_imy11 = Plot(
        r"ImY11(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.IMAG,
        style="xtraction_color",
    )
    plt_rey21 = Plot(
        r"ReY21(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
        style="markers_lines",
        y_log=True,
    )
    plt_imy21 = Plot(
        r"ImY21(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.IMAG,
        y_log=True,
        style="xtraction_color",
    )
    plt_rey12 = Plot(
        r"ReY12(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.REAL,
        style="xtraction_color",
    )
    plt_imy12 = Plot(
        r"ImY12(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.IMAG,
        y_log=True,
        style="xtraction_color",
    )
    plt_rey22 = Plot(
        r"ReY22(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.REAL,
        style="xtraction_color",
        y_log=True,
    )
    plt_imy22 = Plot(
        r"ImY22(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.IMAG,
        y_log=True,
        style="xtraction_color",
    )
    plt_vbiei = Plot(
        r"VBIEI(VBE)",
        x_specifier=specifiers.VOLTAGE + "B",
        y_specifier=specifiers.VOLTAGE + "Bi" + "Ei",
        style="xtraction_color",
    )
    # end define plots

    # store all reactive elements value
    caps = [
        "cjcx0",
        "cjci0",
        "cjep0",
        "cjei0",
        "cbcpar",
        # 'cbepar',
        # 'cjs0',
        # 'fcrbi',
        # 'csu',
        # 'cscp0',
        "all",
    ]

    for cap in caps:
        mc_modified = copy.deepcopy(mc)
        try:
            cap_val = mc[cap].value
            for caps_ in caps[:-2]:
                mc_modified.set_values({caps_: 0})
            mc_modified.set_values({cap: cap_val})
            label = " only " + cap
        except:
            dummy = 1
            pass
        if cap == "all":
            label = "all on"

        data_ngspice, data_ads = compare_ngspice_ads_real_mc(mc_modified)

        # fill plots
        # gummel
        plt_gummel.add_data_set(data_ngspice["V_B"], data_ngspice["I_C"], label="ngspice " + label)
        plt_gummel.add_data_set(data_ads["V_B"], data_ads["I_C"], label="ADS " + label)
        plt_gummel.add_data_set(
            data_ngspice["V_B"],
            data_ngspice["I_B"],  # IB from ngspice short is wrong
            # data_ngspice['VBBP']/mc['rbx'].value,
            # label='ngspice ' + label
        )
        # plt_gummel.add_data_set(
        #     data_ngspice['V_B'],
        #     data_ngspice['IBEI'], #IB from ngspice short is wrong
        #     #data_ngspice['VBBP']/mc['rbx'].value,
        #     label='ngspice $IBEI$'
        # )
        plt_gummel.add_data_set(
            data_ads["V_B"],
            data_ads["I_B"],
            # label='ADS ' + label
        )
        # it
        plt_it.add_data_set(data_ngspice["V_B"], data_ngspice["IT"], label="ngspice " + label)
        plt_it.add_data_set(data_ads["V_B"], data_ads["IT_"], label="ADS " + label)
        # rbi
        plt_rbi.add_data_set(data_ngspice["V_B"], data_ngspice["RBI"], label="ngspice " + label)
        plt_rbi.add_data_set(data_ads["V_B"], data_ads["rbi"], label="ADS " + label)
        # temp
        plt_temp.add_data_set(data_ngspice["V_B"], data_ngspice["V_T"], label="ngspice " + label)
        plt_temp.add_data_set(data_ads["V_B"], data_ads["DTSH"], label="ADS " + label)
        # ft
        try:
            plt_ft.add_data_set(
                data_ngspice["I_C"],
                data_ngspice[specifiers.TRANSIT_FREQUENCY],
                label="ngspice " + label,
            )
            plt_ft.add_data_set(
                data_ads["I_C"], data_ads[specifiers.TRANSIT_FREQUENCY], label="ADS " + label
            )
        except KeyError:
            pass
        # cbe
        try:
            plt_cbe.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.CAPACITANCE + "B" + "E"],
                label="ngspice " + label,
            )
            plt_cbe.add_data_set(
                data_ads["V_B"], data_ads[specifiers.CAPACITANCE + "B" + "E"], label="ADS " + label
            )
        except KeyError:
            pass
        # cbc
        try:
            plt_cbc.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.CAPACITANCE + "B" + "C"],
                label="ngspice " + label,
            )
            plt_cbc.add_data_set(
                data_ads["V_B"], data_ads[specifiers.CAPACITANCE + "B" + "C"], label="ADS " + label
            )
        except KeyError:
            pass
        # cce
        try:
            plt_cce.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.CAPACITANCE + "C" + "E"],
                label="ngspice " + label,
            )
            plt_cce.add_data_set(
                data_ads["V_B"], data_ads[specifiers.CAPACITANCE + "C" + "E"], label="ADS " + label
            )
        except KeyError:
            pass
        # reY11
        try:
            plt_rey11.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.REAL],
                label="ngspice " + label,
            )
            plt_rey11.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.REAL],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # imY11
        try:
            plt_imy11.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.IMAG],
                label="ngspice " + label,
            )
            plt_imy11.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.IMAG],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # reY21
        try:
            plt_rey21.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL],
                label="ngspice " + label,
            )
            plt_rey21.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # imY21
        try:
            plt_imy21.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.IMAG],
                label="ngspice " + label,
            )
            plt_imy21.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.IMAG],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # reY12
        try:
            plt_rey12.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.REAL],
                label="ngspice " + label,
            )
            plt_rey12.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.REAL],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # imY12
        try:
            plt_imy12.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.IMAG],
                label="ngspice " + label,
            )
            plt_imy12.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.IMAG],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # reY22
        try:
            plt_rey22.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.REAL],
                label="ngspice " + label,
            )
            plt_rey22.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.REAL],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # imY22
        try:
            plt_imy22.add_data_set(
                data_ngspice["V_B"],
                data_ngspice[specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.IMAG],
                label="ngspice " + label,
            )
            plt_imy22.add_data_set(
                data_ads["V_B"],
                data_ads[specifiers.SS_PARA_Y + "C" + "C" + sub_specifiers.IMAG],
                label="ADS " + label,
            )
        except KeyError:
            pass
        # vbici
        plt_vbici.add_data_set(data_ngspice["V_B"], data_ngspice["VBICI"], label="ngspice " + label)
        plt_vbici.add_data_set(
            data_ads["V_B"], data_ads["_V_BiE"] - data_ads["_V_CiE"], label="ADS " + label
        )
        # vbiei
        plt_vbiei.add_data_set(data_ngspice["V_B"], data_ngspice["VBIEI"], label="ngspice " + label)
        plt_vbiei.add_data_set(
            data_ads["V_B"], data_ads["_V_BiE"] - data_ads["_V_EiE"], label="ADS " + label
        )

    plts = [
        plt_vbiei,
        plt_rbi,
        plt_vbici,
        plt_rey11,
        plt_imy11,
        plt_rey12,
        plt_imy12,
        plt_rey21,
        plt_imy21,
        plt_rey22,
        plt_imy22,
        plt_ft,
        plt_cbe,
        plt_cbc,
        plt_cce,
        plt_temp,
        plt_it,
        plt_gummel,
    ]
    if show:
        for plt in plts[:-2]:
            plt.plot_py(show=False)

        plts[-1].plot_py(show=True)

    else:
        ###PRINT TO DOCUMENT FROM HERE#####################
        from pylatex import (
            Section,
            Subsection,
            Tabular,
            Math,
            Plot,
            Figure,
            Matrix,
            Alignat,
            Package,
            Itemize,
            NoEscape,
            Document,
        )
        from pylatex.base_classes import Arguments
        from pylatexenc.latex2text import LatexNodes2Text

        # from DMT.gui.utils import SubFile, CommandRefRange, CommandRef, CommandInput, CommandLabel from DMT.gui.utils import SubFile, CommandRefRange, CommandRef, CommandInput, CommandLabel from pylatexenc.latex2text import LatexNodes2Text
        from DMT.external import SubFile, CommandRef, CommandInput, CommandLabel

        width = "4.5in"

        doc = Document()
        fig_dir = folder_path / "documentation", "figs"

        with doc.create(Section("Comparison ADS/NGspice")):
            doc.append(
                NoEscape(
                    r'In this document the ngspice HICUM/L2.4.3 model in ngspice is compared against ADS simulations. The modelcard is taken from a real process and is realistic. This document is auto-generated using Pylatex. The shown ft, CBE, CCE and CBC results show quantities that are calculated from simulated Y-parameters. In these simulations all reactive model elements but one are turned off (except those simulations labeled as "all"). E.g. "only cjei0" means that only the Cjei capacitance is active.'
                )
            )
            with doc.create(Subsection("Plots")):
                for plt in plts:
                    plt_name = plt.save_tikz(
                        fig_dir, width=width, mark_repeat=2, legend_location="upper right outer"
                    )
                    with doc.create(Figure(position="h!")) as _plot:
                        _plot.append(
                            CommandInput(arguments=Arguments('"' + str(fig_dir / plt_name) + '"'))
                        )
                        _plot.add_caption(NoEscape(plt.name))
                        _plot.append(
                            CommandLabel(
                                arguments=Arguments(LatexNodes2Text().latex_to_text(plt.name))
                            )
                        )

        doc.generate_tex(folder_path / "documentation" / "comparison_ngspice_ads")
