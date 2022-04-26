"""testing the plotting data delivery. Plotting is not possible in the CI...
"""
import os
from pathlib import Path
from DMT.core import read_data, Plot, specifiers

folder_path = Path(__file__).resolve().parent


def read_mdm():
    df = read_data(folder_path / "test_data" / "short_freq.mdm")
    df = read_data(folder_path / "test_data" / "short_dc.mdm")


def test_label_generation():
    plt_test = Plot("y_1(x)")

    assert plt_test.x_label == "$x$"
    assert plt_test.y_label == "$y_1$"

    plt_test = Plot(
        "y_2(x)",
        x_label="x/m",
        y_label="y_2/A",
    )

    assert plt_test.x_label == "x/m"
    assert plt_test.y_label == "y_2/A"

    plt_test = Plot(
        "y_2(x)",
        x_specifier=specifiers.X,
        x_scale=1e9,
        y_specifier=specifiers.NET_DOPING,
        # y_scale=1e6, # use natural scale
        y_log=True,
    )

    assert plt_test.x_label == "$x_{\\mathrm{}}\\left(\\si{\\nano\\meter}\\right)$"
    assert plt_test.y_label == "$N_{\\mathrm{net}}\\left(\\si{\\per\\centi\\meter\\cubed}\\right)$"


# def test_plot_add_line():

if __name__ == "__main__":
    test_label_generation()
