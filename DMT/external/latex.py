""" DMT supplied build latex command
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
import subprocess
import re
from pathlib import Path

from DMT.external.os import cd


def build_tex(full_path_to_file, additional_compiler=None, wait=False, extension=None):
    r"""Builds a tex file

    Parameters
    ----------
    full_path_to_file : str or os.Pathlike
    additional_compiler: (str , [str])
        If a additional tex compiler should be used, supply it here. It will be tried as first compiler.
        The additional compiler must be given in this argument with (<call_of_compiler>, List of compiler arguments).
        For example 'latexmk' looks like: ('latexmk', ['--interaction=nonstopmode', '--shell-escape', '--pdf'])
    wait : Boolean, False
        Wait for the build to complete.
    extension : None, optional
        If None, assumed extension of Tex file to build is "tex", else the given string is used. Example: extension="tikz"
    """
    if not isinstance(full_path_to_file, Path):
        full_path_to_file = Path(full_path_to_file)

    ext = ".tex"
    if extension is not None:
        ext = "." + extension.replace(".", "")

    directory = full_path_to_file.parent
    file_name = full_path_to_file.name
    if file_name.endswith(ext):
        file_name = [file_name]
    else:
        file_name = [file_name + ext]

    compilers = (
        ("latexmk", ["--interaction=nonstopmode", "--shell-escape", "--pdf"]),
        ("lualatex", ["--interaction=nonstopmode", "--shell-escape"]),
        ("pdflatex", ["--interaction=nonstopmode", "--shell-escape"]),
    )
    if additional_compiler is not None and additional_compiler[0] is not None:
        compilers = (additional_compiler,) + compilers

    # turn of testing of all compilers. Just use the first one
    compiler = compilers[0]
    command = [compiler[0]] + compiler[1] + file_name

    with cd(directory):
        try:
            if wait:
                # output = subprocess.call(command, stderr=subprocess.STDOUT)
                subprocess.call(command, stderr=subprocess.STDOUT)
            else:
                # output = subprocess.Popen(command, stderr=subprocess.STDOUT)
                subprocess.Popen(command, stderr=subprocess.STDOUT)
        except FileNotFoundError as err:
            print(err)

            # Notify user that the compiler is not found.
            print(
                "The used latex compiler was not found\n"
                + "The latex command was "
                + " ".join(command)
                + "\n"
                + "Make sure that a LaTeX distribution (like Tex Live) is installed and in your PATH."
            )
        except subprocess.CalledProcessError as err:
            # For all other errors print the output and raise the error
            print(err)
            raise
        else:
            print("LaTeX compile successfull")

        # Compilation has finished


def build_png(full_path_to_file, wait=True):
    r"""Builds a tex file to png graphic.

    Parameters
    ----------
    full_path_to_file : str or os.Pathlike

    TODO
    ----
    somehow this does not work so nice...
    """
    if not isinstance(full_path_to_file, Path):
        full_path_to_file = Path(full_path_to_file)
    directory = full_path_to_file.parent
    file_name = full_path_to_file.name.replace(".tex", "")

    with cd(directory):
        # call latex to compile dvi
        command = ["latex", "--interaction=nonstopmode", file_name + ".tex"]
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except (OSError, IOError, subprocess.CalledProcessError) as e:
            # For all these errors print the output and raise the error
            print(e.output.decode())
            # raise
        else:
            print(output.decode())

        # call dvisvgm to compile dvi to svg
        command = ["pdftoppm", file_name + ".pdf", "outpuname", "-png", file_name + ".png"]
        # pdftoppm input.pdf outputname -png
        # command = ['convert ', file_name+'.dvi','-quality 90', file_name+'.png']
        # convert -density 300 F_TJ_C.pdf -quality 90 F_TJ_C.png
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except (OSError, IOError, subprocess.CalledProcessError) as e:
            # For all these errors print the output and raise the error
            print(e.output.decode())
            # raise
        else:
            print(output.decode())


def build_svg(full_path_to_file, wait=True):
    r"""Builds a tex file to scalable vector graphic.

    Parameters
    ----------
    full_path_to_file : str or os.Pathlike
    """
    if not isinstance(full_path_to_file, Path):
        full_path_to_file = Path(full_path_to_file)
    directory = full_path_to_file.parent
    file_name = full_path_to_file.name.replace(".tex", "")

    with cd(directory):
        # call latex to compile dvi
        command = ["latex", "--interaction=nonstopmode", file_name + ".tex"]
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except (OSError, IOError, subprocess.CalledProcessError) as e:
            # For all these errors print the output and raise the error
            print(e.output.decode())
            # raise
        else:
            print(output.decode())

        # call dvisvgm to compile dvi to svg
        command = ["dvisvgm", "--no-fonts", file_name]
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        except (OSError, IOError, subprocess.CalledProcessError) as e:
            # For all these errors print the output and raise the error
            print(e.output.decode())
            # raise
        else:
            print(output.decode())


def clean_tex_files(directory, file_name, keep=(".tex", ".pdf"), regex=False):
    """Deletes all intermediate files in the directory with name file_name except the tex and pdf.

    Parameters
    ----------
    directory : str
        Direcory to clean
    file_name : str
        File name without file ending (!) to clean
    keep : iterable, optional
        File endings to keep
    """

    def test_str(file_name_to_del, test_file_name):
        return file_name_to_del in test_file_name.stem

    def test_regex(regex_pattern_to_del, test_file_name):
        return bool(re.search(regex_pattern_to_del, test_file_name.stem))

    if regex:
        test_fct = test_regex
    else:
        test_fct = test_str

    for file_curr in Path(directory).iterdir():
        if test_fct(file_name, file_curr) and (file_curr.suffix not in keep):
            file_curr.unlink()


SI_UNITS_CONVERTER = {
    r"\second": "s",
    r"\hertz": "Hz",
    r"\volt": "V",
    r"\watt": "W",
    r"\ampere": "A",
    r"\kelvin": "K",
    r"\ohm": "Ohm",
    r"\siemens": "S",
    r"\farad": "F",
    r"\coulomb": "C",
    r"\electronvolt": "eV",
    r"\meter": "m",
    r"\metre": "m",
    r"\per": "inv",
    r"\square": "sq",
    r"\cubic": "cu",
    r"\giga": "G",
    r"\centi": "c",
    r"\milli": "m",
    r"\micro": "u",
    r"\nano": "n",
    r"\femto": "f",
    r"\pico": "p",
}


def resolve_siunitx(label):
    """This function tries to remove siunitx expressions from given Tex expression."""
    regex_si = r"\\si({.*?})"
    regex_SI = r"\\SI({.*?})({.*?})"
    if "si" in label:
        pattern = re.compile(regex_si)
        for match in pattern.findall(label):
            units = match[1:-1]
            # todo: resolve unit after unit, then for each unit the scaler (milli and so on), than stuff like per. Only then per can be correctly replaced.
            for key in SI_UNITS_CONVERTER:
                units = units.replace(key, SI_UNITS_CONVERTER[key])

            label = label.replace(match, units)

    if "SI" in label:
        pattern = re.compile(regex_SI)
        for match_number, match_unit in pattern.findall(label):
            # match 0 is number
            number = match_number[1:-1]
            label = label.replace(match_number, number)

            # match 1 is unit
            units = match_unit[1:-1]
            for key in SI_UNITS_CONVERTER:
                units = units.replace(key, SI_UNITS_CONVERTER[key])

            label = label.replace(match_unit, units)

    if "underline" in label:
        regex_underline = r"(\\underline{)([^{}]+)(})"
        pattern = re.compile(regex_underline)
        for match in pattern.findall(label):
            label = label.replace(match[0], "")
            label = label.replace(match[1] + match[2], match[1])

    # drop some tex things that are not understood by pandoc
    label = label.replace("\\si", "")
    label = label.replace("\\SI", "")
    label = label.replace("\\,", " ")

    return label


def tex_to_text(tex):
    """Return a text representation of a tex label."""
    tex = resolve_siunitx(tex)
    tex = tex.replace("\\num", "")
    tex = tex.replace("\\mathrm", "")
    tex = tex.replace("\\left(", "(")
    tex = tex.replace("\\right)", ")")
    tex = tex.replace("{", "")
    tex = tex.replace("}", "")
    tex = tex.replace("$", "")
    return tex
