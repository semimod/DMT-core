""" Testing the core module mc_parameter
"""
import os
import shutil
import copy
import tempfile
import pytest
import numpy as np
from pathlib import Path
from DMT.core import unit_registry, McParameter, McParameterCollection
from DMT.exceptions import (
    BoundsError,
    ValueTooLargeError,
    ValueExcludedError,
    ParaExistsError,
)
from DMT.external import Tex

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent


def test_mc_parameter():
    """Testing single parameters"""
    with pytest.raises(IOError):
        param_1 = McParameter(5)

    param_without_bounds = McParameter("a", value=1, minval=None, maxval=None)
    param_with_bounds = McParameter("a", value=1, minval=0, maxval=10)
    param_excl_bounds = McParameter("a", value=1, minval=0, maxval=10)
    param_excl_bounds.inc_max = False
    param_excl_bounds.inc_min = False

    # value type
    param_with_bounds.val_type = int
    with pytest.raises(IOError):
        param_with_bounds.val_type = str
    param_with_bounds.val_type = float

    # setting the minimum
    with pytest.raises(BoundsError):
        param_with_bounds.min = 12
    with pytest.raises(BoundsError):
        param_with_bounds.min = 2

    param_with_bounds.min = 1
    param_with_bounds.min = 0
    with pytest.raises(BoundsError):
        param_excl_bounds.min = 1
    with pytest.raises(BoundsError):
        param_excl_bounds.min = 2

    # setting the maximum
    with pytest.raises(BoundsError):
        param_with_bounds.max = -1
    with pytest.raises(BoundsError):
        param_with_bounds.max = 0.5

    param_with_bounds.max = 1
    param_with_bounds.max = 10
    with pytest.raises(BoundsError):
        param_excl_bounds.max = 1
    with pytest.raises(BoundsError):
        param_excl_bounds.max = 0.5

    # value setting using another mc_parameter
    param_with_bounds.value = param_excl_bounds

    # force set
    param_with_bounds = McParameter("a", value=1, minval=0, maxval=10)
    param_with_bounds._set_forced(1.5)
    assert np.isclose(param_with_bounds.value, 1.5)
    assert np.isclose(param_with_bounds.min, 0)
    assert np.isclose(param_with_bounds.max, 10)

    # forcing a not allow value changes bounds to inf
    param_with_bounds._set_forced(-1.5)
    assert np.isclose(param_with_bounds.value, -1.5)
    assert np.isclose(param_with_bounds.min, -np.inf)
    assert np.isclose(param_with_bounds.max, np.inf)

    param_4 = McParameter("a", value=1, minval=0, maxval=10)

    with pytest.raises(TypeError):
        param_4._set_forced(np.array([-1.5]))

    with pytest.raises(IOError):
        param_4 = McParameter("a", value=1, minval=0, maxval=10)
        param_4._value = -1  # hack
        param_with_bounds._set_forced(param_4)  # forbid to pass on

    # start over and check_bounds
    param_with_bounds = McParameter("a", value=1, minval=0, maxval=10)
    assert param_with_bounds != 1
    assert param_with_bounds != 5

    param_with_bounds.check_bounds(2)
    with pytest.raises(TypeError):
        param_with_bounds.check_bounds(np.array([2]))

    with pytest.raises(TypeError):
        param_with_bounds.check_bounds("test")

    with pytest.raises(ValueTooLargeError):
        param_excl_bounds.check_bounds(10)
    with pytest.raises(ValueTooLargeError):
        param_excl_bounds.check_bounds(11)

    param_excl_bounds.exclude = [3]
    with pytest.raises(ValueExcludedError):
        param_excl_bounds.check_bounds(3)

    # formatting and printing:
    param_format = McParameter("a", value=1, minval=0, maxval=10)
    with pytest.raises(IOError):
        "{:h}".format(param_format)

    assert "{:.1f}".format(param_format) == "1.0"
    assert "{:s}".format(param_format) == "a"
    assert "{:u}".format(param_format) == "-"

    ur = unit_registry
    param_format.unit = ur.ampere
    assert "{:u}".format(param_format) == "\\ampere"
    param_format.unit = ur.dimensionless
    assert "{:u}".format(param_format) == "-"  # same as unit == None

    # None should not be allowed for a float!
    # param_format._value = None # if a parameter is initialized without a value..
    # assert  '{:d}'.format(param_format) == '-'

    # testing iteration: -> should not work
    param_1 = McParameter("a", value=1, minval=0, maxval=10)

    with pytest.raises(TypeError):
        for para in param_1:
            para.value = 1

    # adding two parameter should give an error -> add names or values or append to a composition -> we do not know!
    param_1 = McParameter("a", value=1, minval=0, maxval=10)
    param_2 = McParameter("b", value=1, minval=0, maxval=10)

    with pytest.raises(TypeError):
        _comp = param_1 + param_2


