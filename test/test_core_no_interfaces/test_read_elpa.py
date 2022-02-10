import sys
import numpy as np
from DMT.core import read_elpa, read_DEVICE_bin
import os
import time


def test_read_elpa():
    start_time = time.time()
    _device_elpa = read_elpa(os.path.join("test", "test_core_no_interfaces", "HBT_vbc.elpa"))
    end_time = time.time()
    print("read_elpa took ", end_time - start_time, " seconds")


def test_read_DEVICE_internal():
    start_time = time.time()
    _df_internal = read_DEVICE_bin(
        os.path.join("test", "test_core_no_interfaces", "test_data", "idc1")
    )
    end_time = time.time()
    print("read_DEVICE_bin took ", end_time - start_time, " seconds")


if __name__ == "__main__":
    test_read_elpa()
    test_read_DEVICE_internal()
    dummy = 1
