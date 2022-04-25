"""Testing the VA-Files Tree
"""
import pytest
import base64, zlib
from pathlib import Path
from DMT.core import VAFile
from DMT.core.va_file import VACode

path_here = Path(__file__).resolve().parent
path_to_cmc_model = path_here / "test_va_code" / "diode_cmc_160823"


def test_files():
    with pytest.raises(IOError) as exec_info:
        root_error = VAFile("root.va", files={"leaf.va": VACode(code="test code")})

    va_file = VAFile(
        "diode_cmc.va",
        files={
            "diode_cmc.va": VACode(code="test code"),
            "DIODE_CMC_InitModel.include": VACode(code="test child_code 1"),
            "DIODE_CMC_macrodefs.include": VACode(code="test child_code 2"),
        },
    )

    assert set(va_file.files.keys()) == {
        "diode_cmc.va",
        "DIODE_CMC_InitModel.include",
        "DIODE_CMC_macrodefs.include",
    }
    assert va_file.files["DIODE_CMC_InitModel.include"] == "test child_code 1"


def test_structure_generation():
    va_file = VAFile("diode_cmc.va")
    va_file.read_structure(path_to_cmc_model)

    assert len(va_file) == 7

    assert va_file.files[va_file.root] == (path_to_cmc_model / "diode_cmc.va").read_text()
    assert (
        va_file.files["DIODE_CMC_parlist.include"]
        == (path_to_cmc_model / "DIODE_CMC_parlist.include").read_text()
    )


def test_code_compression():
    va_file = VAFile("diode_cmc.va")
    va_file.read_structure(path_to_cmc_model)

    code_compressed, crc = va_file.files[va_file.root].code_compressed

    assert len(code_compressed) < len(va_file.files[va_file.root].code)
    assert crc == 871444854

    # decompress and compare:
    code = base64.b85decode(code_compressed.encode("utf-8"))
    code = zlib.decompress(code).decode("utf-8")
    assert code == (path_to_cmc_model / "diode_cmc.va").read_text()


def test_tree_hash():
    va_file = VAFile("diode_cmc.va")
    va_file.read_structure(path_to_cmc_model)

    assert va_file.get_tree_hash() == "199d457ec02425336859dfbee42dd5fd"


def test_dict_export():
    va_file = VAFile("diode_cmc.va")
    va_file.read_structure(path_to_cmc_model)

    export_dict = va_file.export_dict()

    va_file_imported = VAFile.import_dict(export_dict)

    assert va_file_imported.get_tree_hash() == "199d457ec02425336859dfbee42dd5fd"
    assert (
        va_file_imported.files[va_file_imported.root]
        == (path_to_cmc_model / "diode_cmc.va").read_text()
    )
    assert (
        va_file_imported.files["DIODE_CMC_parlist.include"]
        == (path_to_cmc_model / "DIODE_CMC_parlist.include").read_text()
    )

    export_dict_compressed = va_file.export_dict(compressed_code=True)
    va_file_imported_compressed = VAFile.import_dict(export_dict_compressed)

    assert va_file_imported_compressed.get_tree_hash() == "199d457ec02425336859dfbee42dd5fd"
    assert (
        va_file_imported_compressed.files[va_file_imported_compressed.root]
        == (path_to_cmc_model / "diode_cmc.va").read_text()
    )
    assert (
        va_file_imported_compressed.files["DIODE_CMC_parlist.include"]
        == (path_to_cmc_model / "DIODE_CMC_parlist.include").read_text()
    )


def test_write_files():
    va_file = VAFile("diode_cmc.va")
    va_file.read_structure(path_to_cmc_model)

    target_path = path_here.parent / "tmp" / "test_write_vafile"
    va_file.write_files(target_path)

    assert (target_path / "DIODE_CMC_SIMKIT_macrodefs.include").is_file()

    va_file_read = VAFile("diode_cmc.va")
    va_file_read.read_structure(target_path)

    assert va_file == va_file_read  # compare


if __name__ == "__main__":
    test_files()
    test_structure_generation()
    test_code_compression()
    test_tree_hash()
    test_dict_export()
    test_write_files()
