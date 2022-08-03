""" VA Code structure. As Includes traverse like a tree, it is implemented as a dictionary Oo.
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

from __future__ import annotations
import zlib, base64
from typing import Union, Callable, Optional
from pathlib import Path
import verilogae

from DMT.core import create_md5_hash


class VACode(object):  # Storage
    """Base file for VA-Codes

    Parameters
    ----------
    name : str
        Name of the code file (should include a relative path to the file which includes this one)
    code : str, optional
        Code of the file
    code_compressed : (str, int), optional
        Compressed code as loaded from a json modelcard file.
    ignore_checksum: bool, optional
        If True, the checksum is ignored, defaults to False.
    """

    def __init__(
        self,
        code: str = "",
        code_compressed: tuple[str, int] = ("", -1),
        ignore_checksum: bool = False,
    ):
        self.code = code

        if not self.code and code_compressed[0]:
            self.decompress_code(
                code_compressed[0], code_compressed[1], ignore_checksum=ignore_checksum
            )

    def __str__(self) -> str:
        """Some short cuts"""
        return self.code

    def __eq__(self, other: VACode) -> bool:
        """Compare two Files. Equal if both name and codes are equal

        Parameters
        ----------
        other : VAFileBase
            Other VAFile to compare

        Returns
        -------
        bool
            True if both have the same name and code...
        """
        if isinstance(other, VACode):
            # the files are equal if the codes are the same ??
            # because if the file are collected from 2 different locations they are still the same -> not true because of includes...
            return self.code == other.code
        elif isinstance(other, str):
            return self.code == other

        return NotImplemented

    @property
    def code_compressed(self):
        """zlib compressed code for saving in modelcard json files.

        Returns
        -------
        (str, str)
            Compressed code and CRC32 check sum after compression and before encoding.
        """
        code = zlib.compress(self.code.encode("utf-8"), level=9)
        csum = zlib.crc32(code)
        code = base64.b85encode(code).decode("utf-8")
        return (code, csum)

    def decompress_code(self, code_compressed: str, csum: int, ignore_checksum: bool = False):
        """Set compressed code to file, will be decompressed and saved in self.code

        Parameters
        ----------
        code_compressed : str
            compressed code
        csum : str
            CRC32 check sum loaded from file.
        ignore_checksum: bool, optional
            If True, the checksum is ignored, defaults to False.

        Raises
        ------
        OSError
            If the saved checksum and checksum of decompressed code do not match
        """
        code = base64.b85decode(code_compressed.encode("utf-8"))
        if not ignore_checksum and csum != zlib.crc32(code):
            raise OSError(
                "Saved checksum and checksum of decompressed code do not match",
                "MCard load compressed va_codes failed. VA-Codes not loaded, manual reset needed!",
            )  # Raise an error here??
        self.code = zlib.decompress(code).decode("utf-8")


class VAFile(object):
    """Tree VA-File for VA-Code. The tree is chosen to correctly mirror possible file structures of multi-file VA-Codes

    Parameters
    ----------
    name : Union[str, Path]
        Absolute or relative path to file or just name of the root file.
    files : dict, optional
        Dictionary with {file_name: VACode}. One of the keys must be the same as the name, by default None
    code : Union[str, VACode], optional
        Code of the root file, by default ""
    code_compressed : (str, int), optional
        Compressed code as loaded from a json modelcard file.
    ignore_checksum: bool, optional
        If True, the checksum is ignored, defaults to False.
    """

    def __init__(
        self,
        name: Union[str, Path],
        files: Optional[dict[str, VACode]] = None,
        code: Union[str, VACode] = "",
        code_compressed: tuple[str, int] = ("", -1),
        ignore_checksum: bool = False,
    ):
        self.files: dict[str, VACode] = {}

        if not isinstance(name, Path):
            name = Path(name)

        self.root: str = name.name
        if files is None:

            if name.is_file():
                self.read_structure(name.parent)
            elif code:
                if isinstance(code, VACode):
                    self.files[self.root] = code
                else:
                    self.files[self.root] = VACode(code=code)
            elif code_compressed[0]:
                self.files[self.root] = VACode(
                    code_compressed=code_compressed, ignore_checksum=ignore_checksum
                )
        else:
            self.files = files

            if self.root not in self.files:
                raise IOError("The root must be part of the file structure.")

    @property
    def root_vfs(self) -> str:
        """Returns the root path inside the vfs

        Returns
        -------
        str
            [description]
        """
        return "/" + self.root

    @property
    def vfs(self) -> dict[str, str]:
        vfs = dict()
        for name, code in self.files.items():
            vfs["/" + name] = str(code)
        return vfs

    def rename_root(self, name_new: str):
        """Rename the root file

        Parameters
        ----------
        name_new : str
            New name

        Raises
        ------
        IOError
            If the new name already existed.
        """
        if name_new in self.files:
            raise IOError("The given new root name already exists in the file tree.")

        self.files[name_new] = self.files[self.root]
        del self.files[self.root]
        self.root = name_new

    def read_structure(self, path_to_own_folder: Union[str, Path]):
        """Checks the file for imports and adds them into the dict. This is done using verilogae.

        Parameters
        ----------
        path_to_own_folder : Union[str, Path]
            Path, in which the main file of the model is located.

        Raises
        ------
        NotImplementedError
            Currently only relative imports are supported. If a file includes an absolute path, the error is raised.
        """
        if not isinstance(path_to_own_folder, Path):
            path_to_own_folder = Path(path_to_own_folder)

        path_to_main_code = path_to_own_folder / self.root

        try:
            self.files[self.root] = VACode(code=path_to_main_code.read_text())  # be safe
        except FileNotFoundError as e:
            va_files = path_to_own_folder.glob("*.va")
            va_files = [str(va_file) for va_file in va_files]
            va_files = "\n" + "\n".join(va_files)
            raise FileNotFoundError(
                e.strerror, e.filename, " . Verilog-A files in this folder:" + va_files
            )

        for file, code in verilogae.export_vfs(str(path_to_main_code)).items():  # type: ignore
            self.files[file[1:]] = VACode(code=code)

    def get_tree_hash(self) -> str:
        """Create a hash for all the codes from this node and all its children. Should be unique for each model...

        Returns
        -------
        str
            MD5 Hash for the code of this file and all its children
        """
        return create_md5_hash(*[vafile.code for vafile in self.files.values()])

    def export_dict(self, compressed_code: bool = False) -> dict:
        """Export self and children into a dictionary for serialization

        Parameters
        ----------
        compressed_code : bool, optional
            Set to true to get compressed code, by default False

        Returns
        -------
        dict
            [description]
        """
        export = {"__root__": self.root}  # this should be not used somewhere!
        for name, vafile in self.iter_codes():
            if compressed_code:
                export[name] = vafile.code_compressed  # type: ignore
            else:
                export[name] = vafile.code

        return export

    @classmethod
    def import_dict(cls, data_import: dict, ignore_checksum: bool = False) -> VAFile:
        """Imports a VAFile inclusive children from a (serialized) dictionary

        Parameters
        ----------
        data_import : dict
            [description]
        ignore_checksum: bool, optional
            If True, the checksum is ignored, defaults to False.

        Returns
        -------
        VAFile
            [description]
        """
        root = data_import.pop("__root__")
        files = {}

        for name, code in data_import.items():
            if isinstance(code, str):
                files[name] = VACode(code=code)
            else:
                files[name] = VACode(code_compressed=code, ignore_checksum=ignore_checksum)

        return VAFile(name=root, files=files)

    def write_files(
        self, path_to_target: Union[str, Path], filter: Optional[Callable[[str], str]] = None
    ):
        """Writes the VAFile and all its descendants into the given target path. The file structure is written as read from the "original"

        Parameters
        ----------
        path_to_target : Union[str, Path]
            Path to target directory
        filter : callable, optional

        """
        if not isinstance(path_to_target, Path):
            path_to_target = Path(path_to_target)

        for (name, code) in self.iter_codes():
            path_to_vafile = path_to_target / name
            path_to_vafile.parent.mkdir(exist_ok=True, parents=True)
            if filter is not None:
                text = filter(code.code)
            else:
                text = code.code
            path_to_vafile.write_text(text)

    def iter_codes(self):
        """Iterate through all name:code items"""
        return self.files.items()

    def __len__(self) -> int:
        """Number of Files inside the tree

        Returns
        -------
        int
            Length of tree
        """
        return len(self.files)

    def __eq__(self, other: object) -> bool:
        """Allows comparing two VAFiles

        Parameters
        ----------
        other : object
            Only possible for other VAFiles.

        Returns
        -------
        bool
            True if other VAFile has same root and same files.
        """
        if isinstance(other, VAFile):
            return self.root == other.root and self.files == other.files

        return NotImplemented
