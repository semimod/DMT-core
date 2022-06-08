""" Module responsible for data reading in DMT.

The functions here read from many different formats into a DMT-DataFrame. As reading and writing is always very close, recommended and often used save functions for DataFrames are also given.

Functions
---------
read_data(filename)
    Reads a given file into the internal DMT dataframe, the file's extension determines the exact method which is then called for reading.

read_hdf(filename, key, convert_cmplx)
    Reads in a .hdf file into the internal DMT format.

read_elpa(filename)
    Reads in a .elpa file into the internal DMT format.

read_mdm(filename)
    Reads in a .mdm file into the internal DMT format.

read_csv(filename)
    Read .csv file and generate a DMT dataframe from it.

read_feather(filename)
    Read .feather file and generate a DMT dataframe from it.

read_DEVICE_bin(filename)
    Reads DEVICE binaries. Here the internal spacial data is saved. Returns a Dataframe.

read_ADS_bin(filename)
    Reads a ADS raw data file into a DMT dataframe.

read_tikz_file(filename, col_x=None, col_y=None)
    Reads a tikz plot file into a DMT dataframe.

save_hdf(df, save_dir, filename)
    Save the dataframe df into save_dir as filename.h5 .

save_elpa(fname, ELPA, cols, firstline)
    Save data as a elpa file.

"""
# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-core>
#
# This file is part of DMT_core.
#
# DMT_core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DMT_core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
import pandas as pd
import warnings
import numpy as np
import re
import _pickle as pickle
import struct
from pathlib import Path
from DMT.core import DataFrame


def read_data(filename, key=None, **kwargs):
    """General data reading routine.

    Used to read in data of an arbitrary file format. Correct reading routine is selected based on file extension.

    Parameters
    ----------
    filename : str
        Name of the file to be read including path

    Returns
    -------
    df       :  DMT.Dataframe()
        Dataframe that contains the cleaned up data contained in file filename
    """
    if not isinstance(filename, Path):
        filename = Path(filename)

    extension = filename.suffix.lower()

    if extension == ".mdm":
        df = read_mdm(str(filename))
    elif extension == ".elpa":
        df = read_elpa(filename)
    elif extension == ".crv":
        df = read_elpa(filename, header=3)
    elif extension == ".csv":
        df = read_csv(filename, **kwargs)
    elif extension == ".p":
        with filename.open("rb") as pickle_file:
            df = pickle.load(pickle_file)
    elif extension == ".h5":
        if key is None:
            key = "/df"
        df = read_hdf(filename, key)
    elif extension == ".feather":
        df = read_feather(filename)
    else:
        raise IOError(
            "Error: DMT can not open file "
            + filename
            + " since extension "
            + extension
            + " cannot be read."
        )

    # correct voltage names and make sure all potentials are available, account for imaginary numbers, e.g. columns R:S(1,1) and I:S(1,1) are stored as cmplx128 S(1,1)
    return df


def save_hdf(df, save_dir, filename):
    """Save the dataframe df into save_dir as filename.h5 .

    Parameters
    ----------
    df       :  pd.Dataframe()
        Pandas dataframe that shall be saved.
    save_dir :  str or os.Pathlike
        Directory where the file shall be saved
    filename : str
        Name of the file

    Returns
    -------
    boolean
        if saving was successfull returns True, else False
    """
    if not isinstance(save_dir, Path):
        save_dir = Path(save_dir)

    save_dir.mkdir(parents=True, exist_ok=True)

    return df.to_hdf(str(save_dir / (filename + ".h5")), key="df", mode="w")


def read_hdf(filename, key):
    """Read .h5 file and return the stored pandas dataframe from it.

    Parameters
    ----------
    filename      : str or os.Pathlike
        filename of .mdm file including path

    Returns
    -------
    dataframe  :  :class:`DMT.core.Dataframe`
        DMT DataFrame that stores the mdm data.
    """
    return pd.read_hdf(str(filename), key=key)


def read_mdm_blocks(block, n_row, n_col, n_iccap_vars, iccap_vars):
    data_raw = np.zeros([n_row, n_col + n_iccap_vars], dtype=np.float64)
    # read in raw data
    for i in range(n_row):
        data_raw[i, :n_col] = block[n_col * i : n_col * (i + 1)]
        data_raw[i, n_col : n_col + n_iccap_vars] = iccap_vars

    return data_raw


