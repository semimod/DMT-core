"""
This example shows how to read in measurement data in batch mode.
"""
from pathlib import Path
from DMT.core import DutLib, DutMeas, DutType

# path to DMT test cases
path_test = Path(__file__).resolve().parent.parent.parent.parent / "test"


def dut_filter(dut_name):
    """This function is given to the "import_directory" function as an argument. It will be called for all valid folders. If
    it returns a DutMeas object, all data will be read-in and assigned to the DutMeas object..
    """
    if "0p25x10" in dut_name:
        return DutMeas(
            path_test / "tmp",  # here the device is stored when its save() routine is called
            "CBEBC_0p25x10",
            DutType.npn,
            wafer="xy",
            die="z",
            reference_node="E",
        )
    else:
        return None


# the device and its measurement data are in the folder:
#'test/test_core_no_interfaces/test_data/0p25x10/'
#'test/test_core_no_interfaces/test_data/0p25x10/meas_1'
#'test/test_core_no_interfaces/test_data/0p25x10/meas_2'
#'test/test_core_no_interfaces/test_data/0p25x10/...'

# create a library
lib = DutLib()

# read in all data for all devices
# the folders that contain measurement data for one device structure lie one level below the given first argument.
lib.import_directory(path_test / "test_core_no_interfaces" / "test_data", dut_filter, dut_level=1)

# now the data has been read-in, but the data columns are not yet ensured to
# follow the DMT specifiers grammar for electrical variables => important to have consistent data within DMT

# data that should be deleted is given as a dictionary:
# (every measurement folk has his own naming conventions -> standardize them here)
fallback = {
    "S_DEEMB(1,1)": None,
    "S_DEEMB(1,2)": None,
    "S_DEEMB(2,1)": None,
    "S_DEEMB(2,2)": None,
}
for dut in lib:
    # now ensure the data is in DMT format!
    dut.clean_data(fallback=fallback)


# lib.save() can be now be called to store all the data in HDF5 format => memory efficient and fast.