def test_mc_parameter_collection():
    """here compositions are tested!"""
    # create:
    mc_comp = McParameterCollection()

    # add
    mc_comp.add(McParameter("a", value=1, minval=0, maxval=10))

    with pytest.raises(TypeError):
        mc_comp.add("a")

    # add another with same name
    with pytest.raises(ParaExistsError):
        mc_comp.add(McParameter("a", value=2, minval=0, maxval=10))

    with pytest.raises(TypeError):
        _test = mc_comp + 5
    with pytest.raises(TypeError):
        _test = "a" + mc_comp + 5

    # add parameter using magic
    mc_comp = mc_comp + McParameter("b", value=2, minval=0, maxval=10)
    # reversed also possible
    mc_comp = McParameter("c", value=2, minval=0, maxval=10) + mc_comp
    # inplace
    mc_comp += McParameter("d", value=2, minval=0, maxval=10)

    assert len(mc_comp) == 4
    assert mc_comp.name != ["a", "b", "c", "d"]  # all were added in the given order
    assert mc_comp.name == ["c", "a", "b", "d"]  # beware the 'c'

    # to iter them in alphabetical order (needed for hashable netlists):
    for para, name in zip(mc_comp.iter_alphabetical(), ["a", "b", "c", "d"]):
        assert para.name == name

    # adding 2 compositions:
    mc_comp_2 = McParameterCollection()
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10))
    mc_comp_2.add(McParameter("y", value=1, minval=0, maxval=10))
    mc_comp_2.add(McParameter("z", value=1, minval=0, maxval=10))

    assert len(mc_comp + mc_comp_2) == 7
    assert len(mc_comp_2 + mc_comp) == 7
    # order: !
    assert (mc_comp + mc_comp_2).name == ["c", "a", "b", "d", "x", "y", "z"]
    assert (mc_comp_2 + mc_comp).name == ["x", "y", "z", "c", "a", "b", "d"]

    # without magic
    mc_comp.add(mc_comp_2)
    assert len(mc_comp) == 7
    assert mc_comp.name == ["c", "a", "b", "d", "x", "y", "z"]

    mc_comp.remove(mc_comp_2)
    mc_comp.add(mc_comp_2, index=0)
    assert mc_comp.name == ["x", "y", "z", "c", "a", "b", "d"]

    # testing equal:
    # this could also raise an TypeError, but keeping the door open for more magic
    assert mc_comp != "x"
    assert mc_comp != McParameter("x", value=1, minval=0, maxval=10)

    assert mc_comp != mc_comp_2
    assert mc_comp_2 != mc_comp
    mc_comp_copy = copy.deepcopy(mc_comp)
    assert mc_comp == mc_comp_copy

    # setting a new value
    mc_comp.set(McParameter("a", value=3))
    assert mc_comp != mc_comp_copy  # compositions are equal if all parameters and names are equal

    mc_comp.set(mc_comp_copy)  # setting a complete composition is also usefull

    mc_comp["b"] = 10

    with pytest.raises(ValueTooLargeError):
        mc_comp["b"] = 11

    assert mc_comp.get("b").value == 10

    with pytest.raises(KeyError):
        mc_comp.set(McParameter("k", value=3))

    # using the convinience function:
    mc_comp.set_values({"b": 9})
    assert mc_comp.get("b").value == 9

    with pytest.raises(ValueTooLargeError):
        mc_comp.set_values({"b": 11})

    mc_comp.set_values({"b": 11}, force=True)  # can be forced easily :)

    with pytest.raises(KeyError):
        mc_comp.set_values({"g": 11})

    with pytest.raises(KeyError):
        mc_comp.set_values({"g": 11}, force=True)  # force creation of a parameter is removed...

    assert np.isclose(mc_comp["b"].value, 11)
    assert np.isclose(mc_comp["b"].min, -np.inf)
    assert np.isclose(mc_comp["b"].max, np.inf)

    # getting a parameter
    assert mc_comp.get("a").value == 1
    assert mc_comp["a"].value == 1

    assert mc_comp.get_values({"a"})["a"] == 1
    with pytest.raises(KeyError):
        mc_comp.get_values({"a1"})

    # setting new bounds
    with pytest.raises(KeyError):
        mc_comp.set_bounds({"k": (0, 1)})

    mc_comp.set_bounds({"b": (0, 12)})
    assert np.isclose(mc_comp["b"].min, 0)
    assert np.isclose(mc_comp["b"].max, 12)


