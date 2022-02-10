# this script tests the usage of DMT Xsteps using a DUT Hdev
from DMT.Hdev import DutCOOS, sige_hbt, coos_iv_fallback, XFitCOOS
from DMT.core import (
    DutType,
    SimCon,
    specifiers,
    Sweep,
    DutLib,
    MCard,
    McParameter,
    Technology,
    specifiers,
    sub_specifiers,
    DataFrame,
)
from DMT.extraction import Xtraction
from DMT.gui import XtractionGUI

import os

# 1 : generate artifical data
# prepare simulation
def get_inp(model_paras):
    """This is the TCAD model. We recommend to create this and a modelcard for every process."""
    inp = sige_hbt("1.12")
    for mob_def in inp["MOB_DEF"]:
        if mob_def["valley"] == "X" and mob_def["mod_name"] == "Si":
            mob_def["mu_l"] = model_paras["mu_l"]
            mob_def["v_sat"] = model_paras["v_sat"]
            break

    inp["RANGE_GRID"]["n_pnts"] = 101
    inp["OUTPUT"]["inqu_lev"] = 0

    return inp


inp = get_inp({"mu_l": 0.143, "v_sat": 1e5})
dut_hdev = DutCOOS(None, DutType.npn, inp, reference_node="E")

sweepdef = [
    {
        "var_name": specifiers.VOLTAGE + "C",
        "sweep_order": 3,
        "sweep_type": "LIN",
        "value_def": [0, 1, 101],
    },
    {
        "var_name": specifiers.VOLTAGE + "B",
        "sweep_order": 2,
        "sweep_type": "LIN",
        "value_def": [0, 1, 101],
    },
    {
        "var_name": specifiers.VOLTAGE + "E",
        "sweep_order": 1,
        "sweep_type": "LIN",
        "value_def": [0, 0, 101],
    },
]
outputdef = []
othervar = {"TEMP": 300}
sweep = Sweep("gummel", sweepdef=sweepdef, outputdef=outputdef, othervar=othervar)

dmt = SimCon(t_max=300)
dmt.append_simulation(dut_hdev, sweep)
dmt.run_and_read(force=False)

# clean data
for key in dut_hdev.data.keys():
    if "iv" in key:
        fallback = coos_iv_fallback
        dut_hdev.data[key] = dut_hdev.data[key].clean_data(
            nodes=["B", "E", "C"], reference_node="E", ac_ports=["B", "C"], fallback=fallback
        )

        mres = {}
        mres["R_BM"] = 0
        mres["R_CM"] = 0
        mres["R_EM"] = 0

        dut_hdev.data[key] = dut_hdev.data[key].deembed_DC(DataFrame(), mres=mres)


# put data into a library
save_dir = os.path.join("DMT", "DMT", "Hdev", "test", "tmp")
lib = DutLib(save_dir=save_dir, force=True)
lib.add_duts([dut_hdev])
lib.dut_ref = lib[0]

# init an empty modelcard with one mobility parameter
mc = MCard(["B", "E", "C"], "", "", 1)
mu_l = McParameter("mu_l", value=0.143, minval=1e-5, maxval=2)
v_sat = McParameter("v_sat", value=1e5, minval=0.5e5, maxval=1e6)
mc.add(mu_l)
mc.add(v_sat)

### Extraction
extraction = Xtraction("coos_verify", mc, os.path.join("test", "tmp", "extractions", "Hdev"), lib)
extraction.set_technology(Technology)

step = XFitCOOS(
    name="Hdev mu_l",
    mcard=mc,
    lib=lib,
    op_definition={
        specifiers.TEMPERATURE: 300,
        specifiers.VOLTAGE + "B" + "E": (0.6, None),
        #'V_BC|FORCED':[0.0,0.1,0.2,0.3,0.4,0.5,-0.1,-0.2,-0.3,-0.4,-0.5]
        # specifiers.VOLTAGE+'B'+'C'+sub_specifiers.FORCED:[0.0],
    },
    quantity_fit=specifiers.CURRENT + "C",
    get_inp=get_inp,
    key="iv",
    to_optimize=["v_sat"],
    n_core=4,
    technology=Technology(name="test"),
    inner_sweep_voltage=specifiers.VOLTAGE + "B" + "E",
    outer_sweep_voltage=specifiers.VOLTAGE + "B" + "C",
)
extraction.add_xstep(step)

gui = XtractionGUI(extraction)  # We set the form to be our ExampleApp (design)
gui.start()