def read_mdm(filename):
    """Read .mdm file and generate a DMT dataframe from it.

    Parameters
    ----------
    filename : str or os.Pathlike
        filename of .mdm file including path.

    Returns
    -------
    :class:`DMT.core.Dataframe`
        DMT dataframe representing the mdm data.
    """
    block_data = []
    index_data = 0
    iccap_Vars = {}

    # open mdm for reading
    with open(filename, "r") as mdmfile:
        mdmtext = mdmfile.read()

    block_data = []
    for data in re.findall(r"^BEGIN_DB[\r\n]+([\s\S]*?)END_DB", mdmtext, re.MULTILINE):
        block_lines = data.splitlines()
        iccap_vars = {}
        for i, line in enumerate(block_lines):
            line = line.split()
            if "ICCAP_VAR" in line or "USER_VAR" in line:
                try:
                    iccap_vars[line[1]] = float(line[2])
                except ValueError:
                    raise ValueError(
                        "When trying to convert iccap_vars, ValueError. Could not convert to float."
                    )
                # pass
            else:
                if i == 0:
                    index_data = 0  # special case with no ICCAP_VARS
                else:
                    index_data = i + 1
                break
        # grab the cols
        cols = block_lines[index_data].replace("#", "").split()
        index_data += 1

        # get the raw data
        n_row = len(block_lines[index_data:])
        n_col = len(cols)
        n_iccap_vars = len(iccap_vars)

        block_str = " ".join(block_lines[index_data:])
        block_str = block_str.split()
        block = np.zeros(len(block_str))
        for i in range(len(block_str)):
            block[i] = float(block_str[i])

        data_raw = read_mdm_blocks(
            block,
            n_row,
            n_col,
            n_iccap_vars,
            np.array([value for key, value in iccap_vars.items()]),
        )
        # read in raw data
        # data_raw      =  np.zeros([n_row, n_col + n_iccap_vars ])
        # for i in range(n_row):
        #     data_raw[i,       :n_col             ]  =  block[ n_col*i : n_col*(i+1) ]
        #     data_raw[i,  n_col:n_col+n_iccap_vars]  =  [value  for key,value in iccap_vars.items()]

        cols.extend([key for key, value in iccap_vars.items()])
        block_data.append(data_raw)

    if block_data:
        all_data = np.concatenate(block_data)
        df = DataFrame(all_data, columns=cols)
        return df
    else:
        raise IOError("Failed to read from " + str(filename))


def read_elpa(filename, header=2):
    """Read .elpa file and generate a DMT dataframe from it.

    Parameters
    ----------
    filename : str
        filename of .elpa file including path.

    header   : integer
        Row number where actual data starts. Default=2 as is common for CEDIC in-house tools.

    Returns
    -------
    df       : :class:`DMT.core.Dataframe`
        DMT dataframe representing the elpa data.
    """
    # open file
    with open(filename, "r") as my_file:
        list_lines = my_file.readlines()

    # get column names
    list_lines = [line.strip() for line in list_lines]
    split_header = list_lines[1].split()
    columns = split_header[1:]  # names of columns

    try:  # catch device header splitting
        if int(split_header[0]) != len(columns):
            split_header2 = list_lines[2].split()
            try:
                float(split_header2[0])
                raise IOError(
                    "DMT->read_elpa: the number of columns and the length of the column names do not match. I tried to get more column names from the second line, but this failed."
                )
            except ValueError:
                columns = columns + split_header2
                header = 3 if header == 2 else header  # only tested for DEVICE
    except:
        pass

    # put all numeric values in large array and fill row by row taking n_data chunks
    # this omits the issue with line breaks produced e.g. by DEVICE
    list_lines = " ".join(list_lines[header:])
    list_lines = list_lines.split()
    list_lines = np.array([float(i) for i in list_lines])
    n_col = len(columns)
    n_row = len(list_lines) / len(columns)

    dummy = 1
    # check if n_row is an integer
    if n_row != round(n_row):
        warnings.warn(
            "DMT -> Data_reader: Encountered a weird number of rows in {:s} (n_row = {:f}).".format(
                filename, n_row
            )
        )

    n_row = int(n_row)  # but force it anyways!

    # fill the data into the 2-dimensional array data_raw
    data_raw = np.empty([n_row, n_col])
    for i in range(n_row):
        data_raw[i, :] = list_lines[n_col * i : n_col * (i + 1)]

    # initalize pd.Dataframe() and return it
    return DataFrame(data_raw, columns=columns)