def test_mc_parameter_collection_to_kwargs():
    """separate test for to_kwargs as this method is very important!!"""
    mc_comp_2 = McParameterCollection()
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10))
    mc_comp_2.add(McParameter("y", value=1, minval=0, maxval=10))
    mc_comp_2.add(McParameter("z", value=1, minval=0, maxval=10))

    control_dict = {"x": 1, "y": 1, "z": 1}
    assert mc_comp_2.to_kwargs() == control_dict


def test_mc_parameter_collection_file_methods():
    """File in and output"""
    mc_comp_2 = McParameterCollection()
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10))
    mc_comp_2.add(McParameter("y", value=1, minval=0, maxval=10))
    mc_comp_2.add(McParameter("z", value=1, minval=0, maxval=10))

    shutil.rmtree(str(test_path / "tmp" / "test_comp"), ignore_errors=True)
    # save and load

    # print part of composition
    assert (
        mc_comp_2.print_parameters(paras=("x", "y"))
        == "  x            = 1.00000e+00   y            = 1.00000e+00 "
    )

    # print to file:
    mc_comp_2.print_to_file(test_path / "tmp" / "test_comp" / "mc_comp_2", create_dir=True)

    assert (
        test_path / "tmp" / "test_comp" / "mc_comp_2.txt"
    ).read_text() == "  x            = 1.00000e+00   y            = 1.00000e+00   z            = 1.00000e+00 \n"


