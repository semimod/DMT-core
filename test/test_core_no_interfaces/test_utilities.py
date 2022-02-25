""" Testing the DMT core utilities
"""
from DMT.core import (
    check_nan_inf,
    vectorize,
    memoize,
    flatten,
    enumerate_reversed,
    strictly_increasing,
    resolve_siunitx,
    tex_to_text,
)
from DMT.core import McParameter, McParameterCollection
from DMT.exceptions import NanInfError
import numpy as np
import pytest


def test_nan_inf_decorator():
    @check_nan_inf
    def dummy_function(x, y):
        if x == 0.0:
            return np.asarray(np.nan)
        else:
            return x + y

    with pytest.raises(NanInfError):
        dummy_function(0.0, 1.0)

    assert dummy_function(1.0, 1.0) == 2.0


def test_vectorize_decorator():
    @vectorize
    def dummy_function(x, y, *_args, z=None, **_kwargs):
        return x + y + z

    assert dummy_function(1.0, 1.0, z=1.0) == 3.0

    assert all(dummy_function([1.0, 1.0, 1.0], 1.0, z=1.0) == [3.0, 3.0, 3.0])
    assert all(dummy_function([1.0, 1.0, 1.0], [1.0, 2.0, 3.0], z=1.0) == [3.0, 4.0, 5.0])
    assert all(
        dummy_function([1.0, 1.0, 1.0], [1.0, 2.0, 3.0], z=[1.0, 2.0, 3.0]) == [3.0, 5.0, 7.0]
    )

    with pytest.raises(IOError):
        _a = dummy_function(
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,  # 40 args
            z=np.zeros(1),
        )

    res = dummy_function(
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,  # 20 args
        z=np.zeros(1),
        a00=0.0,
        a01=0.0,
        a02=0.0,
        a03=0.0,
        a04=0.0,
        a05=0.0,
        a06=0.0,
        a07=0.0,
        a08=0.0,
        a09=0.0,
        a10=0.0,
        a11=0.0,
        a12=0.0,
        a13=0.0,
        a14=0.0,
        a15=0.0,
        a16=0.0,
        a17=0.0,
        a18=0.0,
        a19=0.0,  # 20 kwargs -> are cut off ?!?!
    )
    assert res == 0.0


def test_memoize_decorator():
    @memoize
    def dummy_function(x, y):
        return x + y

    assert dummy_function(1, 1) == 2
    assert dummy_function(1, 1) == 2  # second time is only loaded from cache


def test_memoize_decorator_mc():
    @memoize
    def dummy_function_mc(x, y, mcard):
        return x + y + mcard["a"].value

    mc = McParameterCollection()
    mc.add(McParameter("a", value=5.0))

    assert dummy_function_mc(1, 1, mc) == 7
    assert dummy_function_mc(1, 1, mc) == 7  # second time is only loaded from cache


def test_strictly_increasing():
    assert strictly_increasing(np.array([0.0, 1.0, 2.0, 3.0]))
    assert not strictly_increasing(np.array([0.0, 2.0, 1.0, 3.0]))
    assert not strictly_increasing(np.array([0.0, 1.0, 1.0, 3.0]))


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


def test_flatten():
    assert (0, 1, 2, 3) == tuple(flatten((0, (1, 2), 3)))
    assert (0, 1, 2, 3) == tuple(
        flatten(
            (
                0,
                (
                    1,
                    (
                        2,
                        3,
                    ),
                ),
            )
        )
    )


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
    test_nan_inf_decorator()
    test_vectorize_decorator()
    test_memoize_decorator()
    test_memoize_decorator_mc()
    test_strictly_increasing()
    test_flatten()
    test_enumerate_reversed()
    test_resolve_siunitx()
    test_tex_to_text()
