from DMT.core import read_data
import os


def test_read_mdm():
    df = read_data(os.path.join("test", "test_core_no_interfaces", "test_data", "short_freq.mdm"))
    df = read_data(os.path.join("test", "test_core_no_interfaces", "test_data", "short_dc.mdm"))


if __name__ == "__main__":
    test_read_mdm()
    dummy = 1
