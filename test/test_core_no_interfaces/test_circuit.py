""" Testing Circuit and CircuitElement class.
"""
from DMT.core.mcard import MCard
import pytest
from DMT.core import Circuit, CircuitElement
from DMT.core.circuit import RESISTANCE, CAPACITANCE, INDUCTANCE, CURRENT, VOLTAGE, SHORT


def test_CircuitElement():
    # correct way
    ce_r = CircuitElement(
        RESISTANCE,
        "R_1",
        ("A", "B"),
        parameters=[
            ("R", "10"),
        ],
    )

    assert str(ce_r) == "DMT.CircuitElement:R_1 model R nodes A,B"

    # wrong, type must be a string
    with pytest.raises(TypeError):
        CircuitElement(
            5,
            "R_1",
            ("A", "B"),
            parameters=[
                ("R", "10"),
            ],
        )
    # wrong, 'a' is unknown
    with pytest.raises(IOError):
        CircuitElement(
            "a",
            "R_1",
            ("A", "B"),
            parameters=[
                ("R", "10"),
            ],
        )
    # wrong, name must be a string
    with pytest.raises(TypeError):
        CircuitElement(
            CAPACITANCE,
            5,
            ("A", "B"),
            parameters=[
                ("C", "10"),
            ],
        )

    # wrong, nodes must be a tuple
    with pytest.raises(TypeError):
        CircuitElement(
            INDUCTANCE,
            "R_1",
            "A B",
            parameters=[
                ("R", "10"),
            ],
        )
    # wrong, nodes must be tuple of strings
    with pytest.raises(TypeError):
        CircuitElement(
            CURRENT,
            "R_1",
            ("A", 5),
            parameters=[
                ("R", "10"),
            ],
        )

    # wrong, parameters must be list
    with pytest.raises(TypeError):
        CircuitElement(VOLTAGE, "R_1", ("A", "B"), parameters="R=10")
    # wrong, parameters must be list of tuples
    with pytest.raises(TypeError):
        CircuitElement(RESISTANCE, "R_1", ("A", "B"), parameters=["R=10"])
    # wrong, parameters must be list of tuples of strings
    with pytest.raises(TypeError):
        CircuitElement(RESISTANCE, "R_1", ("A", "B"), parameters=[("R", 10)])

    # correct way
    CircuitElement(SHORT, "I_S", ("A", "B"))


def test_CircuitElement_MCard():
    # mcards
    mcard = MCard(["A", "D"], default_subckt_name="dio", default_module_name="diova")

    element = CircuitElement(
        mcard.default_module_name, mcard.default_subckt_name, ["n_A", "n_D"], parameters=mcard
    )

    assert element.parameters == mcard


def test_circuit():
    # correct
    Circuit(
        [
            CircuitElement(
                RESISTANCE,
                "R_1",
                ("A", "B"),
                parameters=[
                    ("R", "10"),
                ],
            ),
            CircuitElement(SHORT, "I_S", ("A", "B")),
            "V_A=0",
        ]
    )
    # wrong
    with pytest.raises(TypeError):
        Circuit(
            [
                CircuitElement(
                    RESISTANCE,
                    "R_1",
                    ("A", "B"),
                    parameters=[
                        ("R", "10"),
                    ],
                ),
                CircuitElement(SHORT, "I_S", ("A", "B")),
                "V_A=0",
                5,
            ]
        )

    # outdated and now forbidden
    with pytest.raises(NotImplementedError):
        Circuit("common_emitter")

    # also test the default circuit as this has to be implemented in the subclass
    mcard = MCard(["A", "D"], default_subckt_name="dio", default_module_name="diova")
    with pytest.raises(NotImplementedError):
        mcard.get_circuit()  # should always work...


if __name__ == "__main__":
    test_CircuitElement()
    test_CircuitElement_MCard()
    test_circuit()
