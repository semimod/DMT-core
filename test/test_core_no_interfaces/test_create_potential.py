from numpy import array
import pytest
from DMT.core import DataFrame, specifiers

specifier_vbe = specifiers.VOLTAGE + "B" + "E"
specifier_vce = specifiers.VOLTAGE + "C" + "E"
specifier_vbc = specifiers.VOLTAGE + "B" + "C"
potential_b = specifiers.VOLTAGE + "B"
potential_c = specifiers.VOLTAGE + "C"
potential_e = specifiers.VOLTAGE + "E"


def test_2_voltages_0_potential_and_reference():
    df = DataFrame.from_dict({specifier_vbe: [0.5], specifier_vce: [1]})
    df.ensure_specifier_column(potential_b, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_c, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_e, debug=True, reference_node="E")
    vb = df[potential_b].to_numpy()
    vc = df[potential_c].to_numpy()
    ve = df[potential_e].to_numpy()
    assert vb == array([0.5])
    assert vc == array([1])
    assert ve == array([0])


def test_2_voltages_0_potential_and_reference_b_common1():
    df = DataFrame.from_dict({specifier_vbe: [0.5], specifier_vbc: [-0.5]})
    df.ensure_specifier_column(potential_b, debug=True, reference_node="B")
    df.ensure_specifier_column(potential_c, debug=True, reference_node="B")
    df.ensure_specifier_column(potential_e, debug=True, reference_node="B")
    vb = df[potential_b].to_numpy()
    vc = df[potential_c].to_numpy()
    ve = df[potential_e].to_numpy()
    assert vb == array([0])
    assert vc == array([0.5])
    assert ve == array([-0.5])


def test_2_voltages_0_potential_and_reference_b_common2():
    df = DataFrame.from_dict({specifier_vbe: [0.5], specifier_vbc: [-0.5]})
    df.ensure_specifier_column(potential_e, debug=True, reference_node="B")
    df.ensure_specifier_column(potential_c, debug=True, reference_node="B")
    df.ensure_specifier_column(potential_b, debug=True, reference_node="B")
    vb = df[potential_b].to_numpy()
    vc = df[potential_c].to_numpy()
    ve = df[potential_e].to_numpy()
    assert vb == array([0])
    assert vc == array([0.5])
    assert ve == array([-0.5])


def test_2_voltages_0_potential_and_reference_b_common3():
    df = DataFrame.from_dict({specifier_vbe: [0.5], specifier_vce: [-0.5]})
    df.ensure_specifier_column(potential_e, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_c, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_b, debug=True, reference_node="E")
    vb = df[potential_b].to_numpy()
    vc = df[potential_c].to_numpy()
    ve = df[potential_e].to_numpy()
    assert vb == array([0.5])
    assert vc == array([-0.5])
    assert ve == array([0])


def test_2_voltage_1_potential_and_reference():
    ## this should work
    df = DataFrame.from_dict({specifier_vbe: [-0.5], specifier_vbc: [0.5], potential_c: [0]})
    df.ensure_specifier_column(potential_b, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_c, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_e, debug=True, reference_node="E")
    assert df[potential_e].to_numpy() == array([0])
    assert df[potential_b].to_numpy() == array([-0.5])
    assert df[potential_c].to_numpy() == array([-1.0])


def test_1_voltage_1_potential_and_reference():
    ## this should work
    df = DataFrame.from_dict({specifier_vbe: [0.5], potential_c: [1]})
    df.ensure_specifier_column(potential_c, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_e, debug=True, reference_node="E")
    df.ensure_specifier_column(potential_b, debug=True, reference_node="E")
    assert df[potential_b].to_numpy() == array([0.5])
    assert df[potential_e].to_numpy() == array([0])
    assert df[potential_c].to_numpy() == array([1])

    # this not
    df = DataFrame.from_dict({specifier_vbe: [0.5], potential_c: [1]})
    with pytest.raises(KeyError):
        df.ensure_specifier_column(potential_b, debug=True)

    with pytest.raises(KeyError):
        df.ensure_specifier_column(potential_b, debug=True, reference_node="C")


if __name__ == "__main__":
    test_2_voltages_0_potential_and_reference()
    test_1_voltage_1_potential_and_reference()
    test_2_voltage_1_potential_and_reference()
    test_2_voltages_0_potential_and_reference_b_common1()
    test_2_voltages_0_potential_and_reference_b_common2()
    test_2_voltages_0_potential_and_reference_b_common3()
