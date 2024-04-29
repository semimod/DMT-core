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
import numpy as np
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Optional, Union
from joblib import Parallel, delayed
from scipy import interpolate
from DMT.config import COMMAND_TEX, DATA_CONFIG
from DMT.core import (
    DutType,
    DutLib,
    specifiers,
    sub_specifiers,
    MCard,
    DutCircuit,
    DutMeas,
    Sweep,
    SimCon,
)
from DMT.core.plot import MIX, PLOT_STYLES, natural_scales, Plot
from DMT.external.os import recursive_copy, rmtree

try:
    from pylatex import (
        Section,
        Subsection,
        Subsubsection,
        SmallText,
        Tabular,
        NoEscape,
        Center,
        Figure,
    )
    from pylatex.base_classes import Arguments
    from DMT.external.pylatex import SubFile, Tex, CommandInput, CommandLabel
except ImportError:
    pass

# defaults for autodoc feature plots
PLOT_DEFAULTS = {
    DutType.npn: {
        "gummel_vbc": {
            "x_log": False,
            "y_log": True,
            "at": specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED,
            "quantity_x": specifiers.VOLTAGE + ["B", "E"],
            "quantity_y": specifiers.CURRENT_DENSITY + "C",
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "caption": r"Gummel @ $V_{\mathrm{BC}}$.",
        },
        "gummel_vbc_mark_ft": {
            "x_log": False,
            "y_log": True,
            "at": specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED,
            "quantity_x": specifiers.VOLTAGE + ["B", "E"],
            "quantity_y": specifiers.CURRENT_DENSITY + "C",
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "caption": r"Gummel @ $V_{\mathrm{BC}}$.",
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
            "caption": r"Output @ $V_{\mathrm{BE}}$.",
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
            "caption": r"Output @ $I_{\mathrm{B}}$.",
        },
        "ft_jc_vbc": {
            "x_log": True,
            "y_log": False,
            "at": specifiers.VOLTAGE + ["B", "C"] + sub_specifiers.FORCED,
            "quantity_x": specifiers.CURRENT_DENSITY + "C",
            "quantity_y": specifiers.TRANSIT_FREQUENCY,
            "legend_location": "upper left",
            "y_limits": (0, None),
            "x_limits": (None, None),
            "caption": r"$f_{\mathrm{T}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{BC}}$.",
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
            "caption": r"$f_{\mathrm{max}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{BC}}$.",
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
            "caption": r"$F_{\mathrm{T}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{CE}}$.",
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
            "caption": r"$f_{\mathrm{max}} \left( J_{\mathrm{C}} \right) $ @ $V_{\mathrm{CE}}$.",
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
            "caption": r"$\beta_{\mathrm{DC}} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
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
            "caption": r"$\Re \left\{ Y_{21} \right\} \left( f \right)$ @ $V_{\mathrm{BC}} @ V_{\mathrm{BE}}$.",
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
            "caption": r"$\Im \left\{ Y_{11} \right\} \left( f \right)$ @ $V_{\mathrm{BC}} @ V_{\mathrm{BE}}$.",
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
            "caption": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
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
            "caption": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
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
            "caption": r"$\Re \left\{ Y_{21} \right\} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
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
            "caption": r"$T_{\mathrm{j}} \left( J_{\mathrm{C}} \right)$ @ $V_{\mathrm{BC}}$.",
            "rth": 3e3,
        },
    },
    DutType.n_mos: {
        "id(vg)": {
            "x_log": False,
            "y_log": False,
            "at": [specifiers.VOLTAGE + ["D"], specifiers.VOLTAGE + ["B"]],
            "quantity_x": specifiers.VOLTAGE + ["G"],
            "quantity_y": specifiers.CURRENT + ["D"],
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "caption": r"$I_{\mathrm{D}}(V_{\mathrm{G}})@V_{\mathrm{D}}$.",
        },
        "id(vd)": {
            "x_log": False,
            "y_log": False,
            "at": [specifiers.VOLTAGE + ["G"], specifiers.VOLTAGE + ["B"]],
            "quantity_x": specifiers.VOLTAGE + ["D"],
            "quantity_y": specifiers.CURRENT + ["D"],
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "caption": r"$I_{\mathrm{D}}(V_{\mathrm{D}})@V_{\mathrm{G}}$.",
        },
    },
    DutType.p_mos: {
        "id(vg)": {
            "x_log": False,
            "y_log": False,
            "at": [specifiers.VOLTAGE + ["D"], specifiers.VOLTAGE + ["B"]],
            "quantity_x": specifiers.VOLTAGE + ["G"],
            "quantity_y": specifiers.CURRENT + ["D"],
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "caption": r"$I_{\mathrm{D}}(V_{\mathrm{G}})@V_{\mathrm{D}}$.",
        },
        "id(vd)": {
            "x_log": False,
            "y_log": False,
            "at": [specifiers.VOLTAGE + ["G"], specifiers.VOLTAGE + ["B"]],
            "quantity_x": specifiers.VOLTAGE + ["D"],
            "quantity_y": specifiers.CURRENT + ["D"],
            "legend_location": "upper left",
            "y_limits": (None, None),
            "x_limits": (None, None),
            "caption": r"$I_{\mathrm{D}}(V_{\mathrm{D}})@V_{\mathrm{G}}$.",
        },
    },
}


