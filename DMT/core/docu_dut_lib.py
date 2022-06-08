""" Automatic documentation for DutLib
"""
# Copyright (C) from 2022  SemiMod
# <https://gitlab.com/dmt-development/dmt-core>
#
# This file is part of DMT.
#
# DMT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DMT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
import copy
import datetime
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Optional, Union
import numpy as np
from scipy import interpolate
from DMT.config import COMMAND_TEX, DATA_CONFIG
from DMT.core import DutType, DutLib, specifiers, sub_specifiers, specifiers_ss_para
from DMT.core.plot import MIX, PLOT_STYLES, natural_scales, Plot
from DMT.external.os import recursive_copy, rmtree

try:
    from pylatex import Section, Subsection, SmallText, Tabular, NoEscape, Center, Figure
    from DMT.external.pylatex import SubFile, Tex
except ImportError:
    pass

# defaults for autodoc feature plots
PLOT_DEFAULTS = {
    DutType.npn: {
        "gummel_vbc": {
            "x_log": False,
            "y_log": True,
            "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            "quantity_x": specifiers.VOLTAGE + "B" + "E",
            "quantity_y": specifiers.CURRENT_DENSITY + "C",
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"Gummel @ $V_{\mathrm{BC}}$.",
        },
        "gummel_vbc_mark_ft": {
            "x_log": False,
            "y_log": True,
            "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            "quantity_x": specifiers.VOLTAGE + "B" + "E",
            "quantity_y": specifiers.CURRENT_DENSITY + "C",
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"Gummel @ $V_{\mathrm{BC}}$.",
        },
        "output_vbe": {
            "x_log": False,
            "y_log": False,
            "at": specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED,
            "quantity_x": specifiers.VOLTAGE + "C" + "E",
            "quantity_y": specifiers.CURRENT_DENSITY + "C",
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"Output @ $V_{\mathrm{BE}}$.",
        },
        "output_ib": {
            "x_log": False,
            "y_log": False,
            "at": specifiers.CURRENT_DENSITY + "B",
            "quantity_x": specifiers.VOLTAGE + "C" + "E",
            "quantity_y": specifiers.CURRENT_DENSITY + "C",
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"Output @ $I_{\mathrm{B}}$.",
        },
        "ft_jc_vbc": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.TRANSIT_FREQUENCY,
            "legend_location": "upper left",
            "y_limits": (0, None),
            "x_limits": (None, None),
            "tex": r"$f_{\mathrm{T}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{BC}}$.",
        },
        "fmax_jc_vbc": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.MAXIMUM_OSCILLATION_FREQUENCY,
            "legend_location": "upper left",
            "y_limits": (0, None),
            "x_limits": (None, None),
            "tex": r"$f_{\mathrm{max}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{BC}}$.",
        },
        "ft_jc_vce": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.TRANSIT_FREQUENCY,
            "legend_location": "upper left",
            "y_limits": (0, None),
            "x_limits": (None, None),
            "tex": r"$F_{\mathrm{T}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{CE}}$.",
        },
        "fmax_jc_vce": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + "C" + "E" + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.MAXIMUM_OSCILLATION_FREQUENCY,
            "legend_location": "upper left",
            "y_limits": (0, None),
            "x_limits": (None, None),
            "tex": r"$f_{\mathrm{max}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{CE}}$.",
        },
        "beta_jc_vbc": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.DC_CURRENT_AMPLIFICATION,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$\beta_{\mathrm{DC}} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
        },
        "rey21_f_vbe_vbc": {
            "x_log": True,
            "y_log": False,
            "at": [
                specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED,
                specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            ],
            "quantity_x": specifiers.FREQUENCY,
            "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$\Re \left\{ Y_{21} \right\} \left( f \right)$ @ $V_{\mathrm{BC}} @ V_{\mathrm{BE}}$.",
        },
        "imy11_f_vbe_vbc": {
            "x_log": True,
            "y_log": True,
            "at": [
                specifiers.VOLTAGE + "B" + "E" + sub_specifiers.FORCED,
                specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            ],
            "quantity_x": specifiers.FREQUENCY,
            "quantity_y": specifiers.SS_PARA_Y + "B" + "B" + sub_specifiers.IMAG,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$\Im \left\{ Y_{11} \right\} \left( f \right)$ @ $V_{\mathrm{BC}} @ V_{\mathrm{BE}}$.",
        },
        "y21_jc_vbc": {
            "x_log": True,
            "y_log": True,
            "at": [
                specifiers.FREQUENCY,
                specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            ],
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
        },
        "y21_jc_vbc_mark_ft": {
            "x_log": True,
            "y_log": True,
            "at": [
                specifiers.FREQUENCY,
                specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            ],
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
        },
        "y21_jc_vbc_mark_ft": {
            "x_log": True,
            "y_log": True,
            "at": [
                specifiers.FREQUENCY,
                specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            ],
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.SS_PARA_Y + "C" + "B" + sub_specifiers.REAL,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
        },
        "tj_jc_at_vbc": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + "B" + "C" + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.TEMPERATURE,
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "tex": r"$T_{\mathrm{j}} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
            "rth": 3e3,
        },
    },
}