def read_csv(filename, **kwargs):
    """Read .csv file and generate a DMT dataframe from it.

    Parameters
    ----------
    filename : str or os.Pathlike
        filename of .csv file including path.
    **kwargs
        kwargs are passed to pandas.read_csv

    Returns
    -------
    df       : :class:`DMT.core.Dataframe`
        DMT dataframe representing the csv data.
    """
    # ok, can just use standard pandas routine here. nice.
    df = pd.read_csv(str(filename), **kwargs)
    df.__class__ = DataFrame  # cast to DMT.DataFrame

    # work around for complex data in one column in the csv:
    # https://stackoverflow.com/a/18919965

    for col in df.columns:  # type: ignore
        if df[col].dtype == object:  # type: ignore
            try:
                df[col] = df[col].apply(lambda x: np.complex(x))  # type: ignore
            except AttributeError:
                # is there i instead of j ?
                df[col] = df[col].str.replace("i", "j").apply(lambda x: np.complex(x))  # type: ignore

    return df


def read_feather(filename, **kwargs):
    """Read .feather file and generate a DMT dataframe from it.

    Parameters
    ----------
    filename : str or os.Pathlike
        filename of .csv file including path.
    **kwargs
        kwargs are passed to pandas.read_csv

    Returns
    -------
    df       : :class:`DMT.core.Dataframe`
        DMT dataframe representing the csv data.
    """
    # ok, can just use standard pandas routine here. nice.
    df = pd.read_feather(str(filename), **kwargs)
    df.__class__ = DataFrame  # cast to DMT.DataFrame
    return df


