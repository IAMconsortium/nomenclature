from nomenclature import CodeList

from conftest import TEST_DATA_DIR


def test_simple_codelist():
    """Import a simple codelist"""
    code = CodeList("simple").parse_files(TEST_DATA_DIR / "simple_codelist")

    assert "Some Variable" in code
    assert code["Some Variable"]["unit"] is None  # this is a dimensionless variable