class DocuDutLib(object):
    """Documentation of an DutLib

    Parameters
    ----------
    dut_lib : :class:`~DMT.core.DutLib`
        Library to document
    devices : Sequence[Mapping[str, object]]
        This list specifies which devices to select from the lib. Only needed if "dev_mode"="sel" in the mode argument.
        Each dict specifies a contact configuration, length and width. All devices that match these properties are used for plotting.
        Example::

            devices = [{
                'contact_config':'CBEBC',
                'length'        :2.8e-6,
                'width'         :0.22e-6,
            },]
    date : convertable to str
        Date of the documentation report.
    """

    def __init__(
        self, dut_lib: DutLib, devices: Optional[Sequence[Mapping[str, object]]] = None, date=None
    ):
        self.dut_lib = dut_lib

        if devices is None:
            self.duts = self.dut_lib.duts
        else:
            self.duts = []  # array of DMT Duts
            for device_specs in devices:
                for dut in self.dut_lib:
                    # check all properties of device_spec
                    ok = True
                    for device_spec, val in device_specs.items():
                        if isinstance(val, str):
                            dut_property = getattr(dut, device_spec)
                            if dut_property != val:
                                ok = False
                        elif isinstance(val, float):
                            dut_property = getattr(dut, device_spec)
                            try:
                                if not np.isclose(dut_property, val):
                                    ok = False
                            except ValueError:  # tetrodes will not work like this (tuple dut_property)
                                pass

                    if ok:
                        print("Found device " + dut.name + ".")
                        self.duts.append(dut)

        if not self.duts:
            raise IOError("Found 0 devices.")

        print("Search finished...\nFound " + str(len(self.duts)) + " devices for plotting.")

        if date is None:
            self.date = datetime.datetime.today().strftime("%Y-%m-%d")
        else:
            self.date = date

        self.plts = []

    def generate_docu(
        self,
        target_base_path: Union[str, Path],
        plot_specs: List[Dict],
        save_tikz_settings: Optional[Dict] = None,
        show: bool = False,
    ):
        """Generate the full documentation folder with all plots and files.

        Parameters
        ----------
        target_base_path : str | Path
            Target path
        plot_specs : List[Dict]
            Plot specs passed to :meth:`~DMT.core.docu_dut_lib.DocuDutLib.create_all_plots`
        save_tikz_settings : Dict
            Plot specs passed to :meth:`~DMT.core.docu_dut_lib.DocuDutLib.generate_all_plots`
        show : bool, optional
            If True, the plots are displayed before the documentation folder is created, by default False
        """
        self.create_all_plots(plot_specs)

        # TODO
        # technology
        # mcard
        # ADD data from mcard simulation

        if show:
            if len(self.plts) > 1:
                for plt in self.plts[:-1]:
                    plt.plot_pyqtgraph(show=False)

            self.plts[-1].plot_pyqtgraph(show=True)

        self.generate_all_plots(target_base_path, save_tikz_settings)

        self.create_documentation(target_base_path)

    def create_all_plots(
        self,
        plot_specs: List[Dict],
    ):
        """This method generates plots for selected devices in the DutLib in a highly configurable way.

        Parameters
        ----------
        plot_specs : [dict]
            For every plot type you want to create, this list contains one dict. Example::

                {
                    'type'        : 'ft_jc_vbc', #possible values are the plot_types that are stored in the defaults (see code below)
                    'exclude_at'  : [-0.2,0.5],  #every plot type generates lines "at" some quantity, e.g. gummel_vbc generates for every VBC. With this argument you can exclude lines.
                    'key'         : 'freq_vbc',  #data keys that will be used for this plot
                    'exact_match' : False,       #Bool, if True, use only keys that match "key" exactly
                    'FREQ'        : 10e9,        #optional, float: If given, use only data at FREQ
                    'xmin'        : 10e-2,       #optional, float: Minimum Value on x-axis to be displayed
                    'xmax'        : 1e2,         #optional, float: Maximum Value on x-axis to be displayed
                    'ymax'        : 300,         #optional, float: Maximum Value on y-axis to be displayed
                    'ymin'        : 0,           #optional, float: Minimum Value on y-axis to be displayed
                    'no_at'       : True,        #optional, Bool: if True, do not display the "at" quantities in the legend.
                },

        """
        plot_spec_defaults = {
            "style": MIX,
            "legend": True,
            "dut_type": DutType.npn,
            "no_at": False,  # no at_specifier= in legend
        }

        # set defaults
        for plot_spec in plot_specs:
            for key in plot_spec_defaults:
                if key not in plot_spec.keys():
                    plot_spec[key] = plot_spec_defaults[key]

        # check plot_spec
        for plot_spec in plot_specs:
            try:
                plot_type = plot_spec["type"]
            except KeyError as err:
                raise IOError("type not specified for plot specification.") from err

            valid_plots = PLOT_DEFAULTS[plot_spec["dut_type"]].keys()
            if not plot_type in valid_plots:
                raise IOError(
                    "Plot type "
                    + plot_type
                    + " not valid. Valid: "
                    + " ".join(str(PLOT_DEFAULTS.keys()))
                    + " ."
                )

            if not plot_spec["style"] in PLOT_STYLES:
                raise IOError("Plot style not valid. Valid: " + " ".join(PLOT_STYLES))

            if not "key" in plot_spec.keys():
                raise IOError("Database key not specified for plot of type " + plot_type + " .")

            # matching key?
            if "exact_match" not in plot_spec.keys():
                plot_spec["exact_match"] = False

        # ensure that plot with type gummel_vbc_mark_ft comes first
        for i, plot_spec in enumerate(plot_specs):
            if plot_spec["type"] == "gummel_vbc_mark_ft":
                if i == 0:
                    pass
                else:
                    plot_specs[0], plot_specs[i] = plot_specs[i], plot_specs[0]  # swap elements

                break

        print("Generating plots...")
        # for every plot try to generate appropriate plots
        self.plts = []
        for plot_spec in plot_specs:
            plot_type = plot_spec["type"]
            print("Generating plots of type " + plot_type + " .")

            style = plot_spec["style"]
            print("Chosen plot style: " + style)

            for dut in self.duts:
                # load default settings of plot
                try:
                    x_log = PLOT_DEFAULTS[dut.dut_type][plot_type]["x_log"]
                    y_log = PLOT_DEFAULTS[dut.dut_type][plot_type]["y_log"]
                    quantity_x = PLOT_DEFAULTS[dut.dut_type][plot_type]["quantity_x"]
                    quantity_y = PLOT_DEFAULTS[dut.dut_type][plot_type]["quantity_y"]
                    legend_location = PLOT_DEFAULTS[dut.dut_type][plot_type]["legend_location"]
                    at_specifier = PLOT_DEFAULTS[dut.dut_type][plot_type]["at"]
                except KeyError:
                    continue  # no plot_type in plot_defaults for this plot_spec

                # overwrite defaults with plot_spec
                try:
                    legend_location = plot_spec["legend_location"]
                except KeyError:
                    pass

                if not isinstance(at_specifier, list):
                    at_specifier = [at_specifier]

                quantities_to_ensure = [quantity_x, quantity_y] + at_specifier
                if "mark_ft" in plot_type:
                    quantities_to_ensure.append(specifiers.TRANSIT_FREQUENCY)
                    peaks = {"vbe": [], "jc": [], "vbc": []}  # store peak ft values for later

                at_scale = []
                for at_ in at_specifier:
                    try:
                        at_scale_ = natural_scales[at_.specifier]
                    except AttributeError:
                        at_scale_ = natural_scales[at_]

                    if at_ == specifiers.CURRENT + "B" or at_ == specifiers.CURRENT_DENSITY + "B":
                        at_scale_ = at_scale_ * 1e3

                    at_scale.append(at_scale_)

                print("Generating plot of type " + plot_type + " for dut " + dut.name + " ...")
                name = [
                    "dut_",
                    dut.name,
                    "_",
                    plot_type,
                ]
                if specifiers.TEMPERATURE in plot_spec.keys():
                    name.append("atT" + str(plot_spec[specifiers.TEMPERATURE]) + "K")
                if specifiers.FREQUENCY in plot_spec.keys():
                    name.append("atf" + str(plot_spec[specifiers.FREQUENCY] * 1e-9) + "GHz")

                for at_ in at_specifier:
                    name.append("at" + at_)

                name = "_".join(name)

                # calc drawn emitter windows area
                AE0_drawn = dut.width * dut.length * dut.contact_config.count("E")

                # find temperatures
                temps = []
                for key in dut.data.keys():
                    temps.append(dut.get_key_temperature(key))
                temps = list(set(temps))

                for temp in temps:

                    y_scale = 1
                    x_label = None  # autolabel
                    y_label = None
                    if (
                        quantity_y.specifier in specifiers.SS_PARA_Y
                    ):  # special cases that I do not want in DMT
                        y_scale = 1e3 / (1e6 * 1e6)  # mS/um^2
                        y_label = r"$\Re{ \left\{ Y_{21} \right\} } / \si{\milli\siemens\per\square\micro\meter } $"

                    plt = Plot(
                        name,
                        style=style,
                        num=name,
                        x_specifier=quantity_x,
                        y_specifier=quantity_y,
                        x_log=x_log,
                        y_log=y_log,
                        y_scale=y_scale,
                        x_label=x_label,
                        y_label=y_label,
                        legend_location=legend_location,
                    )
                    plt.dut_name = dut.name
                    plt.plot_type = plot_type
                    plt.dut = dut
                    plt.temp = temp
                    plt.plot_spec = plot_spec

                    n = 0
                    for key in dut.data.keys():
                        # selected only keys at temp
                        if not dut.get_key_temperature(key) == temp:
                            continue

                        if specifiers.TEMPERATURE in plot_spec.keys():
                            if temp != plot_spec[specifiers.TEMPERATURE]:
                                continue  # key not suitable

                        match = False
                        if plot_spec["exact_match"]:
                            match = plot_spec["key"] == dut.split_key(key)[-1]
                        else:
                            match = plot_spec["key"] in key

                        if match:
                            df = dut.data[key]
                            if specifiers.FREQUENCY in plot_spec.keys():
                                try:
                                    df = df[
                                        df[specifiers.FREQUENCY] == plot_spec[specifiers.FREQUENCY]
                                    ]
                                except KeyError:
                                    pass

                            for quantity in quantities_to_ensure:
                                try:
                                    df.ensure_specifier_column(
                                        quantity, area=AE0_drawn, ports=dut.ac_ports
                                    )
                                except KeyError:
                                    if quantity == specifiers.TEMPERATURE:
                                        # calculate rough temperature
                                        pdiss = (
                                            df[specifiers.CURRENT + "C"].to_numpy()
                                            * df[specifiers.VOLTAGE + "C"].to_numpy()
                                        )

                                        # for the time beeing, only works for CBEBC devices...
                                        # calculate rth parameter
                                        a = (
                                            4.0
                                            * self.dut_lib.dut_ref.length
                                            / self.dut_lib.dut_ref.width
                                        )
                                        F_th = 1
                                        if a > 0.0:
                                            F_th = self.dut_lib.dut_ref.length / np.log(a)
                                        SRTHRM = plot_spec["rth"] / F_th

                                        # scale
                                        a = 4.0 * dut.length / dut.width
                                        F_th = 1
                                        if a > 0.0:
                                            F_th = dut.length / np.log(a)
                                        rth = SRTHRM * F_th

                                        df.loc[:, quantity] = temp + pdiss * rth
                                        dut.rth = rth

                                try:
                                    if quantity.specifier in specifiers_ss_para.SS_PARA_Y:
                                        df.loc[:, quantity] = df[quantity] / AE0_drawn
                                except:
                                    pass

                            at_vals = []
                            for i, at_ in enumerate(at_specifier):
                                at_val = df[at_].to_numpy()
                                if at_.specifier == specifiers.VOLTAGE:
                                    at_val = np.round(at_val, decimals=3)
                                    at_val = np.unique(at_val)
                                elif at_.specifier == specifiers.CURRENT:
                                    at_val = np.round(at_val, decimals=8)
                                    at_val = np.unique(at_val)
                                elif at_.specifier == specifiers.CURRENT_DENSITY:
                                    at_val = np.round(at_val, decimals=0)
                                    at_val = np.unique(at_val)

                                if "at_vals" in plot_spec:
                                    at_val = plot_spec["at_vals"][i]
                                    if not isinstance(at_val, list):
                                        at_val = [at_val]

                                at_vals.append(at_val)

                            units = []
                            for i, at_ in enumerate(at_specifier):
                                units.append(at_.get_tex_unit(scale=at_scale[i]))

                            f = []
                            if len(at_specifier) == 1:
                                for point in at_vals[0]:
                                    f.append((point,))
                            elif len(at_specifier) == 2:
                                f = [(x, y) for x in at_vals[0] for y in at_vals[1]]
                            else:
                                raise IOError("at with more than two specifiers not implemented.")

                            for point in f:
                                df_filter = True
                                at_str = r"$"
                                for i, (speci, u, scale_) in enumerate(
                                    zip(at_specifier, units, at_scale)
                                ):
                                    df_filter = np.logical_and(
                                        df_filter, np.isclose(df[speci], point[i], rtol=1e-3)
                                    )
                                    if at_str != r"$":
                                        at_str += r",\,"
                                    if plot_spec["no_at"]:
                                        at_str += r"{0:1.2f}".format(point[i] * scale_) + u
                                    else:
                                        at_str += (
                                            speci.to_tex()
                                            + r" = {0:1.2f}".format(point[i] * scale_)
                                            + u
                                        )

                                at_str += r"$"
                                df_tmp = df[df_filter]
                                x = df_tmp[quantity_x].to_numpy()
                                y = df_tmp[quantity_y].to_numpy()

                                # device if legend is wanted...default yes
                                kwargs = {}
                                if plot_spec["legend"]:
                                    kwargs["label"] = at_str

                                plt.add_data_set(
                                    x,
                                    y,
                                    **kwargs,
                                )

                                # add dots at peak ft
                                if "mark_ft" in plot_type:
                                    ft = df_tmp[specifiers.TRANSIT_FREQUENCY].to_numpy() * 1e-9
                                    interp_fun_ft = interpolate.interp1d(x, ft)
                                    interp_fun_ic = interpolate.interp1d(x, y)

                                    index_peak_ft = np.argmax(ft)
                                    try:
                                        vbe_new = np.linspace(
                                            x[index_peak_ft - 10], x[index_peak_ft + 10], 201
                                        )  # may error
                                    except IndexError:
                                        vbe_new = np.linspace(
                                            x[index_peak_ft - 10], x[-1], 201
                                        )  # may error

                                    index_peak_ft = np.argmax(interp_fun_ft(vbe_new))

                                    vbe_peak = vbe_new[index_peak_ft]
                                    jc_peak = interp_fun_ic(vbe_new[index_peak_ft])
                                    vbc_peak = point

                                    plt.add_data_set(
                                        np.tile(np.array(vbe_peak), 5),
                                        np.tile(np.array(jc_peak), 5),
                                        style=" ök",  # black dots
                                    )
                                    peaks["vbe"].append(np.tile(vbe_peak, 10))
                                    peaks["jc"].append(np.tile(jc_peak, 10))
                                    peaks["vbc"].append(np.tile(point[0], 10))

                                n = n + 1

                            if "ymin" in plot_spec.keys() or "ymax" in plot_spec.keys():
                                if not "ymin" in plot_spec.keys():
                                    plot_spec["ymin"] = None
                                if not "ymax" in plot_spec.keys():
                                    plot_spec["ymax"] = None
                                plt.y_limits = (plot_spec["ymin"], plot_spec["ymax"])

                            else:
                                try:
                                    plt.y_limits = PLOT_DEFAULTS[plot_type]["y_limits"]
                                except KeyError:
                                    pass

                            if "xmin" in plot_spec.keys() or "xmax" in plot_spec.keys():
                                if not "xmin" in plot_spec.keys():
                                    plot_spec["xmin"] = None
                                if not "xmax" in plot_spec.keys():
                                    plot_spec["xmax"] = None
                                plt.x_limits = (plot_spec["xmin"], plot_spec["xmax"])

                            else:
                                try:
                                    plt.x_limits = PLOT_DEFAULTS[plot_type]["x_limits"]
                                except KeyError:
                                    pass

                    # plots that required to mark peak of ft are accounted for here.
                    if plot_type == "gummel_vbc_mark_ft":
                        dut.peaks = peaks
                    elif plot_type == "output_ib":  # add ft peaks if they exist
                        try:
                            peaks = dut.peaks
                            jc = np.array(peaks["jc"]).flatten()
                            vbe = np.array(peaks["vbe"]).flatten()
                            vbc = np.array(peaks["vbc"]).flatten()
                            vce = vbe - vbc

                            inds = vce.argsort()
                            plt.add_data_set(
                                vce[inds],
                                jc[inds],
                                style="-ök",  # black dots
                            )
                        except AttributeError:
                            pass

                    print(
                        "...finished plot of type "
                        + plot_type
                        + " for dut "
                        + dut.name
                        + " , found "
                        + str(n)
                        + " lines."
                    )

                    if n == 0:
                        print("Found no lines for plot " + plot_type + " .")
                    else:
                        self.plts.append(plt)

    def generate_all_plots(
        self, target_base_path: Union[str, Path], save_tikz_settings: Optional[Dict] = None
    ):
        """Generates the plot tex and pdf files.

        If a plot with the same name already exists, it is deleted before the new is created.

        Parameters
        ----------
        target_base_path : str | Path
            Target base path. Inside this folder the plots will be placed in a "figs" subfolder.
        save_tikz_settings : Dict
            This dict specifies how the plots will be stored, they are directly used as parameters for :meth:`~DMT.core.Plot.save_tikz`. Example::

                save_tikz_settings = {
                    'width'      : '4.5in', #width of the Tikz Pictures
                    'height'     : '4.5in', #height of the Tikz Pictures
                    'fontsize'   : 'Large', #Fontsize Tex specification
                    'clean'      : True,    #If True: remove all files except rendered picture after build
                    'svg'        : False    #bool, False: If True, build svg files instead of pdf files.
                    'build'      : True     #bool, True: If True, build the Tex files using pdflatex compiler. Else only print .tex files.
                    'mark_repeat': 20       #int,20: Only show every nth marker, where n=mark_repeat.
                    'clean'      : False,   #bool, False: Remove all files except *.pdf files in plots. Schroeter likes this.
                }

        """
        if isinstance(target_base_path, Path):
            base_path = target_base_path
        else:
            base_path = Path(target_base_path)

        save_tikz_settings_defaults = {
            "width": "3in",
            "height": "5in",
            "standalone": True,
            "svg": False,
            "build": True,
            "mark_repeat": 20,
            "clean": False,  # Remove all files except *.pdf files in plots
        }

        if save_tikz_settings is None:
            save_tikz_settings = save_tikz_settings_defaults
        else:
            for key in save_tikz_settings_defaults:
                if not key in save_tikz_settings.keys():
                    save_tikz_settings[key] = save_tikz_settings[key]

        for plt in self.plts:
            plot_path = (
                base_path / "figs" / plt.dut_name / ("T" + str(plt.temp) + "K") / plt.plot_type
            )

            if plt.plot_type == "tj_jc_at_vbc":
                plot_path = (
                    base_path
                    / "figs"
                    / plt.dut_name
                    / ("T" + str(plt.temp) + "K")
                    / (plt.plot_type + "rth_" + "{0:1.1f}".format(plt.dut.rth * 1e-3) + "kWperK")
                )

            if plot_path.exists():
                rmtree(plot_path)

            plot_path.mkdir(parents=True, exist_ok=True)

            # special output from plot_spec
            save_tikz_settings_tmp = copy.deepcopy(save_tikz_settings)
            for special in ["width", "height"]:
                try:
                    save_tikz_settings_tmp[special] = plt.plot_spec[special]
                except KeyError:
                    continue

            plt.legend_location = "upper right outer"
            filename = plt.save_tikz(plot_path, **save_tikz_settings_tmp)

            plt.path = plot_path / filename.replace("tex", "pdf")

    def create_documentation(self, target_base_path: Union[str, Path]):
        """Generates the other tex files from the template.

        The template path from the config is used. The key is::

            directories:
                libautodoc: null

        If None/null, the DMT supplied template is used.

        Parameters
        ----------
        target_base_path : str | Path
            Target path for the documentation report.
        """
        if isinstance(target_base_path, Path):
            destination = target_base_path
        else:
            destination = Path(target_base_path)

        dir_source = DATA_CONFIG["directories"]["libautodoc"]

        destination.mkdir(parents=True, exist_ok=True)

        recursive_copy(dir_source, destination)

        try:
            # now rename _x_title and _author
            string_deckblatt = (destination / "content" / "deckblatt.tex").read_text()
            string_deckblatt = string_deckblatt.replace("_author", DATA_CONFIG["user_name"])
            string_deckblatt = string_deckblatt.replace("_x_title", str("B11").replace("_", r"\_"))
            string_deckblatt = string_deckblatt.replace(
                "_wafer", str(self.dut_lib.wafer).replace("_", r"\_")
            )
            string_deckblatt = string_deckblatt.replace(
                "_date_TO", str(self.dut_lib.date_tapeout).replace("_", r"\_")
            )
            string_deckblatt = string_deckblatt.replace(
                "_date_received", str(self.dut_lib.date_received).replace("_", r"\_")
            )
            string_deckblatt = string_deckblatt.replace(
                "_date_docu", str(self.date).replace("_", r"\_")
            )

            (destination / "content" / "deckblatt.tex").write_text(string_deckblatt)
        except FileNotFoundError:
            pass

        # finish copy template

        # subfile that contains overview of library
        lib_tex = SubFile(master="../documentation.tex")
        lib_tex.append(self.dut_lib.toTex())

        # subfile that contains all plots
        plots_tex = SubFile(master="../documentation.tex")
        doc = Tex()
        for dut in self.duts:
            with doc.create(Section(dut.name)):
                plts_for_this_dut = []
                for plt in self.plts:
                    if plt.dut == dut:
                        plts_for_this_dut.append(plt)

                temps = []
                for plt in plts_for_this_dut:
                    temps.append(plt.temp)

                temps = list(set(temps))

                for temp in temps:
                    with doc.create(Subsection("T=" + str(temp) + "K")):
                        for plt in plts_for_this_dut:
                            if plt.temp == temp:
                                # check if plot exists:
                                # Why? The plots are added as images not as tikz plots Oo
                                if plt.path.is_file():
                                    doc.append(NoEscape(r"\FloatBarrier "))
                                    with doc.create(Figure(position="ht!")) as _plot:
                                        _plot.append(
                                            NoEscape(r"\setlength\figurewidth{\textwidth}")
                                        )
                                        # _plot.append(CommandInput(arguments=Arguments(plt.path)))
                                        # \includegraphics[scale=0.65]{screenshot.png}
                                        _plot.add_image('"' + str(plt.path) + '"')
                                        _plot.add_caption(
                                            NoEscape(
                                                PLOT_DEFAULTS[dut.dut_type][plt.plot_type]["tex"]
                                            )
                                        )
                                        # _plot.append(CommandLabel(arguments=Arguments(fig_name)))

                                    doc.append(NoEscape(r"\FloatBarrier "))

        # put into subfile
        plots_tex.append(doc)

        lib_tex.generate_tex(str(destination / "content" / "lib_overview"))
        plots_tex.generate_tex(str(destination / "content" / "lib_plots"))
