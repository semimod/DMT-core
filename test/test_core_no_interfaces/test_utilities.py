""" Testing the DMT core utilities
"""
from DMT.core import (
    enumerate_reversed,
    resolve_siunitx,
    tex_to_text,
)
import numpy as np


def test_enumerate_reversed():
    test_list = ["A", "B", "C", "D"]

    old_index = len(test_list)
    for index, value in enumerate_reversed(test_list):
        assert test_list[index] == value  # original index is preserved

        assert index == old_index - 1  # iterating reversed
        old_index = index

    old_index = 2
    for index, value in enumerate_reversed(test_list, stop=2):
        assert test_list[index] == value  # original index is preserved

        assert index == old_index - 1  # iterating reversed
        old_index = index


def test_resolve_siunitx():
    # stay the same if no si is mentioned
    assert resolve_siunitx("pK") == "pK"

    assert resolve_siunitx("\\si{\\pico\\kelvin}") == "pK"
    assert resolve_siunitx("\\si{\\pico\\kelvin}\\,\\si{\\milli\\volt}") == "pK mV"
    assert resolve_siunitx("\\SI{5}{\\pico\\kelvin}") == "5pK"
    assert resolve_siunitx("\\SI{5}{\\pico\\kelvin}\\,\\SI{0.5}{\\milli\\volt}") == "5pK 0.5mV"

    assert (
        resolve_siunitx(
            "\\underline{Y}^{s}_{\\mathrm{21}} = \\SI{1e5}{\\micro\\siemens\\per\\square\\micro\\meter}"
        )
        == "Y^{s}_{\\mathrm{21}} = 1e5uSinvsqum"
    )


def test_tex_to_text():
    assert tex_to_text(r"I_{C}") == r"I_C"
    assert tex_to_text(r"I_{\mathrm{C}}") == r"I_C"
    assert tex_to_text(r"I_{C}") == r"I_C"


if __name__ == "__main__":
    test_enumerate_reversed()
    test_resolve_siunitx()
    test_tex_to_text()
