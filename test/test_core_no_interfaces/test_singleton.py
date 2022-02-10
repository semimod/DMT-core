import pytest
from DMT.core import SimCon


def test_create_singleton():
    """Creates a sweep and a dummy dut to run using the simulation controller."""
    sim_con = SimCon(n_core=4, t_max=5)

    sim_con.run_and_read(force=True)

    assert sim_con.n_core == 4


def test_create_new_singleton():
    sim_con = SimCon(n_core=4, t_max=5)

    assert sim_con.n_core == 4

    id_old = id(sim_con)

    sim_con = SimCon(
        n_core=5
    )  # instanziation of "new" SimCon with different n_core leads to same object with changed n_core

    assert sim_con.t_max == 5
    assert sim_con.n_core == 5

    assert id(sim_con) == id_old


def test_reinstanziation_errors():
    _sim_con = SimCon(n_core=4, t_max=5)

    with pytest.raises(AttributeError):
        _sim_con = SimCon(5)

    with pytest.raises(AttributeError):
        _sim_con = SimCon(alternative_attr=5)


if __name__ == "__main__":
    test_create_singleton()
    test_create_new_singleton()
    test_reinstanziation_errors()
    dummy = 1
