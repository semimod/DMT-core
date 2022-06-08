""" Wrapper for plots with 2 y axis. Shows only "left plot" in pyqtgraph and merged in tikz

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
from DMT.external import build_tex, build_svg, clean_tex_files, build_png, slugify, tex_to_text

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
        "\\sisetup{range-units=repeat, list-units=repeat, binary-units, exponent-product = \\cdot, print-unity-mantissa=false}\n",
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


class Plot2YAxis(object):
    """Provides a plot with 2 y-Axes

    WARNING: Legend does not work with cyclers :(. You have to set the styles manually.

    """

    def __init__(self, name, plot_left, plot_right, legend_location="upper right"):
        self.name = name

        # do not check anything here!

        self.plot_left = plot_left
        self.plot_right = plot_right

        self.legend_location = legend_location
        self.legend_frame = True

        self.fig = None
        self.ax_left = None
        self.ax_right = None

        self.lines_left = []
        self.lines_right = []

    def plot_py(
        self,
        show=True,
        font_size=None,
        allowGrid=False,
        tight_layout=True,
        figure_size=None,
        use_tex=True,
    ):
        """Plots the 2 axis plot with the same arguments as the usual plot class"""
        matplotlib.rcParams["text.usetex"] = use_tex

        # get a new figure
        self.fig = plt.figure(num=self.name, figsize=figure_size)
        print("init 2 axis figure with name " + self.name + r"\n")
        # setting the window title using the matplotlib figure manager
        # pylint: disable = protected-access
        fig_manager = matplotlib._pylab_helpers.Gcf.get_fig_manager(self.fig.number)
        fig_manager.set_window_title(self.name)  # type: ignore

        if font_size is not None:
            matplotlib.rcParams.update({"font.size": font_size})

        ####################################### left axis
        self.ax_left = self.fig.add_subplot(111)
        # set the line cycler
        self.ax_left.set_prop_cycle(
            self.plot_left._cycler
        )  # does not work properly in combination with legends

        # plotting of the data left
        for _i, dict_line in enumerate(self.plot_left.data):
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

            if self.plot_left.x_axis_scale == "log":
                x = np.abs(x)
            if self.plot_left.y_axis_scale == "log":
                y = np.abs(y)

            if use_tex:
                label = dict_line["label"]
            else:
                label = tex_to_text(dict_line["label"])

            if "style" in dict_line and dict_line["style"] is not None:
                try:
                    if (
                        "o" in dict_line["style"]
                    ):  # o is an empty circle from now on! Use '.' for filled points
                        (line,) = self.ax_left.plot(
                            x * self.plot_left.x_scale,
                            y * self.plot_left.y_scale,
                            dict_line["style"],
                            fillstyle="none",
                            label=label,
                            **dict_line["kwargs"],
                        )
                    else:
                        (line,) = self.ax_left.plot(
                            x * self.plot_left.x_scale,
                            y * self.plot_left.y_scale,
                            dict_line["style"],
                            label=label,
                            **dict_line["kwargs"],
                        )
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.plot_left.name
                        + " for line with label "
                        + str(label)
                    ) from err
            else:
                try:
                    (line,) = self.ax_left.plot(
                        x * self.plot_left.x_scale,
                        y * self.plot_left.y_scale,
                        label=label,
                        **dict_line["kwargs"],
                    )
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.plot_left.name
                        + " for line with label "
                        + str(label)
                    ) from err
            self.lines_left.append(line)

        # labels
        if use_tex:
            self.ax_left.set_xlabel(self.plot_left.x_label)
            self.ax_left.set_ylabel(self.plot_left.y_label)
        else:
            self.ax_left.set_xlabel(tex_to_text(self.plot_left.x_label))
            self.ax_left.set_ylabel(tex_to_text(self.plot_left.y_label))

        # set scale and limits
        self.ax_left.set_xscale(self.plot_left.x_axis_scale)
        self.ax_left.set_yscale(self.plot_left.y_axis_scale)

        self.ax_left.set_xlim(self.plot_left.x_limits)
        if not all(lim is None for lim in self.plot_left.x_limits):
            self.ax_left.set_xlim(left=self.plot_left.x_limits[0], right=self.plot_left.x_limits[1])

        if not all(lim is None for lim in self.plot_left.y_limits):
            self.ax_left.set_ylim(bottom=self.plot_left.y_limits[0], top=self.plot_left.y_limits[1])

        ####################################### right axis
        self.ax_right = self.ax_left.twinx()
        # set the line cycler
        self.ax_right.set_prop_cycle(
            self.plot_right._cycler
        )  # does not work properly in combination with legends

        # plotting of the data right
        for _i, dict_line in enumerate(self.plot_right.data):
            # x and y should be numpy vectors, stable conversion is given (more tests necessary)
            x = dict_line["x"]
            y = dict_line["y"]

            if self.plot_right.x_axis_scale == "log":
                x = np.abs(x)
            if self.plot_right.y_axis_scale == "log":
                y = np.abs(y)

            if use_tex:
                label = dict_line["label"]
            else:
                label = tex_to_text(dict_line["label"])
            x_left = self.ax_left.get_xlim()[0] - 1
            y_left = self.ax_left.get_ylim()[0] - 1

            # plot now on right and left axis at the sime time to ensure legend
            if "style" in dict_line and dict_line["style"] is not None:
                try:
                    if (
                        "o" in dict_line["style"]
                    ):  # o is an empty circle from now on! Use '.' for filled points
                        (line,) = self.ax_right.plot(
                            x * self.plot_right.x_scale,
                            y * self.plot_right.y_scale,
                            dict_line["style"],
                            fillstyle="none",
                            label=label,
                            **dict_line["kwargs"],
                        )
                        (_line,) = self.ax_left.plot(
                            x_left,
                            y_left,
                            dict_line["style"],
                            fillstyle="none",
                            label=label,
                            **dict_line["kwargs"],
                        )
                    else:
                        (line,) = self.ax_right.plot(
                            x * self.plot_right.x_scale,
                            y * self.plot_right.y_scale,
                            dict_line["style"],
                            label=label,
                            **dict_line["kwargs"],
                        )
                        (_line,) = self.ax_left.plot(
                            x_left, y_left, dict_line["style"], label=label, **dict_line["kwargs"]
                        )
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.plot_right.name
                        + " for line with label "
                        + str(label)
                    ) from err
            else:
                try:
                    (line,) = self.ax_right.plot(
                        x * self.plot_right.x_scale,
                        y * self.plot_right.y_scale,
                        label=label,
                        **dict_line["kwargs"],
                    )
                    (_line,) = self.ax_left.plot(x_left, y_left, label=label, **dict_line["kwargs"])
                except ValueError as err:
                    raise ValueError(
                        "Too many values to unpack in plot "
                        + self.plot_right.name
                        + " for line with label "
                        + str(label)
                    ) from err
            self.lines_right.append(line)

        # labels (only y label needed)
        if use_tex:
            self.ax_right.set_ylabel(self.plot_right.y_label)
        else:
            self.ax_right.set_ylabel(tex_to_text(self.plot_right.y_label))

        # set scale and limits (only y label needed)
        self.ax_right.set_yscale(self.plot_right.y_axis_scale)

        if not all(lim is None for lim in self.plot_right.y_limits):
            self.ax_right.set_ylim(
                bottom=self.plot_right.y_limits[0], top=self.plot_right.y_limits[1]
            )

        # legend ( only once ! )
        if self.legend_location in [
            "upper right outer",
            "right mid",
        ]:  # not supported in matplotlib
            self.ax_left.legend(loc="upper right", frameon=self.legend_frame)
        else:
            self.ax_left.legend(loc=self.legend_location, frameon=self.legend_frame)

        if allowGrid:
            # Don't allow the axis to be on top of your data
            self.ax_left.set_axisbelow(True)
            # self.ax_right.set_axisbelow(True)

            # Turn on the minor TICKS, which are required for the minor GRID
            self.ax_left.minorticks_on()
            # self.ax_right.minorticks_on()

            # Customize the major grid and show only one grid!
            self.ax_left.grid(which="major", linewidth=0.65, linestyle="-", color=".85")
            # Customize the minor grid and show only one grid!
            self.ax_left.grid(which="minor", linewidth=0.65, linestyle="-", color=".85")

        if tight_layout:
            plt.tight_layout()

        if show:
            plt.show()

    def plot_pyqtgraph(self, *args, **kwargs):
        """At the moment only a pass through to the left plot..."""
        self.plot_left.plot_pyqtgraph(*args, **kwargs)

    def show_pyqtgraph(self, *args, **kwargs):
        self.plot_left.show_pyqtgraph(*args, **kwargs)

    def save_tikz(
        self,
        directory,
        file_name=None,
        width="\\textwidth",
        fontsize="normalsize",
        height=None,
        mark_repeat=1,
        extension=None,
        restrict_left=True,
        restrict_right=True,
        hide_second_ticks=False,
        hide_second_axis=False,
        standalone=False,
        build=False,
        clean=False,
        svg=False,
        png=False,
    ):
        """Save plot in directory and return name of the tikz file. The name of the tikz file will be the figure attribute self.name if not given.

        Parameters
        ----------
        hide_second_ticks : Bool, False
            If true, the y-tick lines of the second plot are not drawn.
        """
        if not isinstance(directory, Path):
            directory = Path(directory)
        os.makedirs(directory, exist_ok=True)

        ext_file = ".tex"
        if extension is not None:
            ext_file = "." + extension

        if file_name is None:
            file_name = slugify(self.name) + ext_file
        elif not file_name.endswith(ext_file):
            file_name = file_name + ext_file

        # create tikz files from the subplots
        # change names as these plots will only exists temporarily
        name_old_left = self.plot_left.name
        num_old_left = self.plot_left.num
        name_old_right = self.plot_right.name
        num_old_right = self.plot_right.num

        self.plot_left.name = name_old_left + "_tmp"
        self.plot_left.num = num_old_left + "_tmp"
        self.plot_right.name = name_old_right + "_tmp"
        self.plot_right.num = num_old_right + "_tmp"

        file_tikz_left = self.plot_left.save_tikz(
            directory,
            width=width,
            height=height,
            mark_repeat=mark_repeat,
            standalone=standalone,
            restrict=restrict_left,
            extension=extension,
        )
        file_tikz_right = self.plot_right.save_tikz(
            directory,
            width=width,
            height=height,
            mark_repeat=mark_repeat,
            standalone=standalone,
            restrict=restrict_right,
            extension=extension,
        )

        # open, read and delete the tikz files
        path_file_left = directory / file_tikz_left
        str_tikz_left = path_file_left.read_text()
        path_file_left.unlink()

        path_file_right = directory / file_tikz_right
        str_tikz_right = path_file_right.read_text()
        path_file_right.unlink()

        self.plot_left.name = name_old_left
        self.plot_left.num = num_old_left
        self.plot_right.name = name_old_right
        self.plot_right.num = num_old_right

        # find color definition from second file

        # add "scale only axis", which makes the y-labels appear correctly independent of figure size
        # add yticks of first y-axis only at left axis, else it looks ugly.
        str_tikz_right = str_tikz_right.replace(r"ytick pos=left", r"ytick pos=right")

        # change str_tikz_right:
        lines_str_tikz_right = str_tikz_right.splitlines()

        # find color definitions from right plot
        color_defs = [line for line in lines_str_tikz_right if "definecolor" in line]

        # find legend from left plot and replace it with labels, these are added later
        legend_entries_left = [
            line
            for line in str_tikz_left.splitlines()
            if "addlegendentry" in line and not "%" in line
        ]
        for i, entry in enumerate(legend_entries_left):
            str_tikz_left = str_tikz_left.replace(
                entry, "\\label{" + file_name.replace(".tex", "_") + str(i) + "}"
            )

        # find start:
        i_start = next(
            i_line for i_line, line in enumerate(lines_str_tikz_right) if r"\begin{axis}[" in line
        )
        lines_to_del = []
        i_line = 0

        for i_line, line in enumerate(lines_str_tikz_right[i_start:]):  # iterate over a copy..
            if line == "]":
                break

            if (
                line.startswith("xlabel")
                or line.startswith("xmajorgrids")
                or line.startswith("xminorgrids")
                or line.startswith("xtick")
                or line.startswith("minor xtick")
                or line.startswith("x ")
            ):
                lines_to_del.append(i_start + i_line)

        str_hide_second_axis = "hide y axis=true,\n"
        if not hide_second_axis:
            str_hide_second_axis = "% " + str_hide_second_axis

        str_hide_second_ticks = ",\n"
        y_label_def = "ylabel style={at={(1.32, 0.5)}, anchor=north},\n"
        if hide_second_ticks:
            str_hide_second_ticks = "ytick=\\empty,\n"
            y_label_def = "ylabel style={at={(1.02, 0.5)}, anchor=north},\n"
        y_label_def = ""

        lines_str_tikz_right.insert(
            i_start + i_line,
            (
                "hide x axis=true,\n"
                + str_hide_second_axis
                + "every outer y axis line/.append style={black},\n"
                + "scale only axis,"
                + "every y tick label/.append style={font=\\color{black}},\n"
                + "every y tick/.append style={black},\n"
                + y_label_def
                + "yticklabel style={text width=0.6em,align=left},\n"
                + "yticklabel pos=right,\n"
                + "axis x line*=bottom,\n"
                + str_hide_second_ticks
                + "axis y line*=right,"
            ),
        )

        for i_del in lines_to_del[::-1]:
            del lines_str_tikz_right[i_del]

        # after axis definition in right plot, add legend entries from left plot
        line_legend_left = "]\n" + "\n".join(
            [
                r"\addlegendimage{/pgfplots/refstyle="
                + file_name.replace(".tex", "_")
                + str(i)
                + "}"
                + entry
                for i, entry in enumerate(legend_entries_left)
            ]
        )
        for i, line in enumerate(lines_str_tikz_right):
            if line == "]":
                lines_str_tikz_right[i] = line_legend_left

        # create one big string from array of strings
        str_tikz_right = "\n".join(lines_str_tikz_right)

        # merge the strings
        # color defs from right plot
        color_defs = "\n".join(color_defs) + "\n\\begin{axis}"
        str_tikz_left = str_tikz_left.replace(r"\begin{axis}", color_defs)

        # from left plot everything including \end{axis} and before end{tikzpicture}
        i_left_end = str_tikz_left.find(r"\end{tikzpicture}")
        str_tikz_picture = str_tikz_left[:i_left_end]

        # append right plot starting after \begin{tikzpicture} and before \begin{axis}
        i_right_start = str_tikz_right.find(r"\begin{axis}")
        str_tikz_picture += "\n" + str_tikz_right[i_right_start:]

        # if legend location is upper right outer, shift to right
        if hide_second_ticks:
            str_tikz_picture = str_tikz_picture.replace(
                "at={(1.02,1.00)}, anchor=north west,", "at={(1.07,1.00)}, anchor=north west,"
            )
        else:
            str_tikz_picture = str_tikz_picture.replace(
                "at={(1.02,1.00)}, anchor=north west,", "at={(1.12,1.00)}, anchor=north west,"
            )

        # having y-major ticks makes these plots ugly. Either rescale the ticks or just remove them. At the moment, just remove
        str_tikz_picture = str_tikz_picture.replace("ymajorgrids", "")

        # correct sizes
        if width is not None:
            str_tikz_picture = str_tikz_picture.replace(
                "\\setlength\\figurewidth{60mm}\n", "\\setlength\\figurewidth{" + width + "}\n"
            )
        if height is not None:
            str_tikz_picture = str_tikz_picture.replace(
                "\\setlength\\figureheight{60mm}\n", "\\setlength\\figureheight{" + height + "}\n"
            )

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
                build_tex(path_file, wait=clean)
                build_png(path_file, wait=clean)
                ending_to_keep = ".png"
            else:
                build_tex(path_file, wait=clean)
                ending_to_keep = ".pdf"

            if clean:
                clean_tex_files(
                    directory, file_name.replace(ext_file, ""), keep=(ending_to_keep, ext_file)
                )

        return file_name