def read_DEVICE_bin(filename):
    """Reads DEVICE binaries. Here the internal spacial data is saved. Returns a Dataframe.

    Parameters
    ----------
    filename : str
        Path to the file to read

    Returns
    -------
    df       : :class:`DMT.core.Dataframe`
        DMT dataframe representing the data.
    """

    def convert_to_int(ba_in):
        r"""Convert a byte array into an integer.

        Takes each byte from the input byte array and multiplies it with its "position"
        Example: ba_in = b'\xb4\t\x00\x00' => 00 00 09 B4 in hex
        First loop: char c = B4, should be multiplied with 1, (16*16)^0 = 1
        Second loop: char c = 09, should be multiplied with 256, (16*16)^1 = 256
        ...

        Parameters
        ----------
        ba_in : Byte array
            Read byte array from a binary file

        Returns
        -------
        int
            Calculated integer
        """
        return int(sum([c * pow(16 * 16, i_c) for i_c, c in enumerate(ba_in)]))

    # prepare struct unpack object
    obj_struct_f = struct.Struct("f")

    # first prepare dataframe
    with open(filename, mode="rb") as my_file:
        # length of one record
        ba_len_records = my_file.read(4)  # read an integer ( 4 Bytes)
        nr_len_records = convert_to_int(ba_len_records)  # [lrec]

        # read header
        # header is 76 Bytes long ( According to readdir.m )
        ba_header = my_file.read(76)
        _str_header = ba_header.decode()[3:75] + ba_header.decode()[0:2]

        # nr of axes
        # 1 for 1D, 2 for 2D, 3 for 3D
        nr_axes = convert_to_int(my_file.read(4))
        len_axes = [convert_to_int(my_file.read(4)) for i_axes in range(0, nr_axes)]
        len_axes_bytes = 4 + len(len_axes) * 4  # 4 bytes each, +8 from _nsum and _nend

        # next 2 are copied, I don't know their use
        _nsum = convert_to_int(my_file.read(4))
        _nend = convert_to_int(my_file.read(4))
        len_axes_bytes = len_axes_bytes + 8  # +8 from _nsum and _nend

        # read coordinates
        # construct indices: tuple of the coordinate permutations
        x = [obj_struct_f.unpack(my_file.read(4))[0] for i_x in range(0, len_axes[0])]
        name_columns = ["x"]
        len_axes_bytes = len_axes_bytes + len(x) * 4  # 4 bytes each, +8 from _nsum and _nend

        # y and z are only present in object if given in file
        if nr_axes >= 2:
            y = [obj_struct_f.unpack(my_file.read(4))[0] for i_y in range(0, len_axes[1])]
            name_columns.append("y")
            len_axes_bytes = len_axes_bytes + len(y) * 4  # 4 bytes each

            if nr_axes == 3:
                z = [obj_struct_f.unpack(my_file.read(4))[0] for i_z in range(0, len_axes[2])]
                name_columns.append("z")
                len_axes_bytes = len_axes_bytes + len(z) * 4  # 4 bytes each
                df_indices = []
                for z_a in z:
                    for y_a in y:
                        for x_a in x:
                            df_indices.append((x_a, y_a, z_a))
            else:
                df_indices = []
                for y_a in y:
                    for x_a in x:
                        df_indices.append((x_a, y_a))
        else:
            df_indices = x

    df = DataFrame(df_indices, columns=name_columns)

    # Read all records = saved variables over axis
    i_record = 0
    with open(filename, mode="rb") as my_file:
        while True:
            # jump to current record
            nr_jump = i_record * nr_len_records + 4
            my_file.seek(nr_jump, 0)  # 1 so relative to current position

            # read column name
            # header is 76 Bytes long ( According to readdir.m )
            ba_header = my_file.read(76)
            if len(ba_header) < 76:
                # here reading went wrong -> end of file!
                break
            col_name = ba_header.decode()[0:3].strip()

            # jump axis read
            my_file.seek(len_axes_bytes, 1)

            # read data in DEVICE sequence (for x,y,z index)
            read_vals = []
            if nr_axes == 1:
                # list of values
                for _i_x in range(0, len_axes[0]):
                    read_vals.append(obj_struct_f.unpack(my_file.read(4))[0])

            elif nr_axes == 2:
                # list readValues[i_y,i_x]
                for i_y in range(0, len_axes[1]):
                    # read_vals.append([])
                    for _i_x in range(0, len_axes[0]):
                        # read_vals[i_y].append(
                        read_vals.append(obj_struct_f.unpack(my_file.read(4))[0])

                # flatten the list of lists:
                # read_vals = list(chain(*read_vals))
            elif nr_axes == 3:
                # list readValues[i_z,i_y,i_x]
                for i_z in range(0, len_axes[2]):
                    read_vals.append([])
                    for i_y in range(0, len_axes[1]):
                        read_vals[i_z].append([])
                        for _i_x in range(0, len_axes[0]):
                            read_vals[i_z][i_y].append(obj_struct_f.unpack(my_file.read(4))[0])

                raise NotImplementedError(
                    "Needs testing how to flatten the list of lists of lists!"
                )

            df[col_name] = read_vals
            i_record = i_record + 1

    # check if pseudo 2D simulation
    if "y" in df.columns:
        if all((df["y"] == 0.0) | (df["y"] == df["y"].to_numpy()[-1])):
            # all 'y' are either 0.0 or 1.0 -> 1D simulation: cut off the df
            df = df[df["y"] == 0.0]
            del df["y"]

    return df


