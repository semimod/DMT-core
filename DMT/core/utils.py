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
import sys


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


def enumerate_reversed(iterable, start=0, stop=None, step=1):
    """Generator to go through an iterable from back to front with correct indexes without copy of the iterable.

    Source:
        `Stack Overflow <https://stackoverflow.com/a/52195368>`_

    Parameters
    ----------
    iterable : Iterable[_T]
    start, stop, step : int, optional
        Starting and ending index with step size for the iterable

    Yields
    ------
    index, value
        index always refers to the true index of the iterable, independent of start or stop!
    """
    if stop is None:
        stop = len(iterable)

    for index, value in enumerate(reversed(iterable[start:stop:step])):
        index = stop - 1 - index
        yield index, value
