"""
This example shows the basic data handling with python.
We will read data, clean it, calculate with the data and then plot.
"""
from pathlib import Path
from DMT.core import read_data, specifiers, Plot

# path to static folder:
path_static = Path(__file__).resolve().parent.parent / "_static"

# some specifiers, they allow consistent access to electrical data
# all interfaces of DMT adhere to these specifiers!
col_vbe = specifiers.VOLTAGE + ["B", "E"]
col_vbc = specifiers.VOLTAGE + ["B", "C"]
col_ic = specifiers.CURRENT + "C"
col_ib = specifiers.CURRENT + "B"

# read data using the given method
data = read_data(path_static / "HBT_vbc.elpa")

# "clean" the data so we have DMT-specifier in it.
# This ensure that the read-in data is consistent with the DMT specifiers.
# clean data additionally removes all voltages and only potentials remain
data = data.clean_data(["B", "C", "E"], reference_node="E")
# adjust unit from read in file (currents were in mA, DMT uses always basic units):
data[col_ic] = data[col_ic] * 1e-3
data[col_ib] = data[col_ib] * 1e-3
# The "ensure_specifier_column" method can be used to ensure that a given derived
# electrical quantity, such as a voltage, is inside the dataframe. If it is not there,
# an algorithm will try to generate the quantity.
data.ensure_specifier_column(col_vbe)
data.ensure_specifier_column(col_vbc)

# generate the plot object with proper axis and legend location
plot = Plot(
    "I_C(V_BE)",
    x_specifier=col_vbe,
    y_specifier=col_ic,
    y_scale=1e3,
    y_log=True,
    legend_location="lower right",
)
plot.legend_frame = False
plot.x_limits = (0.6, 1.1)

# fill the gummel plot with a line for each V_BC
for _index, vbc, data_vbc in data.iter_unique_col(col_vbc, decimals=3):
    plot.add_data_set(
        data_vbc[col_vbe],
        data_vbc[col_ic],
        label="${:s}= \\SI{{{:.1f}}}{{\\volt}}$".format(col_vbc.to_tex(), vbc),
    )

# show the plot (DMT has three plotting back-ends: matplotlib, pyqtgraph and tikz)
# plot.plot_pyqtgraph()
plot.plot_py()
# save the plot as tikz and build it
plot.save_tikz(
    path_static,
    standalone=True,
    build=True,
    clean=True,
    width="3in",
)