def read_ADS_bin(filename):
    """Reads a ADS raw data file into a DMT dataframe.

    Parameters
    ----------
    filename : str
        Path to the file to read

    Returns
    -------
    df       : :class:`DMT.core.Dataframe`
        DMT dataframe representing the data.
    """
    # read file
    with open(filename, "rb") as my_file:
        bin_content = my_file.readlines()

    # reverse order
    bin_content = bin_content[::-1]

    # binary 2 number
    # copy of sim_fe.read_raw_bin

    # content of file: simulations.name .type .var .data
    # 1st line: name
    _name = bin_content.pop()
    # 2nd line: date
    _date = bin_content.pop()

    # create output lists for both simulation types
    simulations = []
    simulations_dcop = []

    # prepare struct.Struct object for speed
    obj_struct_d = struct.Struct("d")

    # already get 1st line, for all others: rest after binary is this!
    line = bin_content.pop()
    while bin_content:
        sim = {}
        # analyze line

        # bugfix for letting line begin with Plotname
        # Use re, because it works in bytearrays
        pos = re.search(b"Plotname", line)
        while pos is None:
            # try to jump over this bias point :/
            # error prone because many things relay on same ordering as some reference...
            line = line + bin_content.pop()
            pos = re.search(b"Plotname", line)

        pos = pos.regs[0][0]
        line = line[pos:].decode()
        # type of simulation?
        if line[10:13] == "DC_":
            sim["name"] = line[18:]
            sim["type"] = line[10:17]
        else:
            sim["name"] = line[13:]
            sim["type"] = line[10:12]

        # next line is the format
        str_format = bin_content.pop().decode().strip()

        # number of variables and number of simulation points
        line = bin_content.pop()
        num_var = int(line[15:].strip())
        line = bin_content.pop()
        num_points = int(line[12:].strip())

        # Names of the columns
        sim["vars"] = []
        # in 1st column, there is "Variables:"
        for _i_var in range(num_var):
            line = bin_content.pop().strip().decode()
            str_splitted = line.split("\t")
            if str_splitted[0] == "Variables:":
                sim["vars"].append(str_splitted[2])
            else:
                sim["vars"].append(str_splitted[1])

        # remove "Binary:"
        line = bin_content.pop()[7:]

        # read the numbers according to the format
        if str_format == "Flags: real":
            if sim["type"] == "DC_DCOP":
                sim["data"] = []
                for _i_pt in range(num_points):
                    device_id = obj_struct_d.unpack_from(line)[0]
                    # check which type of simulation element is read
                    # at the moment _convert_CircuitElement_netlist in dut_ads sets the name to 3 characters!
                    str_splitted = sim["name"].split(".")
                    i_devicetype = len(str_splitted) - 1
                    if str_splitted[i_devicetype][0] == "R":
                        read_in = 3
                    elif str_splitted[i_devicetype][0] == "C":
                        read_in = 3
                    elif str_splitted[i_devicetype][0] == "S":
                        read_in = 3
                    elif str_splitted[i_devicetype][0] == "V":
                        read_in = 3
                    elif str_splitted[i_devicetype][0] == "I":
                        read_in = 3
                    else:
                        # VA-module
                        read_in = 3

                    line = bin_content.pop()
                    val = struct.unpack_from("{0}c".format(read_in), line)
                    val_decode = ""
                    for a in val:
                        try:
                            val_decode = val_decode + a.decode()
                        except UnicodeDecodeError:
                            break
                    sim["data_str"] = val_decode

                    data = np.zeros(num_var - 1)
                    data[0] = device_id
                    offset = read_in
                    for ndi_data in np.nditer(data[1:], op_flags=["writeonly"]):
                        while len(line) < offset + 8:
                            line = line + bin_content.pop()

                        ndi_data[...] = obj_struct_d.unpack_from(line, offset=offset)[0]
                        offset = offset + 8

                    sim["data"].append(data)
                    # old_line = line
                    # print('a: ' + str(line))
                    line = line[offset:]
                    # print('a: ' + str(line))

            else:
                data = np.zeros((num_var, num_points))
                offset = 0
                for ndi_data in np.nditer(data, order="F", op_flags=["writeonly"]):
                    while len(line) < offset + 8:
                        line = line + bin_content.pop()

                    ndi_data[...] = obj_struct_d.unpack_from(line, offset=offset)[0]
                    offset = offset + 8

                sim["data"] = data.transpose()
                # prepare for next iteration
                # old_line = line
                # print('b: ' + str(line))
                line = line[offset:]

        elif str_format == "Flags: complex":

            data = np.zeros((num_var, num_points), dtype=np.complex128)
            offset = 0

            # fortran order, 1h of bugfix Oo
            for ndi_data in np.nditer(data, order="F", op_flags=["writeonly"]):
                while len(line) < offset + 16:
                    line = line + bin_content.pop()

                a = obj_struct_d.unpack_from(line, offset=offset)[0]
                offset = offset + 8
                b = obj_struct_d.unpack_from(line, offset=offset)[0]
                offset = offset + 8

                ndi_data[...] = np.complex(a, b)

            sim["data"] = data.transpose()
            # old_line = line
            # print('c: ' + str(line))
            line = line[offset:]

        # save into output
        if sim["type"] == "DC_DCOP":
            simulations_dcop.append(sim)
        else:
            simulations.append(sim)

    return simulations, simulations_dcop


