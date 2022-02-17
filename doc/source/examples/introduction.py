""" Python script which is explained in detail in the introduction.
Here the commands are repeated to be able to test them.
"""
from pathlib import Path

path_file = Path(__file__).resolve()
from DMT import core

dut_meas = core.DutMeas(
    database_dir=None,  # Use dir from config
    dut_type=core.DutType.npn,  # it is a BJT-npn
    width=float(1e-6),
    length=float(2e-6),
    name="dut_meas_npn",  # name and width/length for documentation
    reference_node="E",  # defines configuration
)
dut_meas.add_data(path_file.parent.parent / "_static/meas_data_300K.csv", key="300K/iv")
dut_meas.clean_data(fallback={"E_": "E"})

print(dut_meas.data["300K/iv"].columns)
# V_c, V_E, V_B, I_E_, I_C, I_b, FREQ, Y_21, Y_11, Y22, Y_12

dummy = 1
