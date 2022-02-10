import numpy as np
from DMT.core import DataFrame, specifiers

COL_VB = specifiers.VOLTAGE + "B"
COL_VC = specifiers.VOLTAGE + "C"
COL_VE = specifiers.VOLTAGE + "E"
COL_VBE = specifiers.VOLTAGE + ["B", "E"]
COL_VBC = specifiers.VOLTAGE + ["B", "C"]


def test_unique_iterator():
    df = DataFrame.from_dict(
        {COL_VB: np.linspace(0, 1, num=5), COL_VC: np.ones(5), COL_VE: np.zeros(5)}
    )
    df.ensure_specifier_column(COL_VBC)

    for index, vbc, data in df.iter_unique_col(COL_VBC):
        assert np.isclose(vbc, np.linspace(-1, 0, num=5)[index])


if __name__ == "__main__":
    test_unique_iterator()
