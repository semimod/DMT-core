""" Step to fit a Hdev TCAD model to measurement data.

Author: Markus Müller       | Markus.Mueller3@tu-dresden.de
"""
# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-device>
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
import numpy as np

from DMT.config import DATA_CONFIG
from DMT.core import (
    Plot,
    specifiers,
    sub_specifiers,
    Sweep,
    memoize,
    DataFrame,
    natural_scales,
    DutType,
)
from DMT.extraction import XStep, plot, find_nearest_index, IYNormLog, print_to_documentation
from DMT.Hdev import DutHdev


class XFitCOOS(XStep):
    """This XStep can fit measurement data to a TCAD model implemented in Hdev.

    Parameters
    ----------
    name            : str
        Name of this specific xcjei object.
    mcard           : :class:`~DMT.core.mcard.MCard` or :class:`~DMT.core.mc_parameter.McParameterCollection`
        This MCard needs to hold all relevant parameters of the model and is used for simulations or model equation calculations.
    lib             : :class:`~DMT.core.dut_lib.DutLib`
        This library of devices needs to hold a relevant reference dut with data in one or more DataFrames.
    op_definition   : {key : float, tuple or list}
    get_inp : callable
        for a given line and modelcard, return a Hdev device definition.
    """

    def __init__(
        self,
        name,
        mcard,
        lib,
        op_definition,
        get_inp,
        sim_dir=DATA_CONFIG["directories"]["database"],
        database_dir=None,
        relevant_duts=None,
        to_optimize=None,
        model_deemb_method=None,
        fit_along=None,
        technology=None,
        **kwargs,
    ):

        self.get_inp = get_inp

        self.fit_along = fit_along
        if self.fit_along is None:
            self.fit_along = self.inner_sweep_voltage

        if self.quantity_fit is None:
            raise IOError("DMT -> XVerify: you did not specify a quantity to fit.")

        # init the super class
        super().__init__(
            name,
            mcard,
            lib,
            op_definition,
            DutCircuitClass=DutCOOS,
            circuit_sim_dir=sim_dir,
            circuit_database_dir=database_dir,
            to_optimize=to_optimize,
            technology=technology,
            specifier_paras={
                "inner_sweep_voltage": specifiers.VOLTAGE + ["B", "E"],
                "outer_sweep_voltage": specifiers.VOLTAGE + ["B", "C"],
                "quantity_fit": None,
            },
            **kwargs,
        )

        self.inner_sweep_voltage = self.specifier_paras["inner_sweep_voltage"]
        self.outer_sweep_voltage = self.specifier_paras["outer_sweep_voltage"]
        self.quantity_fit = self.specifier_paras["quantity_fit"]

        self.iynorm = IYNormLog
        self.is_ac = False
        self.model_deemb_method = model_deemb_method

        # define a set of specifiers that we always wish to have next to inner_sweep_voltage, outer_sweep_voltage and quantity_fit (minimum requirement)
        self.dc_specifiers = []
        self.dc_specifiers.append(
            specifiers.VOLTAGE + ["B", "E"]
        )  # i did not really find where we need them ?!? In the
        self.dc_specifiers.append(specifiers.VOLTAGE + ["B", "C"])
        self.dc_specifiers.append(specifiers.VOLTAGE + ["C", "E"])

        self.dc_specifiers.append(specifiers.VOLTAGE + "B")
        self.dc_specifiers.append(specifiers.VOLTAGE + "E")
        self.dc_specifiers.append(specifiers.VOLTAGE + "C")

        self.dc_specifiers.append(specifiers.CURRENT + "C")
        self.dc_specifiers.append(specifiers.CURRENT + "B")
        self.required_specifiers = [
            self.inner_sweep_voltage,
            self.outer_sweep_voltage,
            self.quantity_fit,
        ]
        self.ac_specifiers = []
        self.ac_specifiers.append(specifiers.FREQUENCY)
        self.ac_specifiers.append(specifiers.TRANSIT_FREQUENCY)
        self.ac_specifiers.append(specifiers.MAXIMUM_OSCILLATION_FREQUENCY)
        self.ac_specifiers.append(specifiers.MAXIMUM_STABLE_GAIN)
        self.ac_specifiers.append(specifiers.UNILATERAL_GAIN)
        self.ac_specifiers.append(specifiers.SS_PARA_Y + ["B", "B"])
        self.ac_specifiers.append(specifiers.SS_PARA_Y + ["C", "B"])
        self.ac_specifiers.append(specifiers.SS_PARA_Y + ["B", "C"])
        self.ac_specifiers.append(specifiers.SS_PARA_Y + ["C", "C"])

        if self.fit_along not in self.required_specifiers:
            self.required_specifiers.append(self.fit_along)

        if relevant_duts is not None:
            self.relevant_duts = relevant_duts
        else:
            self.relevant_duts = [lib.dut_ref]

    @plot
    @print_to_documentation
    def main_plot(self):
        """Overwrite main plot."""
        if self.fit_along.specifier == specifiers.FREQUENCY:
            x_scale = 1e-9  # GHz
        else:
            x_scale = 1

        try:
            y_scale = natural_scales[self.quantity_fit.specifier]
        except KeyError:
            y_scale = 1
        try:
            x_scale = natural_scales[self.fit_along.specifier]
        except KeyError:
            x_scale = 1

        main_plot = super(XFitCOOS, self).main_plot(
            r"$ "
            + self.quantity_fit.to_tex()
            + r" \left( "
            + self.fit_along.to_tex()
            + r" \right) $",
            x_specifier=self.fit_along,
            y_specifier=self.quantity_fit,
            y_scale=y_scale,
            x_scale=x_scale,
        )
        if (
            self.quantity_fit.specifier == specifiers.CURRENT
            or self.fit_along == specifiers.FREQUENCY
            or self.quantity_fit == specifiers.CURRENT_DENSITY
        ):
            main_plot.y_axis_scale = "log"
        # if self.fit_along == specifiers.FREQUENCY: #x axis log bugs
        #     main_plot.x_axis_scale = 'log'
        main_plot.legend_location = "upper left"
        return main_plot

    def ensure_input_correct(self):
        """Search for all required columns in the data frames."""
        # determine if this is an AC verification?
        self.is_ac = False
        for dut in self.relevant_duts:
            for key in dut.data.keys():
                if self.validate_key(key):
                    if specifiers.FREQUENCY in dut.data[key].columns:  # AC
                        self.is_ac = True

        # ok, we also need AC specifiers
        self.required_specifiers += self.dc_specifiers
        if self.is_ac:
            self.required_specifiers += self.ac_specifiers

        # now ensure the required specifiers
        for dut in self.relevant_duts:
            for key in dut.data.keys():
                if self.validate_key(key):
                    try:
                        for specifier in self.required_specifiers:
                            dut.data[key].ensure_specifier_column(specifier, ports=dut.nodes)

                    except KeyError as err:
                        raise IOError(
                            "The column "
                            + specifier
                            + " was missing in the data frame with the key "
                            + key
                            + "."
                        ) from err

    def init_data_reference(self):
        """Find the required data in the user supplied dataframe or database and write them into data_model attribute of XStep object."""
        col_outer = self.outer_sweep_voltage
        col_inner = self.inner_sweep_voltage
        for dut in self.relevant_duts:
            for key in dut.data.keys():
                if self.validate_key(key):
                    temp = dut.get_key_temperature(key)
                    df = dut.data[key]
                    outer_unique = np.unique(df[col_outer].to_numpy(copy=True).round(2))  # cheat
                    for v_outer in outer_unique:
                        data = df[np.isclose(df[col_outer], v_outer, rtol=1e-2)]

                        outputdef = self.required_specifiers
                        othervar = {specifiers.TEMPERATURE: temp}
                        sweepdef = Sweep.get_sweep(
                            data, self.inner_sweep_voltage, self.outer_sweep_voltage
                        )

                        if self.is_ac:
                            if len(data[specifiers.FREQUENCY].unique()) == 1:
                                sweepdef.append(
                                    {
                                        "var_name": specifiers.FREQUENCY,
                                        "sweep_order": 4,
                                        "sweep_type": "CONST",
                                        "value_def": data[specifiers.FREQUENCY].unique(),
                                    },
                                )
                            else:
                                sweepdef.append(
                                    {
                                        "var_name": specifiers.FREQUENCY,
                                        "sweep_order": 4,
                                        "sweep_type": "LIST",
                                        "value_def": data[specifiers.FREQUENCY].unique(),
                                    },
                                )

                        if self.fit_along == self.inner_sweep_voltage:
                            line = {
                                "x": data[self.fit_along].to_numpy(),
                                "y": np.real(data[self.quantity_fit].to_numpy()),
                                "sweep": Sweep(
                                    self.key,
                                    sweepdef=sweepdef,
                                    outputdef=outputdef,
                                    othervar=othervar,
                                ),
                                specifiers.TEMPERATURE: temp,
                            }
                            for specifier in self.required_specifiers:
                                line[specifier] = data[specifier].to_numpy()
                            self.data_reference.append(line)
                            if len(self.relevant_duts) == 1:
                                self.labels.append(
                                    r"$"
                                    + self.outer_sweep_voltage.to_tex()
                                    + r" = \SI{"
                                    + f"{data[col_outer].to_numpy()[0]:.2f}"
                                    + r"}{\volt} $"
                                )  # ensures nice labels in the plot
                            else:
                                self.labels.append(
                                    r"$"
                                    + self.outer_sweep_voltage.to_tex()
                                    + r" = \SI{"
                                    + f"{data[col_outer].to_numpy()[0]:.2f}"
                                    + r"}{\volt}, \left( l_{\mathrm{E0}}, b_{\mathrm{E0}} \right) =\left( "
                                    + f"{dut.length * 1e6:.2f}"
                                    + ","
                                    + f"{dut.width * 1e6:.2f}"
                                    + r" \right)\si{\micro\meter} $"
                                )  # ensures nice labels in the plot
                        else:
                            # unique inner voltage
                            df_inner = data
                            df_inner[self.inner_sweep_voltage] = df_inner[
                                self.inner_sweep_voltage
                            ].round(
                                3
                            )  # cheat
                            inner_unique = df_inner[self.inner_sweep_voltage].unique()
                            for i_inner, v_inner in enumerate(inner_unique):
                                df_single_inner = df_inner[
                                    df_inner[self.inner_sweep_voltage] == v_inner
                                ]

                                line = {
                                    "x": df_single_inner[self.fit_along].to_numpy(),
                                    "y": np.real(df_single_inner[self.quantity_fit].to_numpy()),
                                    specifiers.TEMPERATURE: temp,
                                }
                                for specifier in self.required_specifiers:
                                    line[specifier] = df_single_inner[specifier].to_numpy()

                                # modify the sweep, so that inner sweep voltage becomes constant as well
                                for sub_sweep in sweepdef:
                                    if (
                                        sub_sweep["var_name"]
                                        == specifiers.VOLTAGE + self.inner_sweep_voltage.nodes[0]
                                    ):
                                        sub_sweep["sweep_type"] = "CONST"
                                        sub_sweep["value_def"] = [inner_unique[i_inner]]

                                line["sweep"] = Sweep(
                                    self.key,
                                    sweepdef=sweepdef,
                                    outputdef=outputdef,
                                    othervar=othervar,
                                )

                                self.data_reference.append(line)
                                if len(self.relevant_duts) == 1:
                                    self.labels.append(
                                        r"$("
                                        + self.outer_sweep_voltage.to_tex()
                                        + r","
                                        + self.inner_sweep_voltage.to_tex()
                                        + r") = ("
                                        + f"{v_outer:.2f}"
                                        + r","
                                        + f"{inner_unique[i_inner]:.2f}"
                                        + r")\SI{}{\volt} $"
                                    )  # ensures nice labels in the plot
                                else:
                                    self.labels.append(
                                        r"$"
                                        + self.outer_sweep_voltage.to_tex()
                                        + r" = \SI{"
                                        + f"{df_single_inner[col_outer].to_numpy()[0]:.2f}"
                                        + r"}{\volt}, \left( l_{\mathrm{E0}}, b_{\mathrm{E0}} \right) =\left( "
                                        + f"{dut.length * 1e6:.2f}"
                                        + ","
                                        + f"{dut.width * 1e6:.2f}"
                                        + r" \right)\si{\micro\meter} $"
                                    )  # ensures nice labels in the plot

    # ▲▲▲▲▲▲▲
    # These two functions need to go "hand in hand". The temperature that corresponds to each line is needed to allow multidimensional fits.
    # ▾▾▾▾▾▾▾▾

    def fit(self, line, paras_model, dut=None):
        """cite from XStep docs:
        | - Return the data_model's y values for the x-values, if the x-step uses a dut+sweep combination.
        |   In this cases, XStep already carried out dut+sweep simulations with the parameters before calling the function. Promised.
        |   Reason: This allows to use DMT's multithreading capabilities, speeding up the extraction significantly.
        """
        try:
            sweep = line["sweep"]
            key = dut.join_key(dut.get_sweep_key(sweep), "iv")
            data = dut.data[key]
        except KeyError:
            if "data" in locals():
                pass  # in case of key error, use data from line['sweep'] before... Oo
            else:
                raise IOError(
                    "DMT -> XVerify -> " + self.name + ": proably the simulation went wrong."
                )

        # single frequency ?
        if specifiers.FREQUENCY in self.op_definition.keys():
            if isinstance(self.op_definition[specifiers.FREQUENCY], (float, int)):
                data = data[
                    np.isclose(data[specifiers.FREQUENCY], self.op_definition[specifiers.FREQUENCY])
                ]

        data.ensure_specifier_column(self.quantity_fit, ports=dut.nodes)
        data.ensure_specifier_column(self.outer_sweep_voltage)
        data.ensure_specifier_column(self.inner_sweep_voltage)
        data.ensure_specifier_column(self.fit_along, ports=dut.nodes)

        for specifier in self.required_specifiers:
            data.ensure_specifier_column(specifier, ports=dut.nodes)

        # apply bounds from reference data to the simulated data
        # ..todo: alternative we could apply the bounds to the sweepdef. Maybe even smarter?
        # ..todo: this should be put into XStep anyway I think, since it could be valid for all steps that use DutCircuit
        if self.fit_along == self.inner_sweep_voltage:
            x_with_bounds = line["x"]
            i_min = find_nearest_index(x_with_bounds.min(), data[self.fit_along].to_numpy())
            i_max = find_nearest_index(x_with_bounds.max(), data[self.fit_along].to_numpy())
            if i_min > i_max:
                i_min, i_max = i_max, i_min

            data = data[i_min : i_max + 1]

            line["x"] = np.real(data[self.fit_along].to_numpy())
            line["y"] = np.real(data[self.quantity_fit].to_numpy())

            line[self.outer_sweep_voltage] = data[self.outer_sweep_voltage].to_numpy()
            line[self.inner_sweep_voltage] = data[self.inner_sweep_voltage].to_numpy()
            for specifier in self.required_specifiers:
                line[specifier] = data[specifier].to_numpy()

        else:
            # unique inner voltage
            df_inner = data
            df_inner[self.inner_sweep_voltage] = df_inner[self.inner_sweep_voltage].round(
                3
            )  # cheat
            inner_unique = df_inner[self.inner_sweep_voltage].unique()
            for v_inner in inner_unique:
                # get correct line :/
                if v_inner != line[self.inner_sweep_voltage][0]:
                    continue

                df_single_inner = df_inner[df_inner[self.inner_sweep_voltage] == v_inner]

                x_with_bounds = line["x"]
                i_min = find_nearest_index(
                    x_with_bounds.min(), df_single_inner[self.fit_along].to_numpy()
                )
                i_max = find_nearest_index(
                    x_with_bounds.max(), df_single_inner[self.fit_along].to_numpy()
                )
                if i_min > i_max:
                    i_min, i_max = i_max, i_min

                df_single_inner = df_single_inner[i_min : i_max + 1]

                line["x"] = np.real(df_single_inner[self.fit_along].to_numpy())
                line["y"] = np.real(df_single_inner[self.quantity_fit].to_numpy())

                line[self.outer_sweep_voltage] = np.real(
                    df_single_inner[self.outer_sweep_voltage].to_numpy()
                )
                line[self.inner_sweep_voltage] = np.real(
                    df_single_inner[self.inner_sweep_voltage].to_numpy()
                )
                # line[specifiers.TEMPERATURE]   = np.real(df_single_inner['TK'].to_numpy())
                for specifier in self.required_specifiers:
                    line[specifier] = df_single_inner[specifier].to_numpy()

        line["y"] = line["y"]
        return line

    # @memoize #here we memoize calc all, since this is slow with a circuit simulator
    def calc_all(self, *args, **kwargs):
        return super().calc_all(*args, **kwargs)

    def get_tex(self):
        return r"\text{TCAD calibration}"

    def set_initial_guess(self, data_reference):
        pass  # required to overwrite this, however not useful in such a general step

    def get_description(self):
        from pylatex import NoEscape
        from DMT.external.pylatex import Tex

        doc = Tex()
        doc.append(
            NoEscape(
                r"This extraction step compares $"
                + self.quantity_fit.to_tex()
                + r"$ as a function of $"
                + self.inner_sweep_voltage.to_tex()
                + r"$ at different $"
                + self.outer_sweep_voltage.to_tex()
                + r"$ from measurements to Hdev TCAD simulations based on augmented drift-diffusion transport."
            )
        )
        return doc

    def get_dut(self, line, paras_model):
        """Overwritten from XStep. See doc in XStep."""
        inp = self.get_inp(paras_model.to_kwargs())
        dut = DutCOOS(self.circuit_database_dir, DutType.npn, inp, reference_node="E")
        dut.sim_dir = self.circuit_sim_dir
        return dut
