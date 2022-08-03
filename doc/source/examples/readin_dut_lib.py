""" Reading the skywater130 data into a DMT DutLib

This is a large example how to read in the full skywater130 pdk measurement data into a DMT DutLib. Then the processing can go on in Python as you like. Feel free to use this example as a starting point.

Before you can use this data, you have to check out the measurement data repository from:
https://github.com/google/skywater-pdk-sky130-raw-data

This example is used for the inital data from July 2022

The file structure of the Skywater PDK does not fit to the DMT structure. DMT wants 1 folder per Device, in the raw data there is one folder per device type.
Here its easier to restructure the raw data. We will have a look onto the demand for different structures and how to implement into DutLib.import_directory, for now this is the faster and easier solution.

So, in the first step the raw data is sorted for DMT.

"""
import shutil
import re
import numpy as np
from pathlib import Path
from DMT.core import DutMeas, DutType, DocuDutLib, DutLib, specifiers, sub_specifiers, Plot

path_to_dmt_core = Path(__file__).resolve().parent.parent.parent.parent
path_to_git = path_to_dmt_core.parent.parent / "skywater-pdk-sky130-raw-data-main"
path_to_cells = path_to_git / "sky130_fd_pr" / "cells"

# this is the sorting
for child in path_to_cells.glob("*/" * (2)):
    if (
        child.is_file()
    ):  # only files are allowed since directories are created this does not interfere
        device_name = child.stem[: child.stem.find("_ID")]
        target_folder = child.parent / device_name
        target_folder.mkdir(exist_ok=True)
        shutil.move(child, target_folder / child.name)


# Create a DutLib
lib_save_dir = path_to_dmt_core / "test" / "tmp" / "skywater130_lib"
lib = DutLib(save_dir=lib_save_dir, force=True)

# to import all data at once, DutLib offers the import_directory method. This method needs a custom filter function to create the correct DutViews.


def filter_dut(dut_name):
    """Create the DutViews from the different folder names

    Parameters
    ----------
    dut_name : str
        Path to the dut folder

    Returns
    -------
    DMT.core.DutView
        DutView which should represent the data inside the folder
    """
    dut_path = Path(dut_name)
    dut_name = dut_path.parent.name
    width = re.search(r"_w([\dp]+)u_", dut_path.name, re.MULTILINE).group(1)
    width = float(width.replace("p", ".")) * 1e-6
    length = re.search(r"_l([\dp]+)u_", dut_path.name, re.MULTILINE).group(1)
    length = float(length.replace("p", ".")) * 1e-6
    dut_type = DutType.n_mos if "nfet" in dut_name else DutType.p_mos
    multiplication_factor = re.search(r"_m([\d]+)\(", dut_path.name, re.MULTILINE).group(1)
    multiplication_factor = int(multiplication_factor)

    dut = DutMeas(
        database_dir=path_to_dmt_core / "test" / "tmp",
        dut_type=dut_type,
        force=True,
        wafer="MPW-5",
        die="x",
        width=width,
        length=length,
        contact_config="SGD",
        name=dut_path.parent.name,
        reference_node="S",
        ndevices=multiplication_factor,
    )

    return dut


# to correctly key the different measurements, the temperature_converter function can be used:
def key_generator(key_part):
    if "IDVG" in key_part:
        return "T300.00K/IDVG"
    elif "IDVD" in key_part:
        return "T300.00K/IDVD"
    else:
        raise NotImplementedError


# Import the measurements using the dut filter function in parallel
lib.n_jobs = 6  # number of parallel jobs
lib.import_directory(
    import_dir=path_to_cells,
    dut_filter=filter_dut,
    dut_level=2,
    force=True,
    temperature_converter=key_generator,
)

# Clean the data to enfoce specifier columns
for dut_a in lib:
    dut_a.clean_data()

lib.dut_ref = lib.duts[0]  # does not matter currently

# The data is now read for further use
# to save just use:
# lib.save()
# to load in a different script:
# lib = DutLib.load(lib_save_dir)


# Here we will plot JD(VG) for VB = 0, VD=1.8 for all nfet 01v8
sp_vg = specifiers.VOLTAGE + ["G"]
sp_vb = specifiers.VOLTAGE + ["B"]
sp_vd = specifiers.VOLTAGE + ["D"]

sp_ig = specifiers.CURRENT + ["G"]
sp_ib = specifiers.CURRENT + ["B"]
sp_id = specifiers.CURRENT + ["D"]

sp_jd = specifiers.CURRENT_DENSITY + ["D"]

plot = Plot(
    "JD(VG)",
    x_specifier=sp_vg,
    y_specifier=sp_jd,
)

for dut in lib:
    if "nfet_01v8" in dut.name:
        df = dut.data["T300.00K/IDVG"]
        df = df[np.isclose(df[sp_vb], 0)]
        df = df[np.isclose(df[sp_vd], 1.8)]
        df[sp_jd] = df[sp_id] / dut.length / dut.width

        plot.add_data_set(
            df[sp_vg], df[sp_jd], label=f"w={dut.width*1e6:.2f}um, l={dut.length*1e6:.2f}um"
        )

plot.plot_pyqtgraph()

# To get a pdf with all information about the measurements DocuDutLib can be used:
docu = DocuDutLib(lib, devices=[{"name": "esd_nfet_01v8"}])
docu.generate_docu(
    lib_save_dir.parent / "docu_skywater130_raw",
    plot_specs=[
        {"type": "id(vg)", "key": "IDVG", "dut_type": DutType.n_mos},
        {"type": "id(vg)", "key": "IDVG", "dut_type": DutType.p_mos},
        {"type": "id(vd)", "key": "IDVD", "dut_type": DutType.n_mos},
        {"type": "id(vd)", "key": "IDVD", "dut_type": DutType.p_mos},
    ],
    show=False,
    save_tikz_settings={
        "width": "3in",
        "height": "5in",
        "standalone": True,
        "svg": False,
        "build": True,
        "mark_repeat": 20,
        "clean": True,  # Remove all files except *.pdf files in plots
    },
)
