"""testing the plotting data delivery. Plotting is not possible in the CI...
"""

from pathlib import Path
from DMT.core import read_data, Plot, specifiers
from DMT.core.plot import COLORS

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

def test_convert_colors_to_texdefines():
    # any plot object..
    plt_test = Plot(
        "y_2(x)",
        x_specifier=specifiers.X,
        x_scale=1e9,
        y_specifier=specifiers.NET_DOPING,
        # y_scale=1e6, # use natural scale
        y_log=True,
    )

    test_colors = plt_test._convert_colors_to_texdefines(COLORS)

    assert test_colors == "\\definecolor{color0}{rgb}{0.00000, 0.39216, 0.00000}\n\\definecolor{color1}{rgb}{0.00000, 0.00000, 0.54510}\n\\definecolor{color2}{rgb}{0.69020, 0.18824, 0.37647}\n\\definecolor{color3}{rgb}{1.00000, 0.00000, 0.00000}\n\\definecolor{color4}{rgb}{0.58039, 0.40392, 0.74118}\n\\definecolor{color5}{rgb}{0.87059, 0.72157, 0.52941}\n\\definecolor{color6}{rgb}{0.00000, 1.00000, 0.00000}\n\\definecolor{color7}{rgb}{0.00000, 1.00000, 1.00000}\n\\definecolor{color8}{rgb}{1.00000, 0.00000, 1.00000}\n\\definecolor{color9}{rgb}{0.39216, 0.58431, 0.92941}\n"

# def test_plot_add_line():

if __name__ == "__main__":
    test_label_generation()
    test_convert_colors_to_texdefines()
