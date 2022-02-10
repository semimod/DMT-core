# DMT_core
# Copyright (C) from 2020  SemiMod
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
import sys
import numpy as np
import re
import inspect
from functools import wraps
from DMT.exceptions import NanInfError
from DMT.core.mc_parameter import McParameterComposition


def print_progress_bar(
    current=0,
    total=100,
    prefix="progress",
    suffix="completed",
    length=100,
    space=" ",
    fill="█",
    show_balance=False,
    completed=False,
):
    """Displays a progress bar in the terminal."""
    current = 100 if completed else current
    percentage = int((current * 100) / total)
    progress = int((percentage * length) / 100)
    bar = space * int(length - progress)
    progress = fill * progress

    balance = " ({}/{})".format(current, total) if show_balance else ""
    skip = "\n" if percentage == 100 else ""

    sys.stdout.write(
        "\r{} : |{}{}| {}%{} {}{}".format(prefix, progress, bar, percentage, balance, suffix, skip)
    )
    sys.stdout.flush()


def check_nan_inf(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        func_return = func(*args, **kwargs)
        if np.isnan(func_return).any() or np.isinf(func_return).any():
            message = "Method {} returned NaN or Inf".format(func.__name__)
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()
            message = message + r"\n" + str(dict(bound_args.arguments))
            raise NanInfError(message)

        else:
            return func_return

    return func_wrapper


def vectorize(func):
    """Slows everything down heavily!!"""

    @wraps(func)
    def vectorize_wrapper(*args, **kwargs):
        n_args = len(args)
        n_kwargs = len(kwargs)
        if n_args > 32:
            raise IOError("DMT -> vectorize: Can only vectorize up to 32 args.")

        elif (n_args + n_kwargs) > 32:
            delta = 32 - n_args  # exclude last delta kwargs
            func_vectorized = np.vectorize(func, excluded=list(kwargs.keys())[delta - 1 :])

        else:
            func_vectorized = np.vectorize(func)

        return func_vectorized(*args, **kwargs)

    return vectorize_wrapper


def memoize(obj):
    r"""Decorator that implements memoization for McParameter objects in \*args."""
    cache = obj.cache = {}

    @wraps(obj)
    def memoizer(*args, **kwargs):
        # find mcards
        mcard = None
        args_cache = None
        for i_arg, arg in enumerate(args):
            if isinstance(arg, McParameterComposition):
                mcard = arg
                args_cache = tuple(
                    [arg_a for i_arg_a, arg_a in enumerate(args) if i_arg_a != i_arg]
                )
                break

        if mcard is None:
            key = str(args) + str(kwargs)
        else:
            key = (
                str(args_cache) + str(kwargs) + mcard.print_parameters()
            )  # hashing would be better

        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]

    return memoizer


def is_iterable(arg):
    """Returns True if the object is iterable

    Source: https://stackoverflow.com/a/36407550/13212532

    """
    try:
        _test = (e for e in arg)
        return True
    except TypeError:
        return False


def flatten(items):
    """Yield items from any nested iterable; see Reference https://stackoverflow.com/a/40857703."""
    for x in items:
        if not isinstance(x, (str, bytes)) and is_iterable(x):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


def strictly_increasing(L):
    """checks if given iterable is strictly increasing or not"""
    return all(x < y for x, y in zip(L, L[1:]))


def enumerate_reversed(iterable, start=0, stop=None, step=1):
    """Generator to go through an iterable from back to front with correct indexes without copy of the iterable.

    Source:
        `Stack Overflow <https://stackoverflow.com/a/52195368>`_

    Parameters
    ----------
    iterable : Iterable[_T]
    start, stop, step : int, optional
        Starting and ending index with step size for the iterable

    Returns
    -------
    index, value for each element in the iterable.
        index always refers to the true index of the iterable, independent of start or stop!
    """
    if stop is None:
        stop = len(iterable)

    for index, value in enumerate(reversed(iterable[start:stop:step])):
        index = stop - 1 - index
        yield index, value


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