def save_elpa(fname, ELPA, cols, firstline):
    """Save data as a elpa file

    Parameters
    ----------
    fname : str or os.Pathlike
        Path to the file to save
    ELPA : object
        This parameter is passed to numpy.array as first parameter. Check this function for the supported types.
    cols : list[str]
        List of column names
    firstline : str
        First line (comment) for the file to create
    """
    # save xy data as elpa file
    # todo:does not work with pandas dataframes yet
    if not isinstance(fname, Path):
        fname = Path(fname)

    fname.parent.mkdir(parents=True, exist_ok=True)

    # make sure we have strings
    for i, col in enumerate(cols):
        cols[i] = str(col)

    with fname.open("w") as myfile:
        # --> write first line
        firstline = firstline.replace(chr(13), "")
        firstline = firstline.replace(chr(10), "")
        firstline = firstline + chr(13) + chr(10)
        myfile.write("{0:s}".format(firstline))

        # --> column line
        lc = len(cols)
        t = str(lc) + " "
        lc = len(t)
        if not cols == []:
            len_ = len(cols[0])
            t = t + chr(32) * (17 - len_ - lc) + cols[0] + " "
            for i in range(1, len(cols)):
                col = cols[i]
                len_ = len(col)
                if len_ > 17:
                    col = col[:17]
                    len_ = len(col)
                t = t + chr(32) * (17 - len_) + col + " "
            myfile.write("{0:s}\r\n".format(t[:-1]))

        # --> matrix
        ELPA = np.array(ELPA)

        if ELPA.shape[1] == len(cols):
            ELPA = np.transpose(ELPA)

        for ii in range(ELPA.shape[1]):
            for i in range(ELPA.shape[0]):
                if np.isnan(ELPA[i][ii]):
                    myfile.write("{0:17.9e} ".format(0))
                else:
                    myfile.write("{0:17.9e} ".format(ELPA[i][ii]))

            myfile.write("\r\n")


def read_tikz_file(filename, col_x=None, col_y=None):
    """Reads a tikz plot file into a DMT dataframe.

    Parameters
    ----------
    filename : str
        Path to the file to read
    col_x : str, optional
        Base name of the x columns, if not given, it is ugly extracted from the file
    col_y : str, optional
        Base name of the y columns, if not given, it is ugly extracted from the file

    Returns
    -------
    :class:`DMT.core.Dataframe`
        DMT dataframe representing the data.
    """
    # read file
    with open(filename, "r") as my_file:
        file_lines = my_file.readlines()

    # column base names
    for line in file_lines:
        if col_x is not None and col_y is not None:
            break

        if "xlabel" in line and col_x is None:
            col_x = re.search(r"\$(.+?)\$", line).group(1)
            if "/" in col_x:
                col_x = col_x.split("/")[0]
        elif "ylabel" in line and col_y is None:
            col_y = re.search(r"\$(.+?)\$", line).group(1)
            if "/" in col_y:
                col_y = col_y.split("/")[0]

    # column content
    data = {}
    for index, plotline in enumerate(
        re.finditer(
            r"\\addplot(.+?)};.+?(\\addlegendentry{(.+?)}\n|)", "".join(file_lines), flags=re.DOTALL
        )
    ):
        data_x = []
        data_y = []

        plt_lines = plotline.group(1).split("\n")

        for plt_line in plt_lines:
            match = re.match(r"([\d\.e-]+) ([\d\.e-]+)\\\\", plt_line)
            if match:
                data_x.append(float(match.group(1)))
                data_y.append(float(match.group(2)))

        sub_col = plotline.group(3)
        if sub_col is None:
            sub_col = str(index)

        data[col_x + sub_col] = np.array(data_x)
        data[col_y + sub_col] = np.array(data_y)

    return data
