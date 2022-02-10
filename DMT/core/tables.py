from itertools import zip_longest
from pathlib import Path
from typing import List

from DMT.core import unit_registry

from pylatex import Tabular, NoEscape
import numpy as np

# Sciuntix doesnt do what i want exactly and neither does python formatting
def latex_float(val):
    if abs(val) >= 1e4:
        val = "{:g}".format(val)
    elif abs(val) >= 1e2:
        val = "{:.4g}".format(val)
    elif 1e-4 <= abs(val) < 1e-3:
        base = "{:.3g}".format(val * 1e4)
        return base + r" \times 10^{-4}"
    else:
        val = "{:.3g}".format(val)

    if "e" in val:
        base, exponent = val.split("e")
        return r"{0} \times 10^{{{1}}}".format(base, int(exponent))
    else:
        return val


class ReferenceTable:
    def __init__(
        self,
        parameters,
        reference_mc,
        non_symbol=" ",
        info_colums=(("l", "Method", r"\textbf{Reference}"),),
    ):
        """
        Makes generating pretty tables for comparing results for comparing extraction results to a reference modelcard easier
        """
        self.parameters = parameters

        self.non_symbol = NoEscape(r"{" + non_symbol + r"}")
        self.rows = []

        self.reference = []
        self.info_colum_positions = ""
        self.info_colum_names = []
        self.reference_info = []

        for (pos, name, reference_entry) in info_colums:
            self.info_colum_positions = self.info_colum_positions + pos
            self.info_colum_names.append(NoEscape(name))
            self.reference_info.append(NoEscape(reference_entry))

        self.reference = reference_mc.get(self.parameters)

    def process_row(self, info, values, calc_err=True):
        if len(self.info_colum_positions) > 1:
            res = []
            for colum in info:
                res.append(NoEscape("{" + colum + "}"))
        elif len(self.info_colum_positions) == 1:
            res = [info]

        if len(values) != len(self.parameters):
            raise ValueError("Incorrect Row length! Expected {} found {}")

        for val, ref in zip_longest(values, self.reference):
            if val is None:
                res.append(self.non_symbol)
            else:
                ref = ref.value
                if calc_err:
                    if ref == 0.0:
                        if abs(val) == abs(ref):
                            err = r"\quad(0)"
                        err = r"\quad(\infty)"
                    else:
                        err = np.abs(val - ref) / abs(ref) * 100
                        err = "\,(" + latex_float(err) + ")"
                else:
                    err = ""

                val = NoEscape(r"$" + latex_float(val) + err + "$")
                res.append(val)
        return res

    def to_list(self, vals, param_filter=None):
        res = []
        for param in self.parameters:
            if param in vals and (param_filter is None or param in param_filter):
                res.append(vals[param])
            else:
                res.append(None)
        return res

    def add_row(self, info, param_filter=None, **vals):
        res = []

        for param in self.parameters:
            if param in vals and (param_filter is None or param in param_filter):
                res.append(vals[param])
            else:
                res.append(None)

        self.rows.append(self.process_row(info, res))

    def reference_row(self):
        reference = []
        for ref in self.reference:
            reference.append(ref.value)

        return self.process_row(info=self.reference_info, values=reference, calc_err=False)

    def header_row(self, params_bold=True):
        header = self.info_colum_names.copy()
        for x in self.reference:
            unit = x.unit
            param = x.name
            if params_bold:
                param = r"\textbf{" + param + "}"

            if unit == unit_registry.dimensionless:
                header.append(NoEscape("{" + param + "}"))
            else:
                header.append(NoEscape("{" + param + r" (${:Lx}$)".format(unit) + "}"))

        return header

    def table_cotents(self, params_bold=True, transpose=False):
        rows = [self.header_row(params_bold)]
        for param_row in self.rows:
            rows.append(param_row)
        rows.append(self.reference_row())
        if transpose:
            return [list(x) for x in zip(*rows)]
        else:
            return rows

    def init_tabular(self, tranpose=False):
        if tranpose:
            positions = "c|" + "c" * (len(self.rows) + 1)
            return Tabular(positions, booktabs=True, width=len(self.rows) + 2)
        else:
            positions = self.info_colum_positions + "c" * len(self.parameters)
            return Tabular(
                positions, booktabs=True, width=len(self.info_colum_names) + len(self.parameters)
            )

    def dump_tabular(self, params_bold=True, transpose=False):
        tabular = self.init_tabular(transpose)
        rows = self.table_cotents(params_bold, transpose)
        if not transpose:
            tabular.add_row(rows[0])
            rows = rows[1:]
            tabular.add_hline()

        for row in rows:
            tabular.add_row(row)

        return tabular.dumps()

    def save_tabular(self, directory, file_name, params_bold=True, transpose=False):
        if not isinstance(directory, Path):
            directory = Path(directory)

        directory.mkdir(parents=True, exist_ok=True)
        if not file_name.endswith(".tex"):
            file_name = file_name + ".tex"
        file = directory / file_name
        file.write_text(self.dump_tabular(params_bold, transpose))


class XStepTestTable(ReferenceTable):
    def __init__(
        self, parameters, reference_mc, non_symbol=" ", has_plots=True, has_citations=True
    ):
        info = [("l", "DMT Class", r"\textbf{Reference}")]

        if has_citations:
            info.append(("l", "References", " "))

        if has_plots:
            info.append(("l", "Plots", " "))

        self.has_citations = has_citations
        self.has_plots = has_plots
        super().__init__(parameters, reference_mc, non_symbol, info_colums=info)

    def add_step(
        self, step, name_postfix="", additional_parameters=None, citations=None, plots=None
    ):
        info = [type(step).__name__ + name_postfix]

        if self.has_citations:
            info.append(NoEscape(r"\cite{" + citations + r"}"))

        if self.has_plots:
            if isinstance(plots, List):
                res = ""
                for plt in plots:
                    res = res + r"\ref{" + plt + "}, "
                res = res[0:-2]  # remove last comma
            else:
                res = r"\ref{" + plots + "}"
            info.append(NoEscape(res))

        if additional_parameters is None:
            filter = []
        else:
            filter = additional_parameters

        filter.extend(step.paras_to_optimize.to_kwargs().keys())
        self.add_row(info, param_filter=filter, **step.mcard.to_kwargs())