def test_mc_parameter_collection_properties():
    mc_comp_2 = McParameterCollection()
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10, group="g1"))
    mc_comp_2.add(McParameter("y", value=1, minval=0, maxval=10, group="g1"))
    mc_comp_2.add(McParameter("z", value=1, minval=0, maxval=10, group="g2"))

    assert mc_comp_2.group == {"g1", "g2"}  # group is a set of group names

    # set values
    # length must be correct
    with pytest.raises(IOError):
        mc_comp_2.value = [2, 3]
    with pytest.raises(IOError):
        mc_comp_2.value = [2, 3, 4, 5]

    mc_comp_2.value = [2, 3, 4]
    assert all(mc_comp_2.value == np.array([2, 3, 4]))

    # same for min and max
    with pytest.raises(IOError):
        mc_comp_2.min = [2, 3]
    with pytest.raises(IOError):
        mc_comp_2.min = [2, 3, 4, 5]

    mc_comp_2.min = [0, 1, 2]
    assert all(mc_comp_2.min == np.array([0, 1, 2]))

    with pytest.raises(IOError):
        mc_comp_2.max = [2, 3]
    with pytest.raises(IOError):
        mc_comp_2.max = [2, 3, 4, 5]

    mc_comp_2.max = [7, 8, 9]
    assert all(mc_comp_2.max == np.array([7, 8, 9]))

    # remove function:
    mc_comp_2.remove("x")
    assert "x" not in mc_comp_2.name
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10, group="g1"))
    assert "x" in mc_comp_2.name
    mc_comp_2.remove(McParameter("x", value=1))
    assert "x" not in mc_comp_2.name

    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10, group="g1"))

    with pytest.raises(KeyError):
        mc_comp_2.remove("a")

    mc_comp_2.remove(("x", "y"))
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10, group="g1"))
    mc_comp_2.add(McParameter("y", value=1, minval=0, maxval=10, group="g1"))

    mc_comp_2.remove(mc_comp_2)

    assert len(mc_comp_2) == 0


def test_mc_parameter_collection_to_tex():
    mc_comp_2 = McParameterCollection()
    mc_comp_2.add(McParameter("x", value=1, minval=0, maxval=10, group="g1"))
    mc_comp_2.add(McParameter("y", value=1, minval=0, maxval=10, group="g1"))
    mc_comp_2.add(McParameter("z", value=1, minval=0, maxval=10, group="g2"))
    mc_comp_2.sort_paras()

    tex = mc_comp_2.print_tex()

    assert isinstance(tex, Tex)

    fp = tempfile.NamedTemporaryFile(mode="w", suffix=".tex", delete=False)  # generate a temp file
    file_name = fp.name
    fp.close()  # it is not deleted

    tex.generate_tex(file_name.replace(".tex", ""))
    with open(file_name, "r") as fp:
        fp.seek(0)
        tex_content = fp.read()

    os.unlink(file_name)  # delete manually -> this needs to be done bc of windows...

    assert "x" in tex_content
    assert "y" in tex_content
    assert "z" in tex_content


def test_json():
    mc_1 = McParameter(
        "x",
        value=1,
        minval=0,
        maxval=None,
        inc_min=True,
        inc_max=False,
        exclude=2,
        group="g1",
        unit=unit_registry.ampere,
        description="asdf",
    )

    target_dict = {
        "name": "x",
        "value": 1.0,
        "min": 0.0,
        "max": np.inf,
        "inc_min": True,
        "inc_max": False,
        "exclude": [2],
        "type": "float",
        "unit": str(unit_registry.ampere),
        "group": "g1",
        "description": "asdf",
        "__McParameter__": "1.0.0",
    }
    assert mc_1.dict_json() == target_dict

    mc_loaded = McParameter.load_json(**target_dict)
    for param in dir(mc_1):
        if not callable(getattr(mc_1, param)) and not param.startswith("__"):
            assert getattr(mc_1, param) == getattr(mc_loaded, param)

    mc_comp = McParameterCollection()
    mc_comp.add(McParameter("x", value=1, minval=0, maxval=10, group="g1"))
    mc_comp.add(McParameter("y", value=1, minval=0, maxval=10, group="g1"))
    mc_comp.add(McParameter("z", value=1, minval=0, maxval=10, group="g2"))

    file_name = "test_json_composition.json"
    mc_comp.dump_json(file_name)
    mc_comp_read = McParameterCollection.load_json(file_name)

    os.remove(file_name)

    assert mc_comp == mc_comp_read


if __name__ == "__main__":
    test_mc_parameter()
    test_mc_parameter_collection()
    test_mc_parameter_collection_to_kwargs()
    test_mc_parameter_collection_file_methods()
    test_mc_parameter_collection_properties()
    test_mc_parameter_collection_to_tex()
    test_json()
