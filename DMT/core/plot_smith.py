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

import numpy as np
from pathlib import Path
from DMT.core.plot import Plot
from DMT.external import slugify, tex_to_text

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib._pylab_helpers

    # rc params spec
    packages = [
        "\\usepackage{amsmath}\n",
        "\\usepackage{mathtools}\n",
        "\\usepackage{amssymb}\n",
        "\\usepackage{siunitx}\n",
        "\\DeclareSIUnit\\sq{\\ensuremath{\\Box}}\n",
        "\\DeclareSIUnit\\degC{\\degreeCelsius}\n",
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

smith_available = True
try:
    from smithplot.smithaxes import SmithAxes
    from smithplot import smithhelper
except ModuleNotFoundError:
    smith_available = False


class SmithPlot(Plot):
    """Child class of Plot used for plotting SmithCharts using pySmithPlot. Does not support many features available for "normal" plots.
    Only supports S parameters < 1. Very basic implementation, to be improved in the future if needed.
    """

    def __init__(self, *args, **kwargs):
        if not smith_available:
            raise IOError(
                "DMT.core.Plot -> Pysmithplot is not installed. Try: pip install git+https://github.com/miesli/pySmithPlot"
            )
        super().__init__(*args, **kwargs)
        self.outer_fig = None  # here the "outer" matplotlib figure reference is stored

    def plot_pyqtgraph(self, *args, **kwargs):
        raise NotImplementedError

    def show_pyqtgraph(self, *args, **kwargs):
        raise NotImplementedError

    def save_png(self, *args, **kwargs):
        raise NotImplementedError

    def save_tikz(self, *args, **kwargs):
        raise NotImplementedError

    def save_pdf(self, directory, width):
        # prepare folder
        if not isinstance(directory, Path):
            directory = Path(directory)
        os.makedirs(directory, exist_ok=True)

        # prepare folder
        file_name = slugify(self.num) + ".pdf"

        path_file = directory / file_name

        if self.outer_fig is not None:
            self.outer_fig.savefig(path_file)

        return file_name

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
        # default params
        SmithAxes.update_scParams(
            {
                "plot.marker.hack": False,
                "plot.marker.rotate": False,
                "grid.minor.enable": True,
                "grid.minor.fancy": False,
            }
        )

        # get the figure
        self.outer_fig = plt.figure(num=self.num, figsize=figure_size)
        self.outer_fig.set_tight_layout(True)
        # add smith chart
        self.fig = plt.subplot(
            1,
            1,
            1,
            projection="smith",
            grid_major_fancy_threshold=(10, 10),
            grid_minor_enable=True,
            grid_minor_fancy=True,
        )
        if self.fig.axes and sub_plot == (1, 1, 1):
            self.ax = self.fig.axes
            print("Adding data to figure with num " + self.num + " and name " + self.name)
        elif self.fig.axes:
            self.ax = self.fig.add_subplot(*sub_plot)
            print("Adding subplot to figure with num " + self.num + " and name " + self.name)
        else:
            self.ax = self.fig.add_subplot(*sub_plot)
            print("Init figure with num " + self.num + " and name " + self.name)

        # setting the window title using the matplotlib figure manager
        # pylint: disable = protected-access
        fig_manager = matplotlib._pylab_helpers.Gcf.get_fig_manager(self.outer_fig.number)
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
            if not isinstance(x, np.ndarray):
                try:
                    x = [float(x_a) for x_a in x]
                except TypeError:
                    pass
                x = np.asanyarray(x)
            if not isinstance(y, np.ndarray):
                try:
                    y = [float(y_a) for y_a in y]
                except TypeError:
                    pass
                y = np.asanyarray(y)

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
                            # plt.plot(
                            smithhelper.moebius_inv_z(y, norm=50),
                            style,
                            fillstyle="none",
                            label=label,
                            datatype="Z",
                            interpolate=False,
                            **dict_line["kwargs"],
                        )
                    else:
                        (line,) = self.ax.plot(
                            # plt.plot(
                            smithhelper.moebius_inv_z(y, norm=50),
                            style,
                            label=label,
                            datatype="Z",
                            interpolate=False,
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
                        # plt.plot(
                        smithhelper.moebius_inv_z(y, norm=50),
                        label=label,
                        datatype="Z",
                        interpolate=False,
                        **dict_line["kwargs"],
                    )
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.name
                        + " for line with label "
                        + str(label)
                    ) from err
            # self.lines.append(line)

        # labels and legend
        if self.legend_location in ["upper right outer", "right mid"]:  # not supported here
            self.ax.legend(loc="upper right", frameon=self.legend_frame)
        else:
            self.ax.legend(loc=self.legend_location, frameon=self.legend_frame)

        # self.ax.set_xlabel(self.x_label)
        # self.ax.set_ylabel(self.y_label)

        # set scale and limits
        # self.ax.set_xscale(self.x_axis_scale)
        # self.ax.set_yscale(self.y_axis_scale)

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

        if show:
            plt.show()  # self.fig)
            # input("Press any key to continue!")
