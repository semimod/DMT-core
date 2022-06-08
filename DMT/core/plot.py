""" Wrapper for nice plots with tikz, pyqtgraph and matplotlib.

Author:
    Mario Krattenmacher | Mario.Krattenmacher@semimod.de
    Markus Mueller | Markus.Mueller3@tu-dresden.de
"""
# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-core>
#
# This file is part of DMT_core.
#
# DMT_core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DMT_core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
import os
import sys
import re
from typing import Union
import numpy as np
from pathlib import Path
from cycler import cycler
from colormath.color_objects import sRGBColor
from DMT.core import natural_scales, sub_specifiers
from DMT.external import tex_to_text, build_tex, build_svg, clean_tex_files, build_png, slugify

if "PYQTGRAPH_QT_LIB" not in os.environ:  # user did not choose Backend. Try to force PySide2
    # OLD: add PYQTGRAPH_QT_LIB environment variable.
    # os.environ["PYQTGRAPH_QT_LIB"] = "PySide2"
    # https://pyqtgraph.readthedocs.io/en/latest/how_to_use.html#pyqt-and-pyside
    try:
        import PySide2
    except ImportError:
        pass

try:
    import pyqtgraph
    from pyqtgraph.Qt import QtCore
except ImportError:
    print(f"DMT->Plot: Failed to import plotting module pyqtgraph.")

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib._pylab_helpers
    import matplotlib.ticker as ticker

    # matplotlib.rcParams["text.usetex"] = True

    # rc params spec
    packages = [
        "\\usepackage{amsmath}\n",
        "\\usepackage{mathtools}\n",
        "\\usepackage{amssymb}\n",
        "\\usepackage{siunitx}\n",
        "\\sisetup{range-units=repeat, list-units=repeat, binary-units, exponent-product = \\cdot, print-unity-mantissa=false}\n",
        "\\DeclareSIUnit\\sq{\\ensuremath{\\Box}}\n",
        "\\DeclareSIUnit\\degC{\\degreeCelsius}\n",
        "\\DeclareUnicodeCharacter{221E}{$\infty$}\n",
        "\\DeclareUnicodeCharacter{03A9}{$\Omega$}\n",
    ]
    packages_to_add = []
    str_user_packages = "".join(matplotlib.rcParams["text.latex.preamble"])
    for package in packages:
        if package not in str_user_packages:
            packages_to_add.append(package)

    try:
        matplotlib.rcParams["text.latex.preamble"] += packages_to_add
    except TypeError:
        # must be str ?!?
        matplotlib.rcParams["text.latex.preamble"] += "".join(packages_to_add)

except ImportError:
    print("DMT->Plot: Failed to import plotting module matplotlib.")


## Styles that can be used in the "style" argument given to the __init__ of Plot.
PLOT_STYLES = []
BLACK_WHITE = "bw"
PLOT_STYLES.append(BLACK_WHITE)
BLACK_SOLID = "black_solid"
PLOT_STYLES.append(BLACK_SOLID)
BLACK_DASHED = "black_dashed"
PLOT_STYLES.append(BLACK_DASHED)
BLACK_LINESTYLE = "black_linestyle"
PLOT_STYLES.append(BLACK_LINESTYLE)
COLOR = "color"
PLOT_STYLES.append(COLOR)
MARKERS_COLOR = "markers_color"
PLOT_STYLES.append(MARKERS_COLOR)
MARKERS_LINES_COLOR = "markers_lines_color"
PLOT_STYLES.append(MARKERS_LINES_COLOR)
MARKERS = "markers"
PLOT_STYLES.append(MARKERS)
MARKERS_LINES = "markers_lines"
PLOT_STYLES.append(MARKERS_LINES)
XTRACTION = "xtraction"
PLOT_STYLES.append(XTRACTION)
COMPARISON_2_LINES = "comparison_2_lines"
PLOT_STYLES.append(COMPARISON_2_LINES)
XTRACTION_COLOR = "xtraction_color"
PLOT_STYLES.append(XTRACTION_COLOR)
XTRACTION_COLOR_4 = "xtraction_color_4"  # repeat color after 4 pairs of lines
PLOT_STYLES.append(XTRACTION_COLOR_4)
COMPARISON_3 = "comparison_3"
PLOT_STYLES.append(COMPARISON_3)
COMPARISON_3_MARKERS = "comparison_3_markers"  # different markers for every line
PLOT_STYLES.append(COMPARISON_3_MARKERS)
COMPARISON_4 = "comparison_4"
PLOT_STYLES.append(COMPARISON_4)
XTRACTION_INTERPOLATED = "xtraction_interpolated"
PLOT_STYLES.append(XTRACTION_INTERPOLATED)
XTRACTION_INTERPOLATED_COLOR = "xtraction_interpolated_color"
PLOT_STYLES.append(XTRACTION_INTERPOLATED_COLOR)
MIX = "mix"
PLOT_STYLES.append(MIX)

### Translation dictionaries from matplotlib to tikz
_DICT_MARKERS_MPL_TO_PGF = {
    ".": r"mark=*, mark options={solid, fill}, ",
    # ',',# do not know how to translate them ...
    "o": r"mark=o, mark options={solid, fill}, ",
    "ö": r"mark=*, mark options={solid, fill=black}, text mark as node=true, ",  # cheat: mark points in plots with this marker
    "v": r"mark=triangle, mark options={solid, rotate=180}, ",
    "^": r"mark=triangle, mark options={solid, rotate=0}, ",
    "<": r"mark=triangle, mark options={solid, rotate=270}, ",
    ">": r"mark=triangle, mark options={solid, rotate=90}, ",
    "1": r"mark=text, mark options={solid, rotate=0}, text mark={v}, ",  # there are no "tri_down" markers in pgf
    "2": r"mark=text, mark options={solid, rotate=180}, text mark={v}, ",  # needs verification...
    "3": r"mark=text, mark options={solid, rotate=270}, text mark={v}, ",
    "4": r"mark=text, mark options={solid, rotate=90}, text mark={v}, ",
    "s": r"mark=square, mark options={solid}, ",
    "p": r"mark=pentagon, mark options={solid}, ",
    "*": r"mark=asterisk, mark options={solid}, ",
    # 'h', # there are no hexagons in tikz
    # 'H',
    "+": r"mark=+, mark options={solid}, ",
    "x": r"mark=x, mark options={solid}, ",
    "D": r"mark=diamond, mark options={solid}, ",
    "d": r"mark=diamond, mark options={solid}, ",  # what is a thin diamond??
    "|": r"mark=|, mark options={solid}, ",
    "_": r"mark=-, mark options={solid}, ",
    None: r" ",
}
_DICT_LINES_MPL_TO_PGF = {
    " ": "only marks, ",
    "--": "dashed, ",
    "-.": "dashdotted, ",
    "-": "solid, ",
    ".": "dotted, ",
    ":": "dotted, ",  # or densely dotted ??
}
_DICT_COLORS_MPL = {
    "b": "blue",
    "g": "green",
    "r": "red",
    "c": "cyan",
    "m": "magenta",
    "y": "yellow",
    "k": "black",
    "w": "white",
}