def obtain(plot_spec, key, dut_type, plot_type, value_default=None):
    if key in plot_spec:
        return plot_spec[key]

    if dut_type in PLOT_DEFAULTS:
        if plot_type in PLOT_DEFAULTS[dut_type]:
            return PLOT_DEFAULTS[dut_type][plot_type].get(key, value_default)

    return value_default


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
        self,
        dut_lib: DutLib,
        devices: Optional[Sequence[Mapping[str, object]]] = None,
        date: Optional[str] = None,
        modelcard_dict: Optional[Dict[DutType, MCard]] = None,
        DutCircuitClass: Optional[DutCircuit] = None,
        dut_class_kwargs: Optional[Dict] = None,
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
                            if not val in dut_property:
                                ok = False
                        elif isinstance(val, float):
                            dut_property = getattr(dut, device_spec)
                            try:
                                if not np.isclose(dut_property, val):
                                    ok = False
                            except (
                                ValueError
                            ):  # tetrodes will not work like this (tuple dut_property)
                                pass
                        else:
                            dut_property = getattr(dut, device_spec)
                            if val != dut_property:
                                ok = False

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

        self.plts: List[Plot] = []

        self.modelcard_dict = modelcard_dict
        self.DutCircuitClass = DutCircuitClass
        if dut_class_kwargs is None:
            self.dut_class_kwargs = {}
        else:
            self.dut_class_kwargs = dut_class_kwargs

    def get_dut_sim(self, dut_meas: DutMeas) -> DutCircuit:
        """Retrieve a circuit dut view which should be compared to the given dut_meas"""
        if self.DutCircuitClass is not None:
            return self.DutCircuitClass(
                database_dir=None,
                dut_type=dut_meas.dut_type,
                input_circuit=self.modelcard_dict[dut_meas.dut_type],
                technology=dut_meas.technology,  # needed for scaling!
                width=dut_meas.width,
                length=dut_meas.length,
                contact_config=dut_meas.contact_config,
                nfinger=dut_meas.nfinger,
                reference_node=dut_meas.reference_node,
                **self.dut_class_kwargs,
            )
        else:
            return None

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

        if show and self.plts:
            for plt in self.plts:
                plt.plot_pyqtgraph(show=False)

            self.plts[0].show_pyqtgraph()

            for plt in self.plts:
                plt.mw_pg = None
                plt.pw_pg = None
                # remove the plot from the object to allow Parallel prcessing
                # pickle is used to transfer between processes

        self.generate_all_plots(target_base_path, save_tikz_settings)

        # sleep(30)

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
                    'simulate'    : True,        #optional, Bool: if True, a matching simulation is added to the plot, if not given, default is True
                },

        """
        plot_spec_defaults = {
            "style": MIX,
            "legend": True,
            "dut_type": DutType.npn,
            "no_at": False,  # no at_specifier= in legend
        }
        sim_con = SimCon()

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

            # valid_plots = PLOT_DEFAULTS[plot_spec["dut_type"]].keys()
            # if not plot_type in valid_plots:
            #     raise IOError(
            #         f"Plot type {plot_type} not valid. Valid: "
            #         + " ".join(str(PLOT_DEFAULTS.keys()))
            #         + " ."
            #     )

            if not plot_spec["style"] in PLOT_STYLES:
                raise IOError("Plot style not valid. Valid: " + " ".join(PLOT_STYLES))

            if not "key" in plot_spec.keys():
                raise IOError(f"Database key not specified for plot of type {plot_type}.")

            # matching key?
            if "exact_match" not in plot_spec.keys():
                plot_spec["exact_match"] = False

        # ensure that plot with type gummel_vbc_mark_ft comes first
        for i, plot_spec in enumerate(plot_specs):
            if plot_spec["type"] == "gummel_vbc_mark_ft":
                if i == 0:
                    pass
                else:
                    plot_specs[0], plot_specs[i] = (
                        plot_specs[i],
                        plot_specs[0],
                    )  # swap elements

                break

        print("Generating plots...")
        # for every plot try to generate appropriate plots
        self.plts = []
        for plot_spec in plot_specs:
            plot_type = plot_spec["type"]
            print(f"Generating plots of type {plot_type}.")

            style = plot_spec["style"]
            print(f"Chosen plot style: {style}")

            for dut in self.duts:
                if "dut_filter" in plot_spec:
                    if not plot_spec["dut_filter"](dut):
                        continue
                elif "dut_type" in plot_spec:
                    if not dut.dut_type.is_subtype(plot_spec["dut_type"]):
                        continue

                if obtain(plot_spec, "simulate", dut.dut_type, plot_type, True):
                    dut_sim = self.get_dut_sim(dut)
                else:
                    dut_sim = None

                quantity_x = obtain(plot_spec, "quantity_x", dut.dut_type, plot_type)
                x_log = obtain(plot_spec, "x_log", dut.dut_type, plot_type, value_default=False)

                x_scale = obtain(plot_spec, "x_scale", dut.dut_type, plot_type, value_default=None)

                quantity_y = obtain(plot_spec, "quantity_y", dut.dut_type, plot_type)
                quantities_y = None
                if quantity_y is None:
                    quantities_y = plot_spec["quantities_y"]
                    quantity_y = quantities_y[0]
                y_log = obtain(plot_spec, "y_log", dut.dut_type, plot_type, value_default=False)
                y_scale = obtain(plot_spec, "y_scale", dut.dut_type, plot_type, value_default=None)

                # load settings from plot_spec with additions from defaults
                legend_location = obtain(plot_spec, "legend_location", dut.dut_type, plot_type)
                at_specifier = obtain(plot_spec, "at", dut.dut_type, plot_type)

                if at_specifier is None:
                    at_specifier = []
                elif not isinstance(at_specifier, list):
                    at_specifier = [at_specifier]

                if "xmin" in plot_spec.keys() or "xmax" in plot_spec.keys():
                    x_limits = (plot_spec.get("xmin", None), plot_spec.get("xmax", None))
                else:
                    try:
                        x_limits = PLOT_DEFAULTS[dut.dut_type][plot_type]["x_limits"]
                    except KeyError:
                        x_limits = (None, None)

                if "ymin" in plot_spec.keys() or "ymax" in plot_spec.keys():
                    y_limits = (plot_spec.get("ymin", None), plot_spec.get("ymax", None))
                else:
                    try:
                        y_limits = PLOT_DEFAULTS[dut.dut_type][plot_type]["y_limits"]
                    except KeyError:
                        y_limits = (None, None)

                caption = obtain(plot_spec, "caption", dut.dut_type, plot_type)

                quantities_to_ensure = [quantity_x, quantity_y] + at_specifier
                if quantities_y is not None:
                    quantities_to_ensure += quantities_y

                if "mark_ft" in plot_type:
                    quantities_to_ensure.append(specifiers.TRANSIT_FREQUENCY)
                    peaks = {
                        "vbe": [],
                        "jc": [],
                        "vbc": [],
                    }  # store peak ft values for later

                at_scale = []
                for at_ in at_specifier:
                    try:
                        at_scale_ = natural_scales[at_.specifier]
                    except AttributeError:
                        at_scale_ = natural_scales[at_]

                    # if at_ == specifiers.CURRENT + "B" or at_ == specifiers.CURRENT_DENSITY + "B":
                    #     at_scale_ = at_scale_ * 1e3

                    at_scale.append(at_scale_)

                print(f"Generating plot of type {plot_type} for dut {dut.name} ...")
                name = [dut.name, plot_type]
                if specifiers.TEMPERATURE in plot_spec.keys():
                    name.append("atT" + str(plot_spec[specifiers.TEMPERATURE]) + "K")
                if specifiers.FREQUENCY in plot_spec.keys():
                    name.append("atf" + str(plot_spec[specifiers.FREQUENCY] * 1e-9) + "GHz")
                for at_ in at_specifier:
                    name.append("at" + at_)

                name = "_".join(name).replace(".", "p")

                # calc drawn emitter windows area
                try:
                    AE0_drawn = (
                        dut.width * dut.length * dut.contact_config.count("E") * dut.ndevices
                    )
                except (TypeError, AttributeError):
                    AE0_drawn = 1

                # find temperatures
                temps = []
                for key in dut.data.keys():
                    temp = dut.get_key_temperature(key)
                    if specifiers.TEMPERATURE in plot_spec and np.isclose(
                        temp, plot_spec[specifiers.TEMPERATURE]
                    ):
                        temps.append(dut.get_key_temperature(key))
                    elif specifiers.TEMPERATURE not in plot_spec:
                        temps.append(dut.get_key_temperature(key))

                temps = list(set(temps))

                for temp in temps:
                    plt = Plot(
                        name,
                        style=style,
                        num=name,
                        x_specifier=quantity_x,
                        y_specifier=quantity_y,
                        x_log=x_log,
                        y_log=y_log,
                        x_scale=x_scale,
                        y_scale=y_scale,
                        legend_location=legend_location,
                    )

                    plt.dut_name = (dut.name + f"{len(self.plts)}").replace(".", "p")
                    plt.plot_type = plot_type
                    plt.dut = dut
                    plt.temp = temp
                    plt.plot_spec = plot_spec
                    plt.caption = caption

                    for key in dut.data.keys():
                        # selected only keys at temp
                        if not dut.get_key_temperature(key) == temp:
                            continue

                        match = False
                        if plot_spec["exact_match"]:
                            if isinstance(plot_spec["key"], str):
                                match = plot_spec["key"] == dut.split_key(key)[-1]
                            else:
                                match = dut.split_key(key)[-1] in plot_spec["key"]
                        else:
                            if isinstance(plot_spec["key"], str):
                                match = plot_spec["key"] in key
                            else:
                                match = any(
                                    plot_spec_key in key for plot_spec_key in plot_spec["key"]
                                )

                        if match:
                            df = dut.data[key]
                            if specifiers.FREQUENCY in plot_spec.keys():
                                try:
                                    df = df[
                                        np.isclose(
                                            df[specifiers.FREQUENCY],
                                            plot_spec[specifiers.FREQUENCY],
                                        )
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

                            # units = []
                            # for i, at_ in enumerate(at_specifier):
                            #     units.append(at_.get_tex_unit(scale=at_scale[i]))

                            f = []
                            if len(at_specifier) == 0:
                                f = [None]
                            elif len(at_specifier) == 1:
                                for point in at_vals[0]:
                                    f.append((point,))
                            elif len(at_specifier) == 2:
                                f = [(x, y) for x in at_vals[0] for y in at_vals[1]]
                            else:
                                raise IOError("at with more than two specifiers not implemented.")

                            for point in f:
                                df_filter = True
                                at_str = ""
                                if point is None:
                                    df_tmp = df
                                else:
                                    for i, at_speci in enumerate(at_specifier):
                                        df_filter = np.logical_and(
                                            df_filter,
                                            np.isclose(df[at_speci], point[i], rtol=1e-3),
                                        )

                                        if at_str:
                                            at_str += r",\,"

                                        curr_str = at_speci.to_legend_with_value(
                                            point[i], decimals=2
                                        )

                                        if plot_spec["no_at"]:
                                            # only the number
                                            at_str += "$" + curr_str.split("=")[1]
                                        else:
                                            at_str += curr_str

                                    df_tmp = df[df_filter]

                                x = df_tmp[quantity_x].to_numpy()
                                y = df_tmp[quantity_y].to_numpy()

                                # device if legend is wanted...default yes
                                if "legend" in plot_spec and not plot_spec["legend"]:
                                    label = None
                                else:
                                    label = at_str

                                if quantities_y is None:
                                    plt.add_data_set(x, y, label=label)
                                else:
                                    for quant in quantities_y:
                                        plt.add_data_set(
                                            x, df_tmp[quant], label=f"${quant.to_tex():s}$"
                                        )

                                # add dots at peak ft
                                if "mark_ft" in plot_type:
                                    ft = df_tmp[specifiers.TRANSIT_FREQUENCY].to_numpy() * 1e-9
                                    interp_fun_ft = interpolate.interp1d(x, ft)
                                    interp_fun_ic = interpolate.interp1d(x, y)

                                    index_peak_ft = np.argmax(ft)
                                    try:
                                        vbe_new = np.linspace(
                                            x[index_peak_ft - 10],
                                            x[index_peak_ft + 10],
                                            201,
                                        )  # may error
                                    except IndexError:
                                        vbe_new = np.linspace(
                                            x[index_peak_ft - 10], x[-1], 201
                                        )  # may error

                                    index_peak_ft = np.argmax(interp_fun_ft(vbe_new))

                                    vbe_peak = vbe_new[index_peak_ft]
                                    jc_peak = interp_fun_ic(vbe_new[index_peak_ft])

                                    plt.add_data_set(
                                        np.tile(np.array(vbe_peak), 5),
                                        np.tile(np.array(jc_peak), 5),
                                        style=" ök",  # black dots
                                    )
                                    peaks["vbe"].append(np.tile(vbe_peak, 10))
                                    peaks["jc"].append(np.tile(jc_peak, 10))
                                    peaks["vbc"].append(np.tile(point[0], 10))

                                if dut_sim is not None:
                                    # get a sweep
                                    sweep = Sweep.get_sweep_from_dataframe(
                                        data=df_tmp,
                                        temperature=temp,
                                        outputdef=[quantity_x, quantity_y],
                                        # othervar={},
                                    )
                                    # simulate
                                    sim_con.append_simulation(dut=dut_sim, sweep=sweep)
                                    sim_con.run_and_read()
                                    # add to plot
                                    df_sim = dut_sim.get_data(sweep=sweep)
                                    df_sim.ensure_specifier_column(
                                        quantity_x, area=AE0_drawn, ports=dut.ac_ports
                                    )
                                    df_sim.ensure_specifier_column(
                                        quantity_y, area=AE0_drawn, ports=dut.ac_ports
                                    )
                                    plt.add_data_set(
                                        df_sim[quantity_x].to_numpy(),
                                        df_sim[quantity_y].to_numpy(),
                                        label=label + " sim",
                                    )

                            plt.x_limits = x_limits
                            plt.y_limits = y_limits

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
                        f"...finished plot of type {plot_type} for dut {dut.name}, found {len(dut.data)} lines."
                    )

                    if plt.data:
                        self.plts.append(plt)
                    else:
                        print("Found no lines for plot " + plot_type + ". Plot is not added!")

    def generate_all_plots(
        self,
        target_base_path: Union[str, Path],
        save_tikz_settings: Optional[Dict] = None,
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
            "width": "3.5in",
            "height": "4in",
            "standalone": True,
            "svg": False,
            "build": True,
            "mark_repeat": 20,
            "clean": True,  # Remove all files except *.pdf files in plots
        }

        if save_tikz_settings is None:
            save_tikz_settings = save_tikz_settings_defaults
        else:
            for key in save_tikz_settings_defaults:
                if not key in save_tikz_settings.keys():
                    save_tikz_settings[key] = save_tikz_settings[key]

        paths = Parallel(n_jobs=20, verbose=10)(
            _build_plot(plt, base_path, save_tikz_settings) for plt in self.plts
        )
        for i_plt, plt in enumerate(self.plts):
            plt.path = paths[i_plt]
        # for plt in self.plts:
        #     plot_path = (
        #         base_path / "figs" / plt.dut_name / ("T" + str(plt.temp) + "K") / plt.plot_type
        #     )

        #     if plt.plot_type == "tj_jc_at_vbc":
        #         plot_path = (
        #             base_path
        #             / "figs"
        #             / plt.dut_name
        #             / ("T" + str(plt.temp) + "K")
        #             / (plt.plot_type + "rth_" + "{0:1.1f}".format(plt.dut.rth * 1e-3) + "kWperK")
        #         )

        #     if plot_path.exists():
        #         rmtree(plot_path)

        #     plot_path.mkdir(parents=True, exist_ok=True)

        #     # special output from plot_spec
        #     save_tikz_settings_tmp = copy.deepcopy(save_tikz_settings)
        #     for special in ["width", "height"]:
        #         try:
        #             save_tikz_settings_tmp[special] = plt.plot_spec[special]
        #         except KeyError:
        #             continue

        #     plt.legend_location = "upper right outer"
        #     filename = plt.save_tikz(plot_path, **save_tikz_settings_tmp)

        #     plt.path = plot_path / filename.replace("tex", "pdf")

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
            string_deckblatt = string_deckblatt.replace(
                "_company", str(DATA_CONFIG["company"]).replace("_", r"\_")
            )
            string_deckblatt = string_deckblatt.replace(
                "_x_title", str(DATA_CONFIG["docu_topic"]).replace("_", r"\_")
            )
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
        dut_types = set([dut.dut_type for dut in self.duts])
        duts_sorted = sorted(self.duts, key=lambda dut_a: (dut_a.dut_type, dut_a.name))
        for dut_type in dut_types:
            duts_filtered = [dut for dut in duts_sorted if dut.dut_type == dut_type]
            with doc.create(Section(dut_type.string)):
                for dut in duts_filtered:
                    plts_for_this_dut = []
                    for plt in self.plts:
                        if plt.dut == dut:
                            plts_for_this_dut.append(plt)

                    if not plts_for_this_dut:
                        continue

                    with doc.create(Subsection(dut.name)):
                        temps = []
                        for plt in plts_for_this_dut:
                            temps.append(plt.temp)

                        temps = list(set(temps))

                        for temp in temps:
                            with doc.create(Subsubsection("T=" + str(temp) + "K", label=False)):
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
                                                _plot.add_image(
                                                    '"'
                                                    + str(plt.path.relative_to(destination))
                                                    + '"'
                                                )
                                                _plot.add_caption(NoEscape(plt.caption))
                                                # _plot.append(CommandLabel(arguments=Argument(plt.dut_name + plt.)))

                                            doc.append(NoEscape(r"\FloatBarrier "))

        # put into subfile
        plots_tex.append(doc)

        lib_tex.generate_tex(str(destination / "content" / "lib_overview"))
        plots_tex.generate_tex(str(destination / "content" / "lib_plots"))


@delayed
def _build_plot(plt, base_path, save_tikz_settings):
    plot_path = base_path / "figs" / plt.dut_name / ("T" + str(plt.temp) + "K") / plt.plot_type

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

    return plot_path / filename.replace("tex", "pdf")
