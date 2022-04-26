import pytest
from pathlib import Path
from DMT.core import DataFrame
from DMT.core import (
    specifiers,
    sub_specifiers,
    get_specifier_from_string,
    set_col_name,
    SpecifierStr,
)
from DMT.core import DatabaseManager

folder_path = Path(__file__).resolve().parent
test_path = folder_path.parent


def test_index_objects():
    new_spec = SpecifierStr("NEWSPECVAL")
    new_sub_spec = SpecifierStr("", sub_specifiers="NEWSUBSPECVAL")

    specifiers.add_members([("NEWSPECNAME", new_spec)])
    sub_specifiers.add_members([("NEWSUBSPECNAME", new_sub_spec)])

    # access them again:
    new_spec_2 = specifiers.NEWSPECNAME
    assert new_spec == new_spec_2

    # work with them:
    assert new_spec_2 + sub_specifiers.NEWSUBSPECNAME == "NEWSPECVAL|NEWSUBSPECVAL"

    with pytest.raises(OSError):
        specifiers.add_members([("CURRENT", SpecifierStr("I"))])
    with pytest.raises(OSError):
        specifiers.add_members([("CURRENT", SpecifierStr("B"))])
    with pytest.raises(OSError):
        sub_specifiers.add_members([("AREA", SpecifierStr("", sub_specifiers="AREA2"))])


def test_specifier_texts():
    assert specifiers.VOLTAGE + "B" == "V_B"
    assert specifiers.VOLTAGE + "_B" == "V_B"
    vb = specifiers.VOLTAGE + "B"
    vbe = vb + "E"
    assert vbe == "V_BE"
    assert vbe.to_raw_string() == "V_BE"
    assert isinstance(vbe.to_raw_string(), str)

    assert "V" + SpecifierStr("", "B") == "V_B"
    assert vbe + "" == vbe
    assert vbe is not None  # valid comparision !
    assert vbe != None  # valid comparision !

    with pytest.raises(TypeError):
        _a = vbe + 5
    with pytest.raises(TypeError):
        _a = 5 + vbe

    assert specifiers.VOLTAGE + "B" + sub_specifiers.AREA == "V_B|AREA"
    assert (
        specifiers.VOLTAGE + "B" + sub_specifiers.AREA + sub_specifiers.FORCED == "V_B|AREA|FORCED"
    )
    assert (
        specifiers.VOLTAGE + "B" + [sub_specifiers.AREA, sub_specifiers.FORCED] == "V_B|AREA|FORCED"
    )
    assert (
        specifiers.VOLTAGE + "B" + [sub_specifiers.FORCED, sub_specifiers.AREA] == "V_B|AREA|FORCED"
    )  # order of sub_specifiers does not matter
    assert specifiers.VOLTAGE + "B" + sub_specifiers.FORCED == "V_B|FORCED"
    assert specifiers.VOLTAGE + sub_specifiers.FORCED == "V|FORCED"

    assert set_col_name(specifiers.SS_PARA_Y, "2", "1") == "Y_21"
    assert specifiers.SS_PARA_Y + ["2", "1"] == "Y_21"

    # order of sub_specifiers does not matter
    assert specifiers.VOLTAGE + "B" + [
        sub_specifiers.AREA,
        sub_specifiers.FORCED,
    ] == specifiers.VOLTAGE + "B" + [sub_specifiers.FORCED, sub_specifiers.AREA]


def test_specifier_from_string():
    assert get_specifier_from_string("TAU_F").specifier == "TAU_F"
    assert get_specifier_from_string("BETA").specifier == "BETA"
    assert get_specifier_from_string("V_BE", nodes=["B", "E"]).specifier == "V"
    assert get_specifier_from_string("V_BE", nodes=["B", "E"]).nodes[1] == "E"
    assert get_specifier_from_string("V_BE|FORCED", nodes=["B", "E"]).sub_specifiers[0] == "FORCED"

    assert specifiers.FREQUENCY == "FREQ"
    assert set_col_name(specifiers.FREQUENCY) == "FREQ"
    assert SpecifierStr.string_from_load(specifiers.FREQUENCY.string_to_save()) == "FREQ"

    # only works for marked strings
    assert isinstance(SpecifierStr.string_from_load("FREQ"), str)
    assert not isinstance(SpecifierStr.string_from_load("FREQ"), SpecifierStr)


def column_save_load():
    a = DataFrame({SpecifierStr("V", "B"): [1]})

    dbm = DatabaseManager()
    dbm.save_df(a, test_path / "tmp" / "test_df.p")
    b = dbm.load_df(test_path / "tmp" / "test_df.p")

    assert isinstance(a.columns[0], SpecifierStr)
    assert isinstance(b.columns[0], SpecifierStr)

    data = {"a": a, "b": b}
    dbm.save_db(test_path / "tmp" / "test_db.p", data)
    data_loaded = dbm.load_db(test_path / "tmp" / "test_db.p")

    assert isinstance(data_loaded["a"].columns[0], SpecifierStr)
    assert data_loaded["a"].columns[0] == data["a"].columns[0]


def test_pretty_printing():
    col_ic = specifiers.CURRENT + "C"
    # description for POA
    assert col_ic.get_descriptor() == "current"

    # unit:
    assert str(col_ic.get_pint_unit()) == "ampere"

    assert col_ic.get_tex_unit() == "\\si{\\ampere}"

    with pytest.raises(IOError):
        specifiers.ELECTRONS.get_pint_unit()

    # labeling
    assert col_ic.to_tex() == "I_{\\mathrm{C}}"
    assert col_ic.to_label() == "$I_{\\mathrm{C}}\\left(\\si{\\ampere}\\right)$"
    assert col_ic.to_label(negative=True) == "$-I_{\\mathrm{C}}\\left(\\si{\\ampere}\\right)$"

    col_y21 = specifiers.SS_PARA_Y + ["C", "B"]
    assert col_y21.to_tex() == "\\underline{Y}_{\\mathrm{21}}"
    col_y21_imag = specifiers.SS_PARA_Y + ["C", "B"] + sub_specifiers.IMAG
    assert col_y21_imag.to_tex() == "\\Im\\{\\underline{Y}_{\\mathrm{21}}\\}"


if __name__ == "__main__":
    test_index_objects()
    test_specifier_texts()
    test_specifier_from_string()
    column_save_load()
    test_pretty_printing()
    dummy = 1
