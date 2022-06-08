""" DMT specific PyLaTeX classes and routines used for automatic documentations

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
from DMT.external.latex import build_tex

try:  # soft dependency: DMT can be used without pylatex...
    from pylatex import Section
    from pylatex import Package, NoEscape
    from pylatex.base_classes import CommandBase, Container
except ImportError:
    pass


class Tex(Section):
    """This is basically a Tex container as defined in Pylatex that can do nothing but contain Tex stuff."""

    def __init__(self, numbering=None, label=False, **kwargs):
        super().__init__(
            "dummy", numbering=None, label=label
        )  # dont need a title for a few tex commands

    def dumps(self):
        return self.dumps_content()


class Listing(Container):
    #: Default prefix to use with Marker
    marker_prefix = "listing"

    def __init__(
        self, content=None, file_path=None, language="TRADICA", caption=None, label=None, **kwargs
    ):
        super().__init__(**kwargs)

        self.language = language
        self.content = content
        self.file_path = file_path
        self.caption = caption
        self.label = label

    def dumps(self):
        if self.language == "TRADICA":
            str_language = (
                "backgroundcolor=\\color{lightgray!40},\n"
                + "breaklines=true, breakatwhitespace=true,\n"
                + "emph={[1]NAME, TRACE, OPTI, PHYS, TECH, DEVICE, OUTPUT, PGEN, RUN, END}, emphstyle={[1]\\bfseries},\n"
                + "emph={[2]UNIT_INP, PERMITT, BGP NARR, SAT_VELO, HOLE_MOBI, ELEC_MOBI, INFO_PROCESS, GEOM_DATA, ELEC_PAR, HICUM_PAR, MODEL_DEF, MISC_VAR, TRAN_CONF}, emphstyle={[2]\\color{Blue}},\n"
            )
        else:
            str_language = "language=" + self.language + ",\n"

        str_caption = "caption={:s},\n".format(self.caption) if self.caption is not None else ""
        str_label = "label={:s},\n".format(self.label) if self.label is not None else ""
        if self.file_path is None:
            return (
                "\\begin{lstlisting}[\n"
                + str_caption
                + str_label
                + str_language
                + "]\n"
                + self.content
                + "\\end{lstlisting}\n"
            )
        else:
            return (
                "\\lstinputlisting[\n"
                + str_caption
                + str_label
                + str_language
                + "]\n"
                + "{"
                + self.file_path
                + "}\n"
            )


class SubFile(Section):
    """This class implements a container to create SubFiles (thats a Latex package)"""

    def __init__(self, numbering=None, label=False, master=None, **kwargs):
        self.master = master
        if self.master is None:
            self.master = "documentation.tex"
        super().__init__(
            "dummy", numbering=None, label=label
        )  # dont need a title for a few tex commands

    def dumps(self):
        string = self.dumps_content()
        # now we add what is needed for subfiles
        string = (
            "\\documentclass["
            + self.master
            + "]{subfiles}\n"
            + "\\begin{document}\n"
            + string
            + "\n \\end{document} \n"
        )
        return string

    def generate_pdf(self, full_path_to_file, compiler=None):
        self.generate_tex(str(full_path_to_file))
        build_tex(full_path_to_file, additional_compiler=compiler)


class CommandRefRange(CommandBase):
    """This command can be used to reference multiple things like figures."""

    _latex_name = "crefrange"
    _default_escape = False
    packages = [Package("hyperref"), Package("cleveref")]


class CommandRef(CommandBase):
    """This command can be used to reference multiple things like figures."""

    _latex_name = "cref"
    _default_escape = False
    packages = [Package("hyperref"), Package("cleveref")]


class CommandInput(CommandBase):
    """This command can be used to input matplotlib2tikz .tex files."""

    _latex_name = "input"
    _default_escape = False
    packages = [
        Package("siunitx"),
        Package("tikz"),
        Package("fontspec"),
        Package("pgfplots"),
        Package("inputenc", options="utf8"),
    ]


class CommandLabel(CommandBase):
    """This command can be used to input matplotlib2tikz .tex files."""

    _latex_name = "label"
    _default_escape = False
    packages = []
