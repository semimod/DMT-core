from pathlib import Path
from DMT.core import read_data


folder_path = Path(__file__).resolve().parent


def test_read_mdm():
    df = read_data(folder_path / "test_data" / "short_freq.mdm")
    df = read_data(folder_path / "test_data" / "short_dc.mdm")


if __name__ == "__main__":
    test_read_mdm()
    dummy = 1
