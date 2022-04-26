from pathlib import Path
from DMT.hl2 import McHicum, VA_FILES
from DMT.ADS import DutAds
from DMT.ngspice import DutNgspice
from DMT.core import Sweep, specifiers, SimCon, DutType, sub_specifiers, Plot

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent

if __name__ == "__main__":
    mc = McHicum(load_model_from_path=folder_path / "model-card-examples.lib")
    mc.va_file = VA_FILES["L2V2.4.0_internal"]
    mc.set_values(
        {
            # 'flsh' :1,
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

    plt_gum = Plot(
        r"$I_C(V_{\mathrm{BE}})$",
        x_specifier=specifiers.VOLTAGE + "C" + "E",
        y_specifier=specifiers.CURRENT,
        y_log=True,
        style="mix",
        legend_location="upper right outer",
    )

    temps = [300, 350, 400, 450]
    for temp in temps:
        # create a sweep with ONE operating point
        sweepdef = [
            {
                "var_name": specifiers.VOLTAGE + "B",
                "sweep_order": 3,
                "sweep_type": "LIN",
                "value_def": [0.2, 1.2, 101],
            },
            {
                "var_name": specifiers.VOLTAGE + "C",
                "sweep_order": 2,
                "sweep_type": "CON",
                "value_def": [1],
            },
            {
                "var_name": specifiers.VOLTAGE + "E",
                "sweep_order": 1,
                "sweep_type": "CON",
                "value_def": [0],
            },
        ]
        outputdef = ["I_C", "I_B"]
        othervar = {"TEMP": temp}
        sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

        sim_con = SimCon(n_core=1, t_max=30)
        sim_con.append_simulation(dut=dut_ads, sweep=sweep)
        sim_con.append_simulation(dut=dut_ngs, sweep=sweep)
        sim_con.run_and_read(force=False)

        for key_ads, key_ngs in zip(dut_ads.data.keys(), dut_ngs.data.keys()):
            temp_df = dut_ads.get_key_temperature(key_ads)
            if not temp_df == temp:
                continue

            df_ads = dut_ads.data[key_ads]
            df_ads.ensure_specifier_column(specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED)
            df_ngs = dut_ngs.data[key_ngs]
            df_ngs.ensure_specifier_column(specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED)

            ic = df_ads[specifiers.CURRENT + "C"]
            ib = df_ads[specifiers.CURRENT + "B"]
            vbe = df_ads[specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED]
            plt_gum.add_data_set(vbe, ic, label="ads ic T={:f}".format(temp))
            plt_gum.add_data_set(vbe, ib, label="ads ib T={:f}".format(temp))

            ic = df_ngs[specifiers.CURRENT + "C"]
            ib = df_ngs[specifiers.CURRENT + "B"]
            vbe = df_ngs[specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED]
            # p   = df_ngs['Psh']
            t = df_ngs["DTSH"]
            plt_gum.add_data_set(vbe, ic, label="ngs ic T={:f}".format(temp))
            plt_gum.add_data_set(vbe, ib, label="ngs ib T={:f}".format(temp))

    plt_gum.plot_py(show=True)
