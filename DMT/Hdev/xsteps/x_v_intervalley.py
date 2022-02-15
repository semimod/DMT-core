""" Extracts the parameters of the Hdev intervalley frequency model.

Author: Markus Müller | Markus.Mueller3@tu-dresden.de
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

from DMT.core import constants, specifiers, sub_specifiers, set_col_name
from DMT.extraction import XStep, plot, IYNormLog, print_to_documentation

try:  # soft dependency
    from DMT.external.pylatex import Tex
    from pylatex import Alignat, NoEscape
except ImportError:
    pass


class XVIntervalley(XStep):
    """
    Parameters
    ----------
    name                    : str
        Name of this specific object.
    mcard                   : :class:`~DMT.core.mcard.MCard` or :class:`~DMT.core.mc_parameter.McParameterCollection`
        This MCard needs to hold all relevant parameters of the model and is used for simulations or model equation calculations.
    lib                     : :class:`~DMT.core.dut_lib.DutLib`
        This library of devices need to hold a relevant internal dut with data in one or more DataFrames as fitting reference.
    op_definition           : {key : float, tuple or list}
        Defines how to filter the given data in the duts by setting either a single value (float), a range (2-element tuple) or a list of values (list) for each variable to filter.

    model                   : :class:`~DMT.hl2.hl2_model.Hl2Model`
        Model object with all model equations used for this extraction step.
    mat                     : dict-like material defintion from Hdev material database
    valley                  : string specifying the valley to be extracted
    """

    def __init__(
        self,
        name,
        mcard,
        lib,
        op_definition,
        mat,
        valley_1,
        valley_2,
        possible_parameters=None,
        deembed_method=None,
        relevant_duts=None,
        to_optimize=None,
        **kwargs,
    ):
        self.model_function = self.model_intervalley
        self.model_function_info = {
            "depends": possible_parameters,
        }
        self.valley_1 = valley_1
        self.valley_2 = valley_2
        self.mat = mat

        if relevant_duts is None:
            raise IOError("Please specify the relevant duts keyword argument.")
        else:
            self.relevant_duts = relevant_duts

        super().__init__(
            name,
            mcard,
            lib,
            op_definition,
            to_optimize=to_optimize,
            deembed_method=deembed_method,
            **kwargs,
        )

        self.col_eabs = specifiers.FIELD
        self.col_dop = specifiers.NET_DOPING

    @plot
    @print_to_documentation
    def main_plot(self):
        """Overwrite main plot."""
        main_plot = super(XVIntervalley, self).main_plot(
            r"$ \nu_{\mathrm{"
            + self.valley_1
            + self.valley_2
            + r"}} \left( "
            + self.col_eabs.to_tex()
            + r" \right) $",
            x_label=r"E\left( \si{\kilo\volt\per\centi\meter} \right)",
            y_label=r"$\nu_{\mathrm{" + self.valley_1 + self.valley_2 + r"}}(\si{\tera\hertz})$",
            y_scale=1e-12,  # 1e-7*1e-2
            x_scale=1e-5,
        )
        return main_plot

    def get_tex(self):
        """Return a tex Representation of the Model that is beeing fitted. This can then be displayed in the UI."""
        return "v\\left( E \\right)"

    def ensure_input_correct_per_dataframe(self, dataframe, **_kwargs):
        """Search for all required columns in the data frames."""
        dataframe.ensure_specifier_column(self.col_eabs)
        dataframe.ensure_specifier_column(self.col_dop)

    def set_initial_guess(self, data_reference):
        """Find suitable initial guesses for (some of the) model parameters from the given reference data."""
        pass

    def init_data_reference_per_dataframe(self, dataframe, t_meas, **_kwargs):
        """Find the required data in the user supplied dataframe or database and write them into data_model attribute of XStep object."""
        eabs = dataframe[self.col_eabs].to_numpy()
        col = "v_" + self.valley_1 + self.valley_2
        v = dataframe[col].to_numpy()
        dop = dataframe[self.col_dop].to_numpy()
        dop = np.unique(dop)
        for dop_ in dop:
            eabs = eabs[np.logical_not(np.isnan(v))]
            v = v[np.logical_not(np.isnan(v))]

            line = {
                "x": eabs,
                "y": v,
                specifiers.TEMPERATURE: t_meas,
                "t_dev": t_meas,
                "dop": dop_,
            }
            self.data_reference.append(line)
            self.labels.append(
                r"$ T=\SI{"
                + str(t_meas)
                + r"}{\kelvin}\, , N_{\mathrm{I}}=\SI{"
                + str(dop_)
                + r"}{\per\cubic\centi\meter} $"
            )  # ensures nice labels in the plot

    def fit(self, line, paras_model):
        """We acces the Hdev shared library directly here."""
        kwargs = paras_model.to_kwargs()
        line["y"] = self.model_intervalley(line["x"], line["t_dev"], line["dop"], **kwargs)
        return line

    def model_intervalley(self, field, temp, dop, *, val0=None, **kwargs):
        # f_crit = kwargs ['f0']*( 1+ (dop/kwargs[ 'dop_crit' ])**kwargs['zeta_dop'] )
        # return kwargs['a']*np.log(1+np.exp((field-f_crit)/1e5))

        paras = self.relevant_duts[0].get_recombination_paras(self.mat, "intervalley")
        for key in kwargs.keys():
            setattr(paras, key, kwargs[key])
        self.relevant_duts[0].set_recombination_paras(self.mat, paras)
        return val0 + self.relevant_duts[0].get_intervalley_rate(
            self.mat, self.valley_1, self.valley_2, field, temp, dop
        )
