from pathlib import Path
from DMT.hl2 import McHicum, VA_FILES
from DMT.ADS import DutAds
from DMT.ngspice import DutNgspice
from DMT.core import Sweep, specifiers, SimCon, DutType, sub_specifiers, Plot

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

if __name__ == "__main__":
    mc = McHicum(load_model_from_path=folder_path / "dietmar_full_sh.lib")
    mc.va_file = VA_FILES["L2V2.4.0_internal"]
    mc.set_values(
        {
            "flsh": 1,
            # 'alqav':0,
            # 'alkav':0,
            # # 'rth':1,
            # 'alrth':0,
            # 'alfav':0,
        }
    )
    dut_ads = DutAds(
        None, DutType.npn, mc, nodes="C,B,E,S,T", reference_node="E"
    )  # ADS with VA file
    dut_ngs = DutNgspice(
        None,
        DutType.npn,
        mc,
        nodes="C,B,E,S,T",
        reference_node="E",
        copy_va_files=False,  # ngspice without VA file! -> use internal
        simulator_command="ngspice",
        simulator_options={"GMIN": 1e-18, "ABSTOL": 1e-15},
    )

    # create a sweep with ONE operating point
    sweepdef = [
        {
            "var_name": specifiers.VOLTAGE + "B",
            "sweep_order": 2,
            "sweep_type": "CON",
            "value_def": [0.9],
        },
        {
            "var_name": specifiers.VOLTAGE + "C",
            "sweep_order": 3,
            "sweep_type": "LIN",
            "value_def": [0, 3, 601],
        },
        {
            "var_name": specifiers.VOLTAGE + "E",
            "sweep_order": 1,
            "sweep_type": "CON",
            "value_def": [0],
        },
    ]
    outputdef = ["I_C", "I_B"]
    othervar = {"TEMP": 300}
    sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

    sim_con = SimCon(n_core=1, t_max=30)
    sim_con.append_simulation(dut=dut_ads, sweep=sweep)
    sim_con.append_simulation(dut=dut_ngs, sweep=sweep)
    sim_con.run_and_read(force=True)

    plt_out = Plot(
        r"$I_C(V_{\mathrm{CE}})$",
        x_specifier=specifiers.VOLTAGE + "C" + "E",
        y_specifier=specifiers.CURRENT + "C",
        y_log=False,
        style="mix",
        legend_location="upper right outer",
    )
    plt_p = Plot(
        r"$P(V_{\mathrm{CE}})$",
        x_specifier=specifiers.VOLTAGE + "C" + "E",
        y_specifier=specifiers.POWER,
        y_log=False,
        style="mix",
        legend_location="upper right outer",
    )
    plt_dT = Plot(
        r"$dT(V_{\mathrm{CE}})$",
        x_specifier=specifiers.VOLTAGE + "C" + "E",
        y_specifier=specifiers.TEMPERATURE,
        y_log=False,
        style="mix",
        legend_location="upper right outer",
    )

    for key_ads, key_ngs in zip(dut_ads.data.keys(), dut_ngs.data.keys()):
        df_ads = dut_ads.data[key_ads]
        df_ads.ensure_specifier_column(specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED)
        df_ngs = dut_ngs.data[key_ngs]
        df_ngs.ensure_specifier_column(specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED)

        ic = df_ads[specifiers.CURRENT + "C"]
        ib = df_ads[specifiers.CURRENT + "B"]
        vce = df_ads[specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED]
        p = df_ads["Psh"]
        t = df_ads["DTSH"]
        plt_out.add_data_set(vce, ic, label="ads ic")
        plt_out.add_data_set(vce, ib, label="ads ib")
        plt_p.add_data_set(vce, p, label="ads p")
        plt_dT.add_data_set(vce, t, label="ads dt")

        ic = df_ngs[specifiers.CURRENT + "C"]
        ib = df_ngs[specifiers.CURRENT + "B"]
        vce = df_ngs[specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED]
        p = df_ngs[specifiers.POWER]
        # p   = df_ngs['Psh']
        t = df_ngs["DTSH"]
        plt_out.add_data_set(vce, ic, label="ngs ic")
        plt_out.add_data_set(vce, ib, label="ngs ib")
        plt_p.add_data_set(vce, p, label="ngs p")
        plt_dT.add_data_set(vce, t, label="ngs dt")

    plt_dT.plot_py(show=False)
    plt_p.plot_py(show=False)
    plt_out.plot_py(show=True)
