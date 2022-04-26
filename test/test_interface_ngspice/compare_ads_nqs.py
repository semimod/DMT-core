""" test ngspice vs ADS using a real modelcard in a systematic way.
"""
import logging
from pathlib import Path
from DMT.core import SimCon, Plot, DutType, Sweep, specifiers, McParameter, sub_specifiers
from DMT.ngspice import DutNgspice
from DMT.ADS import DutAds
from DMT.hl2 import McHicum, VA_FILES

import numpy as np
import copy

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=folder_path.parent.parent / "logs" / "test_ADS_nqs.log",
    filemode="w",
)


def compare_ngspice_ads_real_mc(mc):
    rth_de = McParameter(name="rth_de", value=0)
    try:
        mc.add(rth_de)
    except:
        pass

    dut_ads = DutAds(
        None, DutType.npn, mc, nodes="C,B,E,S,T", reference_node="E"
    )  # ADS with VA file

    # create a sweep with ONE operating point
    sweepdef = [
        {
            "var_name": specifiers.FREQUENCY,
            "sweep_order": 4,
            "sweep_type": "LOG",
            "value_def": [9, 12, 101],
        },
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0.7, 1.1, 41],
        },
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
    ]
    outputdef = ["I_C", "I_B"]
    othervar = {specifiers.TEMPERATURE: 298}
    sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

    # first simulate ADS
    sim_con = SimCon(n_core=1, t_max=30)
    sim_con.append_simulation(dut=dut_ads, sweep=sweep)
    sim_con.run_and_read(force=False)

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

    # #ngspice operating point
    # vbiei  = data_ngspice['VBIEI'].to_numpy()
    # vbici  = data_ngspice['VBICI'].to_numpy()
    # vciei  = data_ngspice['VCIEI'].to_numpy()
    # temp   = data_ngspice['TK'].to_numpy()
    # #ngspice currents
    # ibei_ngspice = data_ngspice['IBEI'].to_numpy()
    # ibei_ads     = data_ads['IBIEI'].to_numpy()
    # it_ngspice   = data_ngspice['IT'].to_numpy()
    # it_ads       = data_ads['IT_'].to_numpy()

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
    show = False  # If True, plot in maptplotlib, else generate Tex

    # load a modelcard
    mc = McHicum(load_model_from_path=folder_path / "ngspice_example_modelcard.lib")

    mc = mc.get_clean_modelcard()
    mc.set_values(
        {
            # 'flnqs' : 0,
            # 'flsh'  : 1,
            "cbcpar": 0,
            "cjcx0": 0,
            # 'fqi'    : 0,
            # 'fcrbi'  : 0,
            # 'cjci0'  : 0,
            # 'ibcxs'  : 0,
            # 'csu'  : 0,
            #'rsu'  : 100,
            "iscs": 0,
            "itss": 0,
        },
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
        legend_location="upper right outer",
    )
    plt_ft = Plot(
        r"FT(VBE)",
        x_specifier=specifiers.CURRENT + "C",
        y_specifier=specifiers.TRANSIT_FREQUENCY,
        x_log=True,
        y_scale=1e-9,
        style="xtraction_color",
        legend_location="upper right outer",
    )
    plt_ft.x_limits = (1e-5, 1e0)
    plt_ft.y_limits = (0, 600)
    plt_rey21 = Plot(
        r"ReY21(f)",
        x_specifier=specifiers.FREQUENCY,
        y_specifier=specifiers.SS_PARA_Y + "2" + "1" + sub_specifiers.REAL,
        x_log=True,
        style="xtraction_color",
        x_scale=1e-9,
        legend_location="upper right outer",
    )
    plt_imy21 = Plot(
        r"ImY21(f)",
        x_specifier=specifiers.FREQUENCY,
        y_specifier=specifiers.SS_PARA_Y + "2" + "1" + sub_specifiers.IMAG,
        x_log=True,
        style="xtraction_color",
        x_scale=1e-9,
        legend_location="upper right outer",
    )
    plt_magy21 = Plot(
        r"MagY21(f)",
        x_specifier=specifiers.FREQUENCY,
        y_label="mag(Y21)",
        x_log=True,
        style="xtraction_color",
        x_scale=1e-9,
        legend_location="upper right outer",
    )
    plt_phasey21 = Plot(
        r"PhaseY21(f)",
        x_specifier=specifiers.FREQUENCY,
        y_label=r"Phase (degree)",
        x_log=True,
        style="xtraction_color",
        x_scale=1e-9,
        legend_location="upper right outer",
    )

    mc_no_nqs = copy.deepcopy(mc)
    mc_nqs = copy.deepcopy(mc)
    mc_nqs.set_values({"flnqs": 1, "alqf": 0, "alit": 0})
    mcs = []
    for val in np.linspace(0, 1, 6):
        mc = copy.deepcopy(mc_nqs)
        mc.set_values({"alqf": val})
        mc.set_values({"alit": 0})
        mcs.append(mc)

    for val in np.linspace(0, 1, 6):
        mc = copy.deepcopy(mc_nqs)
        mc.set_values({"alqf": 1})
        mc.set_values({"alit": val})
        mcs.append(mc)

    for mc in mcs:
        # if mc['flnqs'].value == 1:
        #     label_add = 'flnqs=1'
        # else:
        #     label_add = 'flnqs=0'

        label_add = "alqf={0:1.1f}, alit={1:1.1f}".format(mc["alqf"].value, mc["alit"].value)

        data_ngspice, data_ads = compare_ngspice_ads_real_mc(mc)

        # fill plots
        data_ngspice_10GHz = data_ngspice[np.isclose(data_ngspice[specifiers.FREQUENCY], 1e9)]
        data_ads_10GHz = data_ads[np.isclose(data_ads[specifiers.FREQUENCY], 1e9)]
        # gummel
        plt_gummel.add_data_set(
            data_ngspice_10GHz["V_B"], data_ngspice_10GHz["I_C"], label="NGS " + label_add
        )
        plt_gummel.add_data_set(
            data_ads_10GHz["V_B"], data_ads_10GHz["I_C"], label="ADS " + label_add
        )
        plt_gummel.add_data_set(
            data_ngspice_10GHz["V_B"], data_ngspice_10GHz["I_B"]  # IB from ngspice short is wrong
        )
        plt_gummel.add_data_set(data_ads_10GHz["V_B"], data_ads_10GHz["I_B"])

        plt_ft.add_data_set(
            data_ngspice_10GHz["I_C"],
            data_ngspice_10GHz[specifiers.TRANSIT_FREQUENCY],
            label="NGS " + label_add,
        )
        plt_ft.add_data_set(
            data_ads_10GHz["I_C"],
            data_ads_10GHz[specifiers.TRANSIT_FREQUENCY],
            label="ADS " + label_add,
        )

        # find peak ft
        ft = data_ads_10GHz[specifiers.TRANSIT_FREQUENCY].to_numpy()
        vbe = data_ads_10GHz[specifiers.VOLTAGE + "B"].to_numpy()
        index_peak_ft = np.argmax(ft) + 2
        vbe_at_peak = vbe[index_peak_ft]
        data_ads = data_ads[
            np.isclose(data_ads[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED], vbe_at_peak)
        ]
        data_ngs = data_ngspice[
            np.isclose(data_ngspice[specifiers.VOLTAGE + "B" + sub_specifiers.FORCED], vbe_at_peak)
        ]
        plt_rey21.add_data_set(
            data_ads[specifiers.FREQUENCY],
            -data_ads[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.REAL],
            label="ads " + label_add,
        )
        plt_rey21.add_data_set(
            data_ngs[specifiers.FREQUENCY],
            -data_ngs[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.REAL],
            label="ngs " + label_add,
        )
        plt_imy21.add_data_set(
            data_ads[specifiers.FREQUENCY],
            -data_ads[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.IMAG],
            label="ads " + label_add,
        )
        plt_imy21.add_data_set(
            data_ngs[specifiers.FREQUENCY],
            -data_ngs[specifiers.SS_PARA_Y + "B" + "C" + sub_specifiers.IMAG],
            label="ngs " + label_add,
        )
        plt_magy21.add_data_set(
            data_ads[specifiers.FREQUENCY],
            np.abs(data_ads[specifiers.SS_PARA_Y + "B" + "C"]),
            label="ads " + label_add,
        )
        plt_magy21.add_data_set(
            data_ngs[specifiers.FREQUENCY],
            np.abs(data_ngs[specifiers.SS_PARA_Y + "B" + "C"]),
            label="ngs " + label_add,
        )
        plt_phasey21.add_data_set(
            data_ads[specifiers.FREQUENCY],
            -np.angle(data_ads[specifiers.SS_PARA_Y + "B" + "C"], deg=True),
            label="ads " + label_add,
        )
        plt_phasey21.add_data_set(
            data_ngs[specifiers.FREQUENCY],
            -np.angle(data_ngs[specifiers.SS_PARA_Y + "B" + "C"], deg=True),
            label="ngs " + label_add,
        )

    plts = [
        plt_ft,
        plt_gummel,
        plt_rey21,
        plt_imy21,
        plt_magy21,
        plt_phasey21,
    ]
    if show:
        for plt in plts[:-1]:
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
        fig_dir = folder_path / "documentation" / "figs"

        with doc.create(Section("Comparison ADS/NGspice")):
            doc.append(
                NoEscape(
                    r"In this document the ngspice HICUM/L2.4.3 model in ngspice is compared against ADS simulations."
                )
            )
            doc.append(NoEscape(r"The modelcard is taken from the ngspice examples directory. "))
            doc.append(
                NoEscape(
                    r"This document is auto-generated using Pylatex. The shown ft are calculated from simulated Y-parameters. "
                )
            )
            # doc.append(NoEscape(r'\FloatBarrier'))
            with doc.create(Subsection("Example Modelcard Characteristics")):
                doc.append(
                    NoEscape(
                        r"First, the transfer characteristics and transit frequency as a function of Jc are shown: "
                    )
                )
                for plt in [plt_ft, plt_gummel]:
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
            doc.append(NoEscape(r"\newpage"))
            with doc.create(Subsection("Frequency Dependence Y21")):
                doc.append(
                    NoEscape(r"Next, the frequency dependence of Y21 at peak ft are shown: ")
                )
                for plt in [plt_rey21, plt_imy21, plt_phasey21, plt_magy21]:
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

        doc.generate_tex(folder_path / "documentation" / "comparison_ngspice_ads_nqs")