class Plot(object):
    """Class that represents plots with different plotting backends. Many convenience functions for device modeling are supported.

    Attributes
    ----------
    legend_location : str
        Use valid location strings for matplotlib!
    """

    qt_application = None
    list_pg_windows = []

    def __init__(
        self,
        plot_name,
        style="mix",
        x_label=None,
        y_label=None,
        x_specifier=None,
        y_specifier=None,
        x_scale=None,
        y_scale=None,
        x_log=False,
        y_log=False,
        legend_location="upper right",
        num=None,
        divide_by_unit=False,
    ):
        """
        Parameters
        ----------
        plot_name : str
            Name of the plot object, also used for captions and saving the object.
        style : str, optional
            A string that equals one of the styles at the top of this script. These are convenience wrapper for automatic styling of lines, added to the plot.
        x_label : str, optional
            String that is used to label the x_axis.
        y_label : str, optional
            String that is used to label the y_axis.
        x_specifier : DMT.core.SpecifierStr, optional
            A specifier that defines the quantity along the x_axis. Together with the argument "x_scale" this keyword may be used instead of "x_label" to generate x-axis labels automatically.
        x_scale : float, optional
            The x-axis values displayed in the plot are the data stored in the plot times this value.
        y_specifier : DMT.core.SpecifierStr, optional
            A specifier that defines the quantity along the y_axis. Together with the argument "y_scale" this keyword may be used instead of "y_label" to generate x-axis labels automatically.
        y_scale : float, optional
            The y-axis values displayed in the plot are the data stored in the plot times this value.
        legend_location : str, optional
            A string that defines the postition of the legend. Allowed: "upper right", "upper left", "lower left", "lower right"
        num : str, optional
            This string is internally used to identify the plot by the different plotting engines. By the default, this string equals plot_name, however if more than two plots with the same name are initialized, num needs to be given different for every of them so that the plotting enginge can distinguish the plot objects.
        x_log : {True,False}, optional
            If true, use a logarithmic x-axis.
        y_log : {True,False}, optional
            If true, use a logarithmic y-axis.
        divide_by_unit : bool, optional
            Passed forward to specifier.to_label().

        Attributes
        ----------
        name : str
            The name of this plot, used to caption and store the plot. By default, also the identifier for the plot by the plotting engine.
        num  : str
            The plot is identified by this string by the plotting engine.
        x_label : str
            This string is displayed below the x-axis.
        y_label : str
            This string is displayed below the y-axis.
        _cycler : cycler.Cycler
            This object is iteratively called to produce the line styles for every line.
        data : [{'x':np.ndarray, 'y':np.ndarray, 'label':str, 'style':str, 'kwargs':{}}]
            See the Plot.add_data method for details.
        fig  : FigureHandle
            The handle of the figure in the plotting engine.
        axis : AxisHandle
            The axis handle of the figure in the plotting engine.
        mw_pg : pyqtgraph widget handle
        pw_pg : pyqtgraph window handle
        x_limits : (float,float)
            The x_axis is limited to display data between x_limis[0] and x_limits[1]. If either element is None, infinity is used.
        y_limits : (float,float)
            The y_axis is limited to display data between y_limis[0] and y_limits[1]. If either element is None, infinity is used.
        legend_location : str
            Specifies the location of the legend. See the "Parameters" section.
        legend_frame : QtObject
            Handle of the legend in a plotting engine.
        x_axis_scale : str
            String that specifies the scale of the x_axis. May differ for different plotting engines.
        y_axis_scale : str
            String that specifies the scale of the y_axis. May differ for different plotting engines.
        divide_by_unit : bool, optional
            Passed forward to specifier.to_label().

        """
        self.name = plot_name

        # unique identifier to access figure handle later
        if num is None:
            self.num = plot_name
        else:
            self.num = num

        self.divide_by_unit = divide_by_unit
        self.x_scale = 1
        self.y_scale = 1
        self.x_label = ""
        self.y_label = ""

        if x_label is None and x_specifier is None:
            # try to get x_label from provided plot_name
            # (.+)\((.+)\)
            self.x_label = "$" + re.search(r"(.+)\((.+)\)", self.name).group(2) + "$"  # type: ignore
        else:
            self.set_x_label(x_label=x_label, x_specifier=x_specifier, x_scale=x_scale)

        if y_label is None and y_specifier is None:
            # try to get y_label from provided plot_name
            # (.+)\((.+)\)
            self.y_label = "$" + re.search(r"(.+)\((.+)\)", self.name).group(1) + "$"  # type: ignore
        else:
            self.set_y_label(y_label=y_label, y_specifier=y_specifier, y_scale=y_scale)

        self._cycler = cycler("linestyle", "-")  # just set a cycler so pylance is ok...
        self.set_cycler(style)

        self.lines = []

        # only init the data list, it is filled later
        # use add_data_set to do so
        self.data = []
        self.fig = None
        self.ax = None

        # PyQtGraph window and widget:
        self.mw_pg = None
        self.pw_pg = None

        # already prepare them...
        self.x_limits: tuple[Union[None, float], Union[None, float]] = (None, None)
        self.y_limits: tuple[Union[None, float], Union[None, float]] = (None, None)
        self.legend_location = legend_location
        self.legend_frame = True

        if x_log:
            self.x_axis_scale = "log"
        else:
            self.x_axis_scale = "linear"

        if y_log:
            self.y_axis_scale = "log"
        else:
            self.y_axis_scale = "linear"

    def set_x_label(self, x_label=None, x_specifier=None, x_scale=None):
        """Set the x label. Either using directly a string or a specifier.

        Parameters
        ----------
        x_label : str
        x_specifier : SpecifierStr
        x_scale : float
            If given, self.x_scale is overwritten with this value.

        Raises
        ------
        IOError
            If neither x_label nor x_specifier were given.
        """
        try:
            if x_scale is None and x_specifier is not None:
                x_scale = natural_scales[x_specifier.specifier]
        except KeyError as err:
            raise IOError(
                "can not find natural scale for specifier of x-axis:" + str(x_specifier)
            ) from err
        if x_scale is not None:
            self.x_scale = x_scale

        if x_label is not None:
            self.x_label = x_label
        elif x_specifier is not None:
            if sub_specifiers.PHASE.sub_specifiers[0] in x_specifier:
                self.x_scale = 1

            self.x_label = x_specifier.to_label(
                scale=self.x_scale, divide_by_unit=self.divide_by_unit
            )
        else:
            raise IOError("Either label or specifier have to be set!")

    def set_y_label(self, y_label=None, y_specifier=None, y_scale=None):
        """Set the y label. Either using directly a string or a specifier.

        Parameters
        ----------
        y_label : str
        y_specifier : SpecifierStr
        y_scale : float
            If given, self.y_scale is overwritten with this value.

        Raises
        ------
        IOError
            If neither y_label nor y_specifier were given.
        """
        try:
            if y_scale is None and y_specifier is not None:
                y_scale = natural_scales[y_specifier.specifier]
        except KeyError as err:
            raise IOError(
                "can not find natural scale for specifier of x-axis:" + str(y_specifier)
            ) from err

        if y_scale is not None:
            self.y_scale = y_scale

        if y_label is not None:
            self.y_label = y_label
        elif y_specifier is not None:
            if sub_specifiers.PHASE.sub_specifiers[0] in y_specifier:
                self.y_scale = 1

            self.y_label = y_specifier.to_label(
                scale=self.y_scale, divide_by_unit=self.divide_by_unit
            )
        else:
            raise IOError("Either label or specifier have to be set!")

    def set_cycler(self, style):
        """Sets the line cycler. Possible styles are defined in the top of this file for convenience.

        Parameters
        ----------
        style : str
            Style for plotting of the lines. Possible are:
            'color', 'bw', 'markers_color', 'markers', 'markers_lines',
            'xtraction', 'xtraction_color', 'xtraction_interpolated', 'xtraction_interpolated_color',
        """
        markers = [char for char in "x+v^*<>.so"]
        linestyles = ["-", "--", "-.", ":"]
        dashed = ["--"]
        # MM: replaced grey1 (#7f7f7f) with black(#) and grey2 with dark blue #1012d5. Does this cause problems?
        # MK: introduced completely new palette from https://mokole.com/palette.html (settings: 10 colors, 1% min, 80% max, 15000 loops, score 65.49)
        colors = [
            # "#1f77b4",
            # "#ff7f0e",
            # "#2ca02c",
            # "#d62728",
            # "#9467bd",
            # "#e377c2",
            # "#8c564b",
            # "#0e1111",
            # "#1012d5",
            # "#17becf",
            "#006400",  # darkgreen
            "#00008b",  # darkblue
            "#b03060",  # maroon3
            "#ff0000",  # red
            "#9467bd",  # yellow -> replaced by violett/brown combo
            "#deb887",  # curlywood
            "#00ff00",  # lime
            "#00ffff",  # aqua
            "#ff00ff",  # fuchsia
            "#6495ed",  # cornflower
        ]

        if style == BLACK_WHITE:
            self._cycler = (
                cycler("color", ["black"]) * cycler("linestyle", "-") * cycler("marker", markers)
            )

        elif style == BLACK_SOLID:
            self._cycler = cycler("color", ["black"]) * cycler("linestyle", "-")

        elif style == BLACK_DASHED:
            self._cycler = cycler("color", ["black"]) * cycler("linestyle", dashed)

        elif style == BLACK_LINESTYLE:
            self._cycler = cycler("color", ["black"]) * cycler("linestyle", linestyles)

        elif style == COLOR:
            # colors from default matplotlibrc
            self._cycler = cycler("color", colors) * cycler("linestyle", "-")

        elif style == MARKERS_COLOR:
            # colors from default matplotlibrc
            self._cycler = cycler("color", colors) + cycler("marker", markers)

        elif style == MARKERS_LINES_COLOR:
            # colors from default matplotlibrc
            nmin = np.min([len(colors), len(markers), len(linestyles)])
            self._cycler = (
                cycler("color", colors[:nmin])
                + cycler("marker", markers[:nmin])
                + cycler("linestyle", linestyles[:nmin])
            )

        elif style == MARKERS:
            # matplotlib.rcParams['axes.prop_cycle'] = cycler('marker', [char for char in 'oxs+v^*<>.']) * cycler(color= ['k'])
            self._cycler = (
                cycler("color", ["black"]) * cycler("linestyle", " ") * cycler("marker", markers)
            )

        elif style == MARKERS_LINES:
            # matplotlib.rcParams['axes.prop_cycle'] = cycler('marker', [char for char in 'oxs+v^*<>.']) * cycler(color= ['k'])
            self._cycler = (
                cycler("color", ["black"])
                * cycler("linestyle", linestyles)
                * cycler("marker", markers)
            )

        elif style == XTRACTION:
            # matplotlib.rcParams['axes.prop_cycle'] = cycler('marker', [char for char in 'oxs+v^*<>.']) * cycler(color= ['k'])
            xtraction_markers = []
            for marker in markers:
                xtraction_markers.append(marker)
                xtraction_markers.append(None)

            xtraction_lstyle = []
            for marker in xtraction_markers:
                if marker is None:
                    xtraction_lstyle.append("-")
                else:
                    xtraction_lstyle.append("")

            self._cycler = cycler("color", ["black"]) * (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )

        elif style == XTRACTION_COLOR:
            xtraction_markers = []
            for marker in markers:
                xtraction_markers.append(marker)
                xtraction_markers.append(None)

            xtraction_lstyle = []
            for marker in xtraction_markers:
                if marker is None:
                    xtraction_lstyle.append("-")
                else:
                    xtraction_lstyle.append("")
            colors2 = []
            for color in colors:
                colors2.append(color)
                colors2.append(color)

            self._cycler = cycler("color", colors2) + (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )

        elif style == COMPARISON_2_LINES:
            xtraction_lstyle, xtraction_markers, colors2 = [], [], []
            for color in colors:
                xtraction_lstyle.append("-")
                xtraction_lstyle.append("--")
                xtraction_markers.append(None)
                xtraction_markers.append(None)
                colors2.append(color)
                colors2.append(color)

            self._cycler = cycler("color", colors2) + (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )

        elif style == XTRACTION_COLOR_4:
            xtraction_markers = []

            # sub-set of 4 markers and colors
            markers_4 = [markers[0], markers[1], markers[2], markers[3]] * 10
            colors_4 = [colors[0], colors[1], colors[2], colors[3]] * 10

            for marker in markers_4:
                xtraction_markers.append(marker)
                xtraction_markers.append(None)

            xtraction_lstyle = []
            for marker in xtraction_markers:
                if marker is None:
                    xtraction_lstyle.append("-")
                else:
                    xtraction_lstyle.append("")

            colors2 = []
            for color in colors_4:
                colors2.append(color)
                colors2.append(color)

            self._cycler = cycler("color", colors2) + (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )

        elif style == COMPARISON_3:
            # find the limiting style component in terms of numbers
            n_styles = np.argmin([len(markers), len(colors)])
            n_styles = [len(markers), len(colors)][n_styles]

            xtraction_markers = []
            for marker in markers[:n_styles]:
                xtraction_markers.append(marker)
                xtraction_markers.append(None)
                xtraction_markers.append(None)

            xtraction_lstyle = []
            for marker in markers[:n_styles]:
                xtraction_lstyle.append("")
                xtraction_lstyle.append("-")
                xtraction_lstyle.append("--")

            colors2 = []
            for color in colors[:n_styles]:
                colors2.append(color)
                colors2.append(color)
                colors2.append(color)

            self._cycler = cycler("color", colors2) + (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )
        elif style == COMPARISON_3_MARKERS:
            # find the limiting style component in terms of numbers
            n_styles = int(len(markers) / 3)

            colors2, xtraction_lstyle, xtraction_markers = [], [], []
            for i in range(n_styles):
                n = i * 3
                xtraction_markers.append(markers[n])
                xtraction_markers.append(markers[n + 1])
                xtraction_markers.append(markers[n + 2])
                xtraction_lstyle.append("--")
                xtraction_lstyle.append("--")
                xtraction_lstyle.append("--")
                colors2.append(colors[n])
                colors2.append(colors[n])
                colors2.append(colors[n])

            self._cycler = cycler("color", colors2) + (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )

        elif style == COMPARISON_4:
            # find the limiting style component in terms of numbers
            n_styles = np.argmin([int(len(markers) / 2), len(colors)])
            n_styles = [int(len(markers) / 2), len(colors)][n_styles]

            xtraction_markers = []
            for i, marker in enumerate(markers[:n_styles]):
                xtraction_markers.append(None)
                xtraction_markers.append(marker)
                xtraction_markers.append(None)
                xtraction_markers.append(markers[i + 1])

            xtraction_lstyle = []
            for marker in markers[:n_styles]:
                xtraction_lstyle.append("-")
                xtraction_lstyle.append("")
                xtraction_lstyle.append("--")
                xtraction_lstyle.append("-.")

            colors2 = []
            for color in colors[:n_styles]:
                colors2.append(color)
                colors2.append(color)
                colors2.append(color)
                colors2.append(color)

            self._cycler = cycler("color", colors2) + (
                cycler("marker", xtraction_markers) + cycler("linestyle", xtraction_lstyle)
            )

        elif style == XTRACTION_INTERPOLATED:
            markers3 = []
            for marker in markers:
                markers3.append(marker)
                markers3.append(None)
                markers3.append(None)

            linestyles3 = []
            for _color in colors:
                linestyles3.append("")
                linestyles3.append("--")
                linestyles3.append("-")

            self._cycler = cycler("color", ["black"]) * (
                cycler("marker", markers3) + cycler("linestyle", linestyles3)
            )

        elif style == XTRACTION_INTERPOLATED_COLOR:
            markers3 = []
            for marker in markers:
                markers3.append(marker)
                markers3.append(None)
                markers3.append(None)

            linestyles3 = []
            for _color in colors:
                linestyles3.append("")
                linestyles3.append("--")
                linestyles3.append("-")

            colors3 = []
            for color in colors:
                colors3.append(color)
                colors3.append(color)
                colors3.append(color)

            self._cycler = cycler("color", colors3) + (
                cycler("marker", markers3) + cycler("linestyle", linestyles3)
            )

        elif style == MIX:  # wild mix if colors and markers
            self._cycler = (cycler("color", colors) + cycler("marker", markers)) * cycler(
                "linestyle", ["-"]
            )

        else:
            raise OSError("The plot style " + style + " is unknown!")

    def add_data_set(self, x, y, label=None, style=None, **kwargs):
        """Add y(x) to the plot

        Each data set is a dict.

        Parameters
        ----------
        x : array-like
            X data of this line.
        y : array-like
            Y data of this line.
        label : str, optional
            Legend entry for this line. If not given, no entry is used for this line.
        style : string, optional
            Matplotlib style descriptor for this line.
        """
        self.data.append(
            {
                "x": np.asanyarray(x),
                "y": np.asanyarray(y),
                "label": label,
                "style": style,
                "kwargs": kwargs,
            }
        )

    def remove_legend(self):
        for line in self.data:
            line["label"] = None

    def add_data_set_multiple_y(self, x, *y, label=None):
        """Add y(x) to the plot

        Each data set is a tuple with five entries, no need to create a dictionary, keeps it simple

        Parameters
        ----------
        x : array-like
        *y : array-likes
            multiple y arrays to plot versus x
        label : str or list(str), optional
            Legend entry/ies
        """
        if label is None or not label:  # no or empty label
            label = []
            for _i in range(len(y)):
                label.append(None)
        elif isinstance(label, str):
            label = [label]

        if len(y) != len(label):
            raise IOError(
                "To set multiple y(x) at the same time, the number of labels must be equal to the number of y datas"
            )

        for y_a, label_a in zip(y, label):
            self.add_data_set(x, y_a, label=label_a)

    def plot_py(
        self,
        show=True,
        font_size=None,
        allow_grid=False,
        tight_layout=True,
        figure_size=None,
        sub_plot=(1, 1, 1),
        repeated_labels=False,
        use_tex=True,
    ):
        """Plots using matplotlib.pyplot, without IPython shell. If plot is displayed, the python session is halted.

        Parameters
        ----------
        show : {True, False}, optional
            Set to False if the plot should only be prepared, use show_py later to show it
        font_size : int, optional
            Font size in the figure.
        allow_grid : {True, False}, optional
            If True, a grid is activated.
        tight_layout : {True, False}, optional
            Applies the tight_layout method from matplotlib on the plot.
            See: https://matplotlib.org/tutorials/intermediate/tight_layout_guide.html
        figure_size : optional
            Directly passed to matplotlib.pyplot.figure figsize parameter.
        sub_plot : tuple, optional
            Position of the subplot inside a figure.
        repeated_labels : {True, False}, optional
            If True, repeated labels will be removed from the plot. E.g. when this plot holds 10 lines with the same label, only the first label is printed to the legend.

        Notes
        -----
        ..todo: Interactive Mode.
        """
        matplotlib.rcParams["text.usetex"] = use_tex

        # get the figure
        self.fig = plt.figure(num=self.num, figsize=figure_size)
        if self.fig.axes and sub_plot == (1, 1, 1):
            self.ax = self.fig.axes[0]
            print("Adding data to figure with num " + self.num + " and name " + self.name)
        elif self.fig.axes:
            self.ax = self.fig.add_subplot(*sub_plot)
            print("Adding subplot to figure with num " + self.num + " and name " + self.name)
        else:
            self.ax = self.fig.add_subplot(*sub_plot)
            print("Init figure with num " + self.num + " and name " + self.name)

        # setting the window title using the matplotlib figure manager
        # pylint: disable = protected-access
        fig_manager = matplotlib._pylab_helpers.Gcf.get_fig_manager(self.fig.number)
        fig_manager.set_window_title(self.name)  # type: ignore

        if font_size is not None:
            matplotlib.rcParams.update({"font.size": font_size})

        # set the line cycler
        if not self.ax.lines:  # but only if the lines are empty..
            self.ax.set_prop_cycle(self._cycler)

        used_labels = []  # for the repeated_labels kw argument of this routine
        # actual plotting of the data
        for _i, dict_line in enumerate(self.data):
            # x and y should be numpy vectors, stable conversion is given (more tests necessary)
            x = dict_line["x"]
            y = dict_line["y"]

            if self.x_axis_scale == "log":
                x = abs(x)
            if self.y_axis_scale == "log":
                y = abs(y)

            if use_tex:
                label = dict_line["label"]
            else:
                label = tex_to_text(dict_line["label"])

            if label in used_labels:
                label = None
            else:
                used_labels.append(label)

            if "style" in dict_line and dict_line["style"] is not None:
                try:
                    style = dict_line["style"].replace("ö", "o")  # ö not supported in matplotlib
                    if (
                        "o" in dict_line["style"]
                    ):  # o is an empty circle from now on! Use '.' for filled points
                        (line,) = self.ax.plot(
                            x * self.x_scale,
                            y * self.y_scale,
                            style,
                            fillstyle="none",
                            label=label,
                            **dict_line["kwargs"],
                        )
                    else:
                        (line,) = self.ax.plot(
                            x * self.x_scale,
                            y * self.y_scale,
                            style,
                            label=label,
                            **dict_line["kwargs"],
                        )
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.name
                        + " for line with label "
                        + str(label)
                    ) from err
            else:
                try:
                    (line,) = self.ax.plot(
                        x * self.x_scale, y * self.y_scale, label=label, **dict_line["kwargs"]
                    )
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.name
                        + " for line with label "
                        + str(label)
                    ) from err
            self.lines.append(line)

        # labels and legend
        if self.legend_location in ["upper right outer", "right mid"]:  # not supported here
            self.ax.legend(loc="upper right", frameon=self.legend_frame)
        else:
            self.ax.legend(loc=self.legend_location, frameon=self.legend_frame)

        if use_tex:
            self.ax.set_xlabel(self.x_label)
            self.ax.set_ylabel(self.y_label)
        else:
            self.ax.set_xlabel(tex_to_text(self.x_label))
            self.ax.set_ylabel(tex_to_text(self.y_label))

        # set scale and limits
        self.ax.set_xscale(self.x_axis_scale)
        self.ax.set_yscale(self.y_axis_scale)

        self.ax.set_xlim(self.x_limits)
        if not all(lim is None for lim in self.x_limits):
            self.ax.set_xlim(left=self.x_limits[0], right=self.x_limits[1])
        # else:
        #     self.ax.set_autoscalex_on(True)

        if not all(lim is None for lim in self.y_limits):
            self.ax.set_ylim(bottom=self.y_limits[0], top=self.y_limits[1])
        # else:
        #     self.ax.set_autoscaley_on(True)

        if allow_grid:
            # Don't allow the axis to be on top of your data
            self.ax.set_axisbelow(True)

            # Turn on the minor TICKS, which are required for the minor GRID
            self.ax.minorticks_on()

            # Customize the major grid
            self.ax.grid(which="major", linewidth=0.65, linestyle="-", color=".85")
            # Customize the minor grid
            self.ax.grid(which="minor", linewidth=0.65, linestyle="-", color=".85")

        if tight_layout:
            plt.tight_layout()
            self.fig.subplots_adjust(hspace=0.02, wspace=0.02)

        if show:
            plt.show()  # self.fig)
            # input("Press any key to continue!")

    def show_py(self):
        """Calls .show on the matplotlib figure"""
        plt.show()  # self.fig)

    def save_png(self, directory):
        """Saves the plot to a png"""
        if self.fig is not None:
            self.fig.savefig(os.path.join(directory, self.num + ".png"), format="png", dpi=600)

    def plot_pyqtgraph(
        self,
        only_widget=False,
        show=True,
        figure_size=(800, 800),
        plot_empty=True,
    ):
        """Plots the figure using PyQtGraph

        Parameters
        ----------
        only_widget : Bool, False
            If True, only a plot widget is returned that can be used in other Qt applications. If False, a full QApplication with layout is returned.
        show        : {True, False}, optional
            If True, the QtEventLoop is started at the end if the plotting.
        figure_size : tuple, optional
            Size of the main window
        plot_empty : {True, False}, optional
            If False and data is empty, it will not create a plot widget.
        """
        if not plot_empty and not self.data:
            return

        pyqtgraph.setConfigOption("background", "w")
        pyqtgraph.setConfigOption("foreground", "k")

        if Plot.qt_application is None and not only_widget:
            try:
                Plot.qt_application = pyqtgraph.Qt.QtGui.QApplication([])  # type: ignore
            except RuntimeError:
                Plot.qt_application = "Already started"

        self.pw_pg = pyqtgraph.PlotWidget(name=self.name)
        qt_layout = None

        if not only_widget:
            # make own window
            self.mw_pg = pyqtgraph.Qt.QtGui.QMainWindow()  # type: ignore
            self.mw_pg.setWindowTitle(self.num)
            self.mw_pg.resize(*figure_size)
            cw = pyqtgraph.Qt.QtGui.QWidget()  # type: ignore
            self.mw_pg.setCentralWidget(cw)
            qt_layout = pyqtgraph.Qt.QtGui.QVBoxLayout()  # type: ignore
            cw.setLayout(qt_layout)
            qt_layout.addWidget(self.pw_pg)

        x_label = self.x_label
        y_label = self.y_label
        x_label = tex_to_text(x_label)
        y_label = tex_to_text(y_label)

        # labels and legend
        self.pw_pg.setLabel("bottom", x_label)
        self.pw_pg.setLabel("left", y_label)
        legend = self.pw_pg.addLegend()  # loc=self.legend_location, frameon=self.legend_frame)
        legend_pos = {  # not sure if correct
            "upper right": {"itemPos": (1, 0), "parentPos": (1, 0), "offset": (-10, 10)},
            "upper left": {"itemPos": (0, 0), "parentPos": (0, 0), "offset": (10, 10)},
            "lower right": {"itemPos": (1, 1), "parentPos": (1, 1), "offset": (-10, -10)},
            "lower left": {"itemPos": (0, 1), "parentPos": (0, 1), "offset": (10, -10)},
            None: {"itemPos": (0, 0), "parentPos": (0, 0), "offset": (10, 10)},
        }
        legend.anchor(**legend_pos[self.legend_location])

        # actual plotting of the data
        for i_line, dict_line in enumerate(self.data):
            # x and y should be numpy vectors, stable conversion is given (more tests necessary)
            x = dict_line["x"]
            y = dict_line["y"]

            if self.x_axis_scale == "log":
                x = np.abs(x)
            else:
                x = np.real(x)

            if self.y_axis_scale == "log":
                y = np.abs(y)
            else:
                y = np.real(y)

            label = dict_line["label"]
            if label is not None:
                # workaround since siunitx is not supported yet in pandoc
                label = tex_to_text(label)
                # insert space after <p>, so that label is not ON the symbol
                label = label.replace("\n", "")

            if "style" in dict_line and dict_line["style"] is not None:
                dict_style = self._convert_mpl_to_pyqt(dict_line["style"])
            else:
                dict_style = self._get_pyqt_from_cycler(i_line)

            # https://groups.google.com/forum/#!topic/pyqtgraph/X7fL1KfXalY
            dict_style["symbolSize"] = 10

            try:
                self.pw_pg.plot(
                    x=x * self.x_scale,
                    y=y * self.y_scale,
                    name=label,
                    **dict_style,
                    **dict_line["kwargs"],
                )
            except ValueError as err:
                raise ValueError(
                    "Too many values to unpack in plot "
                    + self.name
                    + " for line with label "
                    + str(label)
                ) from err

        # set scale
        self.pw_pg.setLogMode((self.x_axis_scale == "log"), (self.y_axis_scale == "log"))

        # limits
        padding = None
        if self.x_limits[0] is None:
            if self.data:  # fails for empty plots
                x_min = np.nanmin(
                    [
                        np.nanmin(dict_line["x"])
                        for dict_line in self.data
                        if not len(dict_line["x"]) == 0
                    ]
                )
                x_min = 0.9 * x_min if x_min > 0 else 1.1 * x_min
                x_min_set = x_min * self.x_scale
            else:
                x_min = 0
                x_min_set = x_min
        else:
            x_min = self.x_limits[0]
            x_min_set = x_min
            padding = 0.0

        if self.x_limits[1] is None:
            if self.data:  # fails for empty plots
                x_max = np.nanmax(
                    [
                        np.nanmax(dict_line["x"])
                        for dict_line in self.data
                        if not len(dict_line["x"]) == 0
                    ]
                )
                x_max = 1.1 * x_max if x_max > 0 else 0.9 * x_max
                # x_max = np.ceil(1.1*x_max) if x_max > 0 else np.ceil(0.9*x_max)
                x_max_set = x_max * self.x_scale
            else:
                x_max = 1
                x_max_set = x_max
        else:
            x_max = self.x_limits[1]
            x_max_set = x_max
            padding = 0.0

        if self.x_axis_scale == "log":
            # also doing this in case of log for the data itself
            x_min_set = np.log10(np.abs(x_min_set + np.finfo(float).eps))
            x_max_set = np.log10(np.abs(x_max_set + np.finfo(float).eps))

        try:
            self.pw_pg.setXRange(np.real(x_min_set), np.real(x_max_set), padding=padding)  # type: ignore
        except Exception:
            print("Error setting the XRange of PyQtGraph plot with name " + self.name + ".")

        padding = None
        if self.y_limits[0] is None:
            if self.data:  # fails for empty plots
                try:
                    y_min = np.inf
                    for dict_line in self.data:
                        y_filter = np.logical_and(
                            dict_line["x"] > x_min,
                            dict_line["x"] < x_max,
                        )
                        y_min_local = np.min(dict_line["y"][y_filter])
                        y_min = np.min([y_min, y_min_local])
                    # y_min = (
                    #     np.min([np.min(dict_line["y"]) for dict_line in self.data])
                    # )
                    y_min = 0.9 * y_min * self.y_scale if y_min > 0 else 1.1 * y_min * self.y_scale
                except ValueError:
                    y_min = 0.0
                # y_min = np.floor(0.9*y_min) if y_min > 0 else np.floor(1.1*y_min)
            else:
                y_min = 0.0
        else:
            y_min = self.y_limits[0]
            padding = 0.0

        if self.y_limits[1] is None:
            if self.data:  # fails for empty plots
                try:
                    y_max = -np.inf
                    for dict_line in self.data:
                        y_filter = np.logical_and(
                            dict_line["x"] > x_min,
                            dict_line["x"] < x_max,
                        )
                        y_max_local = np.max(dict_line["y"][y_filter])
                        y_max = np.max([y_max, y_max_local])
                    # y_max = (
                    #     np.max([np.max(dict_line["y"]) for dict_line in self.data])
                    # )
                    y_max = 1.1 * y_max * self.y_scale if y_max > 0 else 0.9 * y_max * self.y_scale
                except ValueError:
                    y_max = 1.0
            else:
                y_max = 1.0
        else:
            y_max = self.y_limits[1]
            padding = 0.0

        if self.y_axis_scale == "log":
            # also doing this in case of log for the data itself
            y_min = np.log10(np.abs(y_min + np.finfo(float).eps))
            y_max = np.log10(np.abs(y_max + np.finfo(float).eps))
        try:
            self.pw_pg.setYRange(np.real(y_min), np.real(y_max), padding=padding)  # type: ignore
        except Exception:
            print("Error setting the YRange of PyQtGraph plot with name " + self.name + ".")

        # grid
        self.pw_pg.getPlotItem().showGrid(True, True)  # type: ignore

        if self.mw_pg is not None:
            self.mw_pg.show()

        ## Start Qt event loop unless running in interactive mode or using pyside.
        if show:
            if sys.flags.interactive != 1 or not hasattr(pyqtgraph.Qt.QtCore, "PYQT_VERSION"):
                pyqtgraph.QtGui.QApplication.exec_()  # type: ignore

        if only_widget:
            return self.pw_pg
        elif qt_layout is not None:
            return qt_layout

    def show_pyqtgraph(self):
        """Reshows the PyQtGraph main window and startes the Qt event loop"""
        if self.mw_pg is not None:
            self.mw_pg.show()
            pyqtgraph.QtGui.QApplication.exec_()  # type: ignore

    def _convert_mpl_to_pyqt(self, mpl_style):
        """Returns a corresponding PyQtGraph style for a given matplotlib style.

        This can be very complicated as PyQtGraph directly uses a QtPen/QtBrush...

        Parameters
        ----------
        mpl_style : str
            For example 'k-o' for a solid black line with circle symbols

        Returns
        -------
        dict_style : dict
            Dictionary with kwargs for pyqtgraph.plot() and similar routines
        """
        kwargs_pen = {}

        dict_style = {
            "pen": None,  # The pen to use when drawing plot lines, or None to disable lines.
            "symbol": None,  #  A string describing the shape of symbols to use for each point. Optionally, this may also be a sequence of strings with a different symbol for each point.
            "symbolPen": "k",  #  The pen (or sequence of pens) to use when drawing the symbol outline.
            "symbolBrush": None,  # The brush (or sequence of brushes) to use when filling the symbol.
            # 'fillLevel': None, # Fills the area under the plot curve to this Y-value.
            # 'brush': None, # The brush to use when filling under the curve.
        }

        if mpl_style:
            for mpl_color in _DICT_COLORS_MPL:
                if mpl_color in mpl_style:
                    kwargs_pen["color"] = mpl_color
                    kwargs_pen["width"] = 2
                    dict_style["symbolPen"] = mpl_color
                    # dict_style['symbolBrush'] = mpl_color
                    mpl_style = mpl_style.replace(mpl_color, "")
                    break

        if mpl_style:
            for mpl_line in sorted(
                _DICT_LINES_MPL_TO_PGF, key=len, reverse=True
            ):  # sort descending length, only for the keys
                if mpl_line in mpl_style:
                    mpl_style = mpl_style.replace(mpl_line, "")
                    kwargs_pen["style"] = {
                        "--": QtCore.Qt.DashLine,  # type: ignore
                        "-.": QtCore.Qt.DashDotLine,  # type: ignore
                        "-": QtCore.Qt.SolidLine,  # type: ignore
                        ":": QtCore.Qt.DotLine,  #  type: ignore
                        " ": QtCore.Qt.NoPen,  # type: ignore
                    }[mpl_line]
                    break

        if "color" not in kwargs_pen:
            kwargs_pen["color"] = "k"
            kwargs_pen["width"] = 2

        if kwargs_pen:
            dict_style["pen"] = pyqtgraph.mkPen(**kwargs_pen)
        else:
            dict_style["pen"] = pyqtgraph.mkPen(None)  # equal to only symbols ...

        if mpl_style:
            for mpl_marker in _DICT_MARKERS_MPL_TO_PGF:  # get only the keys...
                if mpl_marker is not None and mpl_marker in mpl_style:
                    dict_style["symbol"] = {
                        "x": "d",
                        "+": "+",
                        "v": "t",
                        "^": "t1",
                        "*": "star",
                        "<": "t2",
                        ">": "t3",
                        "t4": "t3",  # t4 not available in pyqtgraph, what to do?
                        ".": "p",
                        "s": "s",
                        "o": "o",
                    }[mpl_marker]
                    mpl_style = mpl_style.replace(mpl_marker, "")
                    break

        if mpl_style:
            raise IOError(
                "A part of the mpl style was not removed and therefore not used in the pgf style. Unused: "
                + mpl_style
            )

        return dict_style

    def _get_pyqt_from_cycler(self, i_line):
        """Returns a corresponding PyQtGraph style for the used style cycler.

        This can be very complicated as PyQtGraph directly uses a QtPen/QtBrush...

        Parameters
        ----------
        i_line : int
            Number of the line to draw.

        Returns
        -------
        dict_style : dict
            Dictionary with kwargs for pyqtgraph.plot() and similar routines
        """

        while i_line >= len(
            self._cycler
        ):  # make sure i_line is a valid index for a list generate from the cycler
            i_line -= len(self._cycler)

        kwargs_pen = {}

        dict_style = {
            "pen": None,  # The pen to use when drawing plot lines, or None to disable lines.
            "symbol": None,  #  A string describing the shape of symbols to use for each point. Optionally, this may also be a sequence of strings with a different symbol for each point.
            "symbolPen": "k",  #  The pen (or sequence of pens) to use when drawing the symbol outline.
            "symbolBrush": None,  # The brush (or sequence of brushes) to use when filling the symbol.
            # 'fillLevel': None, # Fills the area under the plot curve to this Y-value.
            # 'brush': None, # The brush to use when filling under the curve.
        }

        try:
            color = [ele["color"] for ele in self._cycler][i_line]
            if color == "black":
                color = "k"
            dict_style["symbolPen"] = color
        except KeyError:
            # no color ->
            color = None

        try:
            line_style = [ele["linestyle"] for ele in self._cycler][i_line]
        except KeyError:
            # no line style: should be no line...
            line_style = None

        if line_style is not None and line_style:
            kwargs_pen["style"] = {
                "--": QtCore.Qt.DashLine,  # type: ignore
                "-.": QtCore.Qt.DashDotLine,  # type: ignore
                "-": QtCore.Qt.SolidLine,  # type: ignore
                ":": QtCore.Qt.DotLine,  # type: ignore
                " ": QtCore.Qt.NoPen,  # type: ignore
            }[line_style]

            kwargs_pen["width"] = 2
            if color is None:
                kwargs_pen["color"] = "k"
            else:
                kwargs_pen["color"] = color

        if kwargs_pen:
            dict_style["pen"] = pyqtgraph.mkPen(**kwargs_pen)
        else:
            dict_style["pen"] = pyqtgraph.mkPen(None)  # equal to only symbols ...

        try:
            mpl_marker = [ele["marker"] for ele in self._cycler][i_line]
        except KeyError:
            mpl_marker = None

        dict_style["symbol"] = {
            "x": "d",
            "+": "+",
            "v": "t",
            "^": "t1",
            "*": "star",
            "<": "t3",
            ">": "h",  # not available in pyqtgraph
            ".": "p",
            "s": "s",
            "o": "o",
            None: None,
        }[mpl_marker]

        return dict_style

    def save_tikz(
        self,
        directory,
        file_name=None,
        width="\\textwidth",
        height=None,
        mark_repeat=1,
        restrict=True,
        standalone=False,
        build=False,
        clean=False,
        fontsize="normalsize",
        svg=False,
        png=False,
        extension=None,
        nth=1,
        mark_delta=1,
        skip_every=lambda x: x,
        n_ticks_x=None,
        n_ticks_y=None,
        legend_location=None,
        legend_to_name=None,
        **kwargs,
    ):
        """Save plot in directory and return name of the tikz file.

        The name of the tikz file will be the figure attribute self.num, if not given.

        Parameters
        ----------
        directory : str or os.Pathlike
            Directory the tikz file will be placed in
        file_name : str, optional
            Set a different file name to create. Default is self.name sluggified, by default None
        width : str, optional
            Width of the figure, by default '\\\\textwidth'
        height : str, optional
            Height of the figure, by default None
        mark_repeat : int, optional
            Repeat the marks every x times, by default 1
        restrict : bool, optional
            Turn on/off the restricted data feature from tikz, by default True
        nth : int, optional
            Plot only every nth line in the plot.
        mark_delta : int, optional
            Start marks at this number of point, see https://tex.stackexchange.com/questions/239700/how-to-plot-mark-on-every-nth-point.
        standalone : bool, optional
            Create standalone tikz figure, by default False
        build : bool, optional
            Build the latex file (only possible for standalone), by default False
        clean : bool, optional
            Remove all files except the rendered picture after build, by default False
        fontsize : str, optional
            Latex fontsize, by default 'normalsize'.
        svg : bool, optional
            Build the figure to svg (suited for FrameMaker), by default False
        png : bool, optional
            Build the figure to png.
        extension : str, optional
            Extension for the saved tikz file, if not given extension == "tex".
        skip_every : callable, optional
            Apply this callable to the lines in the plot and only plot what is returned, by default lambda x:x
        n_ticks_x : int, optional
            Number of ticks on x axis, by default None
        n_ticks_y : int, optional
            Number of ticks on y axis, by default None
        legend_location : str, optional
            Change legend location to something different, by default None
        legend_to_name: str, optional
            If this value is set to a name the legend is saved to a label with the provided name. It is not display inside the plot. Instead it can be printed anywhere in the document with '\\\\rec{<<name>>}'

        Returns
        -------
        str
            file name including path

        Raises
        ------
        IOError
            Raised if non-standalone figures are tried to build
        """
        if not isinstance(directory, Path):
            directory = Path(directory)
        os.makedirs(directory, exist_ok=True)

        legend_pos = {
            "lower left": "at={(0.02,0.02)}, anchor=south west,",
            "upper left": "at={(0.02,0.98)}, anchor=north west,",
            "lower right": "at={(0.98,0.02)}, anchor=south east,",
            "upper right": "at={(0.98,0.98)}, anchor=north east,",
            "upper right outer": "at={(1.02,1.00)}, anchor=north west,",
            "right mid": "at={(0.98,0.70)}, anchor=north east,",
            None: "at={(0.98,0.98)}, anchor=north east,",
        }
        if legend_location is None:
            legend_location = legend_pos[self.legend_location]
        else:
            legend_location = legend_pos[legend_location]
        if standalone:
            str_tikz_picture = (
                "\\begin{tikzpicture}[font=\\"
                + fontsize
                + "]\n"
                + "\\pgfplotsset{every axis/.append style={ultra thick},compat=1.5},\n"
            )
        else:  # if this figure is used in other tex documents, the axis are trimed so that figures with different y-labels and ticks get displayed nicely
            str_tikz_picture = (
                "\\begin{tikzpicture}[font=\\"
                + fontsize
                + ",trim axis left, trim axis right]\n"
                + "\\pgfplotsset{every axis/.append style={very thick},compat=1.5},\n"
            )
        str_height = "" if height is None else "height=" + height + ",\n"
        if width is None:
            str_width = ""
        elif width == "\\textwidth":
            str_width = "width=0.951*\\figurewidth,\n"
        else:
            str_width = "width=" + width + ",\n"
        str_x_log = "" if self.x_axis_scale == "linear" else "xmode=log,\n"
        str_y_log = "" if self.y_axis_scale == "linear" else "ymode=log,\n"

        if self.legend_frame:
            str_legend_frame = ""
        else:
            str_legend_frame = ", fill=none, draw=none"

        str_limits = ""
        str_x_ticks = ""
        str_y_ticks = ""

        comment_restrict = "" if restrict else "% "

        if self.ax is not None:
            self.ax.set_xlim(self.x_limits[0], self.x_limits[1])
            self.ax.set_ylim(self.y_limits[0], self.y_limits[1])

            x_axis = self.ax.get_xaxis()
            x_min, x_max = self.ax.get_xlim()
            str_limits += f"xmin={x_min:g},\n"
            str_limits += f"xmax={x_max:g},\n"

            if x_axis._scale.name == "linear":
                x_min_restrict = x_min / 5 if x_min > 0 else x_min * 5
                x_max_restrict = x_max / 5 if x_max < 0 else x_max * 5
                str_limits += comment_restrict + "restrict x to domain={0:g}:{1:g},\n".format(
                    x_min_restrict, x_max_restrict
                )
            else:
                str_limits += comment_restrict + "restrict x to domain={0:g}:{1:g},\n".format(
                    np.log10(x_min - 1), np.log10(x_max + 1)
                )
            str_limits += "log basis x=10,\n"

            y_axis = self.ax.get_yaxis()
            y_min, y_max = self.ax.get_ylim()
            str_limits += "ymin={0:g},\n".format(y_min)
            str_limits += "ymax={0:g},\n".format(y_max)
            if y_axis._scale.name == "linear":
                y_min_restrict = y_min / 5 if y_min > 0 else y_min * 5
                y_max_restrict = y_max / 5 if y_max < 0 else y_max * 5
                str_limits += comment_restrict + "restrict y to domain={0:g}:{1:g},\n".format(
                    y_min_restrict, y_max_restrict
                )
            else:
                str_limits += comment_restrict + "restrict y to domain={0:g}:{1:g},\n".format(
                    np.log10(y_min - 1), np.log10(y_max + 1)
                )
            str_limits += "log basis y=10,\n"

            # #adjust the size of figure, which also makes nice ticks
            # #assumes that 'in' are the last characters
            # self.fig.tight_layout()
            # self.fig.set_size_inches(float(width[:-2]),float(height[:-2]),forward=True)
            if n_ticks_y is not None:
                # self.ax.yaxis.set_major_locator(plt.MaxNLocator(n_ticks_y))
                ymin, ymax = self.ax.get_ylim()
                print(str(ymin))
                print(str(ymax))
                print(self.y_limits)
                self.ax.xaxis.set_major_locator(ticker.MaxNLocator(n_ticks_y))
            if n_ticks_x is not None:
                # self.ax.xaxis.set_major_locator(plt.MaxNLocator(n_ticks_x))
                xmin, xmax = self.ax.get_xlim()
                print(str(xmin))
                print(str(xmax))
                print(self.x_limits)
                self.ax.xaxis.set_major_locator(ticker.MaxNLocator(n_ticks_x))

            # also get ticks and the ticks labels!
            x_major_ticks = [
                tick for tick in x_axis.get_majorticklabels()
            ]  # if (tick._x>=x_min) and (tick._x<=x_max)] # pylint: disable=protected-access
            x_minor_ticks = [
                tick for tick in x_axis.get_minorticklabels()
            ]  # if (tick._x>=x_min) and (tick._x<=x_max)] # pylint: disable=protected-access
            str_x_ticks = (
                "xtick={" + ",".join(["{0:g}".format(tick._x) for tick in x_major_ticks]) + "},\n"
            )  # pylint: disable=protected-access
            str_x_ticks += (
                "xticklabels={" + ",".join([tick._text for tick in x_major_ticks]) + "},\n"
            )  # pylint: disable=no-member, protected-access
            str_x_ticks += (
                "minor xtick={"
                + ",".join(["{0:g}".format(tick._x) for tick in x_minor_ticks])
                + "},\n"
            )  # pylint: disable=no-member, protected-access

            y_major_ticks = [
                tick
                for tick in y_axis.get_majorticklabels()
                if (tick._y >= y_min) and (tick._y <= y_max)
            ]  # pylint: disable=protected-access
            y_minor_ticks = [
                tick
                for tick in y_axis.get_minorticklabels()
                if (tick._y >= y_min) and (tick._y <= y_max)
            ]  # pylint: disable=protected-access
            str_y_ticks = (
                "ytick={" + ",".join(["{0:g}".format(tick._y) for tick in y_major_ticks]) + "},\n"
            )  # pylint: disable=protected-access
            str_y_ticks += (
                "yticklabels={" + ",".join([tick._text for tick in y_major_ticks]) + "},\n"
            )  # pylint: disable=no-member, protected-access
            str_y_ticks += (
                "minor ytick={"
                + ",".join(["{0:g}".format(tick._y) for tick in y_minor_ticks])
                + "},\n"
            )  # pylint: disable=no-member, protected-access
        elif self.pw_pg is not None:
            # self.pw_pg.
            view_range = self.pw_pg.viewRange()
            if self.x_axis_scale == "linear":
                x_min, x_max = view_range[0]
            else:
                x_min = np.float_power(10, view_range[0][0])
                x_max = np.float_power(10, view_range[0][1])
            if self.y_axis_scale == "linear":
                y_min, y_max = view_range[1]
            else:
                y_min = np.float_power(10, view_range[1][0])
                y_max = np.float_power(10, view_range[1][1])

            str_limits += "xmin={0:g},\n".format(x_min)
            str_limits += "xmax={0:g},\n".format(x_max)
            x_min_restrict = view_range[0][0] / 5 if view_range[0][0] > 0 else view_range[0][0] * 5
            x_max_restrict = view_range[0][1] / 5 if view_range[0][1] < 0 else view_range[0][1] * 5
            str_limits += comment_restrict + "restrict x to domain={0:g}:{1:g},\n".format(
                x_min_restrict, x_max_restrict
            )
            str_limits += "log basis x=10,\n"
            str_limits += "ymin={0:g},\n".format(y_min)
            str_limits += "ymax={0:g},\n".format(y_max)
            y_min_restrict = view_range[1][0] / 5 if view_range[1][0] > 0 else view_range[1][0] * 5
            y_max_restrict = view_range[1][1] / 5 if view_range[1][1] < 0 else view_range[1][1] * 5
            str_limits += comment_restrict + "restrict y to domain={0:g}:{1:g},\n".format(
                y_min_restrict, y_max_restrict
            )
            str_limits += "log basis y=10,\n"

            # x_axis = self.pw_pg.getPlotItem().getAxis('bottom')
            # x_ticks = x_axis.tickValues(x_min, x_max, spacing) # TODO find good spacing!
            # y_axis = self.pw_pg.getPlotItem().getAxis('left')
        else:
            str_limits += (
                "% xmin=0,\n" if self.x_limits[0] is None else f"xmin={self.x_limits[0]:g},\n"
            )
            str_limits += (
                "% xmax=0,\n" if self.x_limits[1] is None else f"xmax={self.x_limits[1]:g},\n"
            )
            if self.x_limits[0] is None or self.x_limits[1] is None:
                str_limits += "% restrict x to domain=0:1,\n"
            else:
                if self.x_axis_scale == "linear":
                    x_min_restrict = (
                        self.x_limits[0] / 5 if self.x_limits[0] > 0 else self.x_limits[0] * 5
                    )
                    x_max_restrict = (
                        self.x_limits[1] / 5 if self.x_limits[1] < 0 else self.x_limits[1] * 5
                    )
                else:
                    x_min_restrict = (
                        np.log10(self.x_limits[0] / 5)
                        if self.x_limits[0] > 0
                        else np.log10(self.x_limits[0] * 5)
                    )
                    x_max_restrict = (
                        np.log10(self.x_limits[1] / 5)
                        if self.x_limits[1] < 0
                        else np.log10(self.x_limits[1] * 5)
                    )
                str_limits += comment_restrict + "restrict x to domain={0:g}:{1:g},\n".format(
                    x_min_restrict, x_max_restrict
                )

            str_limits += "log basis x=10,\n"
            str_limits += (
                "% ymin=0,\n" if self.y_limits[0] is None else f"ymin={self.y_limits[0]:g},\n"
            )
            str_limits += (
                "% ymax=0,\n" if self.y_limits[1] is None else f"ymax={self.y_limits[1]:g},\n"
            )
            if self.y_limits[0] is None or self.y_limits[1] is None:
                str_limits += "% restrict y to domain=0:1,\n"
            else:
                if self.y_axis_scale == "linear":
                    y_min_restrict = (
                        self.y_limits[0] / 5 if self.y_limits[0] > 0 else self.y_limits[0] * 5
                    )
                    y_max_restrict = (
                        self.y_limits[1] / 5 if self.y_limits[1] < 0 else self.y_limits[1] * 5
                    )
                else:
                    y_min_restrict = (
                        np.log10(self.y_limits[0] / 5)
                        if self.y_limits[0] > 0
                        else np.log10(self.y_limits[0] * 5)
                    )
                    y_max_restrict = (
                        np.log10(self.y_limits[1] / 5)
                        if self.y_limits[1] < 0
                        else np.log10(self.y_limits[1] * 5)
                    )
                str_limits += comment_restrict + "restrict y to domain={0:g}:{1:g},\n".format(
                    y_min_restrict, y_max_restrict
                )
            str_limits += "log basis y=10,\n"
            print("using pgf")

        if legend_to_name is None:
            legend_to_name = ""
        else:
            legend_to_name = "legend to name={},\n".format(legend_to_name)

        ### header
        str_axis = (
            "\n\\begin{axis}[scale only axis,ytick pos=left,\n"
            # + fontsize+",\n"
            + str_width
            + str_height
            + "xlabel={"
            + self.x_label
            + "},\n"
            + "ylabel={"
            + self.y_label
            + "},\n"
            + str_x_log
            + str_y_log
            + str_limits
            + str_x_ticks
            + str_y_ticks
            + "xmajorgrids,\n"
            + "enlargelimits=false,\n"
            + "scaled ticks=true,\n"
            + "ymajorgrids,\n"
            + "x tick style={color=black},\n"
            + "y tick style={color=black},\n"
            + "x grid style={white!69.01960784313725!black},\n"
            + "y grid style={white!69.01960784313725!black},\n"
            # + "y tick label style={/pgf/number format/fixed, /pgf/number format/fixed zerofill, /pgf/number format/precision=3 },\n"
            + "/tikz/mark repeat="
            + str(mark_repeat)
            + ",\n"
            + "legend style={"
            + legend_location
            + "legend cell align=left, align=left"
            + str_legend_frame
            + "},\n"
            + legend_to_name
            + "]\n"
        )

        ### Lines
        str_lines = ""
        colors = []
        # try:
        #     mark_delta = np.int(mark_repeat/len(self.data[::nth]))
        # except ZeroDivisionError:
        #     mark_delta = 1
        #     print("DMT->plot->{:s}: Plot has no data, generating axis anyways.".format(self.name))

        for nr_line, dict_line in enumerate(self.data[::nth]):
            if len(dict_line["x"]) == 0:
                continue
            str_addplot, colors = self._tikz_addplot(
                dict_line, nr_line, colors=colors, mark_delta=mark_delta
            )
            if str_addplot is not None:
                str_lines += str_addplot

        ### footer
        str_footer = "\\end{axis}\n\n\\end{tikzpicture}\n"

        # str_cal_points = ''
        # if calibration_points is not None:
        #     for cal_points in calibration_points:
        #         # \draw [loosely dashed] (301.7,0) -- (301.7,270);
        #         str_cal_points += '\draw [loosely dashed] (%.2f,%.2f) -- (%.2f,%.2f);\n' % (cal_points[0], cal_points[1], cal_points[2], cal_points[3])
        #         #str_cal_points += '\draw [loosely dashed] (axis cs:762.5,\pgfkeysvalueof{/pgfplots/ymin}) -- (axis cs:762.5,\pgfkeysvalueof{/pgfplots/ymax});'
        #         #str_cal_points += '\draw [loosely dashed] (axis cs:762.5,ymin) -- (axis cs:762.5,ymax);'

        ### merge:
        str_tikz_picture += (
            self._convert_colors_to_texdefines(
                colors
            )  # needs work! -> replaced matplotlib with colormath! Test this!
            + str_axis
            + str_lines
            + str_footer
        )

        if standalone:
            str_tikz_picture = (
                "\\documentclass[class=IEEEtran]{standalone}\n"
                + "\\usepackage{tikz,amsmath,siunitx}\n"
                + "\\sisetup{range-units=repeat, list-units=repeat, binary-units, exponent-product = \\cdot, print-unity-mantissa=false}\n"
                + "\\usetikzlibrary{arrows,snakes,backgrounds,patterns,matrix,shapes,fit,calc,shadows,plotmarks}\n"
                + "\\usepackage[graphics,tightpage,active]{preview}\n"
                + "\\usepackage{pgfplots}\n"
                + "\\pgfplotsset{compat=newest}\n"
                + "\\usetikzlibrary{shapes.geometric}\n"
                + "\\PreviewEnvironment{tikzpicture}\n"
                + "\\PreviewEnvironment{equation}\n"
                + "\\PreviewEnvironment{equation*}\n"
                + "\\newlength\\figurewidth\n"
                + "\\newlength\\figureheight\n"
                + "\\begin{document}\n"
                + "\\setlength\\figurewidth{60mm}\n"
                + "\\setlength\\figureheight{60mm}\n"
                + str_tikz_picture
                + "\\end{document}\n"
            )

        ext_file = ".tex"
        if extension is not None:
            ext_file = "." + extension

        if file_name is None:
            file_name = slugify(self.num) + ext_file
        elif not file_name.endswith(ext_file):
            file_name = file_name + ext_file

        path_file = directory / file_name
        path_file.write_text(str_tikz_picture)

        if build:
            if not standalone:
                raise IOError(
                    "To build a single TikZ picture, you should also activate standalone!"
                )

            if svg:
                build_svg(path_file, wait=clean)
                ending_to_keep = ".svg"
            elif png:
                build_tex(path_file, wait=clean, extension=ext_file)
                build_png(path_file, wait=clean)
                ending_to_keep = ".png"
            else:
                build_tex(path_file, wait=clean, extension=ext_file)
                ending_to_keep = ".pdf"

            if clean:
                clean_tex_files(
                    directory, file_name.replace(ext_file, ""), keep=(ending_to_keep, ".tex")
                )

        return file_name

    def _tikz_addplot(self, dict_line, nr_line, colors=None, mark_delta=None):
        """Transforms a line into a pgfplots addplot command.

        Parameters
        ----------
        dict_line : (x_data, y_data, label, style)
            See the description in Plot.add_data .
        nr_line : int
            Number of the line in self.data.
        """
        x_data = dict_line["x"]
        y_data = dict_line["y"]
        if self.x_axis_scale == "log":
            x_data = np.abs(x_data)
        if self.y_axis_scale == "log":
            y_data = np.abs(y_data)

        if len(x_data) == 0:
            return "\n", colors

        label = dict_line["label"]
        style = dict_line["style"]
        line_width = dict_line["kwargs"].get("line_width", None)
        mark_size = dict_line["kwargs"].get("markersize", None)
        if colors is None:
            colors = []

        if style is None:
            opts_style, colors = self._get_pgfplotset_for_line_nr(nr_line, colors)
        else:
            opts_style, colors = self._convert_mpl_to_pfg(style, colors)

        if "mark phase" not in opts_style:
            # Markus: what was this?
            # mark_phase = np.int(nr_line)*mark_delta if (mark_delta is not None) else np.int(1)
            opts_style += "mark phase={:d}, ".format(mark_delta)

        if line_width is not None:
            opts_style += "line width={0:f}pt, ".format(line_width)

        if mark_size is not None:
            opts_style += "mark size={0:f}pt, ".format(mark_size)

        if label is None:
            opts_style += "forget plot, "

        str_addplot = "\\addplot [" + opts_style + "]\n"
        # str_addplot += "  table[row sep=crcr, x expr=\\thisrowno{0}*10^0, y expr=\\thisrowno{1}*10^0]{\n"
        str_addplot += "  table[row sep=crcr, x expr=\\thisrowno{{0}}*{0:e}, y expr=\\thisrowno{{1}}*{1:e}]{{\n".format(
            self.x_scale, self.y_scale
        )

        if np.iscomplex(x_data).any() or np.iscomplex(y_data).any():
            raise IOError("DMT: tikz_addplot: can not plot complex numbers.")

        x_data = np.real(x_data)
        y_data = np.real(y_data)

        # for x, y  in zip(np.abs(x_data), np.abs(y_data)): # why abs??
        for x, y in zip(x_data, y_data):
            try:
                str_addplot += "{0:g} {1:g}\\\\\n".format(x, y)
            except TypeError:
                raise IOError(
                    "DMT->Plot: Unsupported line added to plot with name "
                    + self.name
                    + ". Check that the data are 1D arrays."
                )

        str_addplot += "};\n"

        if label is None:
            str_addplot += "% \\addlegendentry{}\n"
        else:
            str_addplot += "\\addlegendentry{" + label + "}\n"

        return str_addplot, colors

    def _convert_mpl_to_pfg(self, mpl_style, colors):
        """Converts a matplotlib style text to a valid pgfplots options string."""
        pgf_color = "color=black, "
        pgf_line = "only marks, "
        pgf_marker = ""  # is a default case needed ?

        if mpl_style:
            for mpl_color in _DICT_COLORS_MPL:
                if mpl_color in mpl_style:
                    pgf_color = "color=" + _DICT_COLORS_MPL[mpl_color] + ", "
                    mpl_style = mpl_style.replace(mpl_color, "")
                    break

        if mpl_style:
            for mpl_line in sorted(
                _DICT_LINES_MPL_TO_PGF.keys(), key=len, reverse=True
            ):  # sort descending length
                if mpl_line in mpl_style:
                    pgf_line = _DICT_LINES_MPL_TO_PGF[mpl_line]
                    mpl_style = mpl_style.replace(mpl_line, "")
                    break

        if mpl_style:
            for mpl_marker in _DICT_MARKERS_MPL_TO_PGF:
                if mpl_marker in mpl_style:
                    pgf_marker = _DICT_MARKERS_MPL_TO_PGF[mpl_marker] + "mark phase=0, "
                    mpl_style = mpl_style.replace(mpl_marker, "")
                    break

        if mpl_style:
            raise IOError(
                "A part of the mpl style was not removed and therefore not used in the pgf style. Unused: "
                + mpl_style
            )

        return pgf_color + pgf_line + pgf_marker, colors

    def _get_pgfplotset_for_line_nr(self, line_nr, colors):
        """Converts the style cycler self._cylcer into a valid  pgfplots options string."""
        # markers = [char for char in 'oxs+v^*<>.']
        # linestyles = ['-', '--', '-.', ':']
        # colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        while line_nr >= len(
            self._cycler
        ):  # make sure line_nr is a valid index for a list generate from the cycler
            line_nr -= len(self._cycler)

        pgf_color = ""
        try:
            color = [ele["color"] for ele in self._cycler][line_nr]
            for i_color, color_a in enumerate(colors):
                if color == color_a:
                    pgf_color = "color=color" + str(i_color) + ", "
                    break
            if not pgf_color:
                pgf_color = "color=color" + str(len(colors)) + ", "
                colors.append(color)
        except KeyError:
            pgf_color = "color=black, "
            # do not need to append black...

        pgf_line = []
        for ele in self._cycler:
            try:
                pgf_line.append(_DICT_LINES_MPL_TO_PGF[ele["linestyle"]])
            except KeyError:
                pgf_line.append("only marks, ")

        pgf_line = pgf_line[line_nr]

        try:
            pgf_marker = [_DICT_MARKERS_MPL_TO_PGF[ele["marker"]] for ele in self._cycler][line_nr]
        except KeyError:
            pgf_marker = ""

        return pgf_color + pgf_line + pgf_marker, colors

    def _convert_colors_to_texdefines(self, colors):
        """Converting the list of tuples into valid XColor LaTeX strings"""
        str_tex = ""

        for i_color, color_a in enumerate(colors):
            # blue #00008b conversion is buggy? -> replaced matplotlib with colormath! Test this!
            if (
                color_a == "black"
            ):  # black is the only color given as a name in the cyclers above...
                color = (0.0, 0.0, 0.0)
            else:
                color = sRGBColor.new_from_rgb_hex(color_a).get_value_tuple()

            str_tex += "\\definecolor{{color{0:d}}}{{rgb}}{{{1:.5f}, {2:.5f}, {3:.5f}}}\n".format(
                i_color, *color
            )

        return str_tex


def save_or_show(plts, show=True, location=None, **kwargs):
    """Convenience function for either showing or saving an array of DMT plots.

    Parameters
    ----------
    plts : [Plot]
        An array of plots
    show : Bool, True
        If true, the plots will be opened in the interactive Matplotlib editor, else they will be saved as specified by the other args.
    location : os.path
        Here the plots will be saved
    kwargs : {}
        Additional arguments that are passed to the save_tikz routine.
    """
    if show:
        for plt in plts[:-1]:
            plt.plot_py(show=False)

        plts[-1].plot_py(show=True)
    else:
        for plt in plts:
            plt.save_tikz(
                location,
                plt.name + "_standalone",
                clean=True,
                build=True,
                standalone=True,
                **kwargs,
            )
            plt.save_tikz(
                location,
                plt.name,
                standalone=False,
                build=False,
                extension=r"tikz",
                width=None,
                height=None,
                **kwargs,
            )
