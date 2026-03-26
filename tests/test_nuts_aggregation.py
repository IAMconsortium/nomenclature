# tests/test_nuts_aggregation.py
import pandas as pd
import pytest
from pathlib import Path
from pyam import IamDataFrame, assert_iamframe_equal
from pyam.utils import IAMC_IDX

from nomenclature import DataStructureDefinition
from nomenclature.processor.nuts import NutsProcessor, EU27_MIN_COUNTRIES

here = Path(__file__).parent
TEST_DATA_DIR = here / "data"
NUTS_TEST_DIR = TEST_DATA_DIR / "nuts_processing" / "dsd"
NUTS_NO_EU_TEST_DIR = TEST_DATA_DIR / "nuts_processing" / "dsd_no_eu"

# 27 EU member country names (as returned by the countries module)
EU27_NAMES = [
    "Austria",
    "Belgium",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Germany",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Greece",
    "Hungary",
    "Ireland",
    "Italy",
    "Lithuania",
    "Luxembourg",
    "Latvia",
    "Malta",
    "Netherlands",
    "Poland",
    "Portugal",
    "Romania",
    "Sweden",
    "Slovenia",
    "Slovakia",
    "Spain",
    "Czechia",
]
assert len(EU27_NAMES) == 27

UK_NAME = "United Kingdom"


def _make_country_df(countries: list[str], value: float = 1.0) -> IamDataFrame:
    """Build a minimal IamDataFrame with one row per country."""
    return IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", c, "Primary Energy", "EJ/yr", value, value]
                for c in countries
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )


def test_nuts_simple_aggregation():
    """Test basic NUTS3 -> NUTS2 -> NUTS1 -> Country aggregation"""

    # Create test data with NUTS3 regions (Austria)
    # AT111, AT112 should aggregate to AT11 (NUTS2) -> AT1 (NUTS1) -> Austria
    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "AT111", "Primary Energy", "EJ/yr", 1.0, 2.0],
                ["model_a", "scen_a", "AT112", "Primary Energy", "EJ/yr", 3.0, 4.0],
                ["model_a", "scen_a", "Belgium", "Primary Energy", "EJ/yr", 5.0, 6.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    # Expected output: aggregated hierarchies + all original/intermediate NUTS regions
    expected = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "AT1", "Primary Energy", "EJ/yr", 4.0, 6.0],
                ["model_a", "scen_a", "AT11", "Primary Energy", "EJ/yr", 4.0, 6.0],
                ["model_a", "scen_a", "AT111", "Primary Energy", "EJ/yr", 1.0, 2.0],
                ["model_a", "scen_a", "AT112", "Primary Energy", "EJ/yr", 3.0, 4.0],
                ["model_a", "scen_a", "Austria", "Primary Energy", "EJ/yr", 4.0, 6.0],
                ["model_a", "scen_a", "Belgium", "Primary Energy", "EJ/yr", 5.0, 6.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    # Load DSD and apply NUTS processor
    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)

    result = processor.apply(test_df)

    assert_iamframe_equal(result, expected)


def test_nuts_duplicate_aggregation_raises():
    """Test that NUTS aggregation on a region and its children raises."""

    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "AT111", "Primary Energy", "EJ/yr", 1.0, 2.0],
                ["model_a", "scen_a", "AT112", "Primary Energy", "EJ/yr", 3.0, 4.0],
                ["model_a", "scen_a", "AT11", "Primary Energy", "EJ/yr", 5.0, 6.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)

    with pytest.raises(ValueError, match="Duplicate rows in `data`"):
        processor.apply(test_df)


def test_eu27_aggregation_sufficient_countries():
    """EU27 aggregate is produced when at least 23 members are present."""
    countries = EU27_NAMES[:EU27_MIN_COUNTRIES]
    test_df = _make_country_df(countries)

    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)
    result = processor.apply(test_df)

    # All original countries still present, plus European Union
    assert "European Union" in result.region
    # Individual country data preserved
    for country in countries:
        assert country in result.region
    # No EU+UK since UK not in data
    assert "European Union and United Kingdom" not in result.region


def test_eu27_aggregation_insufficient_countries():
    """No EU27 aggregate produced when fewer than 23 members present."""
    countries = EU27_NAMES[:3]
    test_df = _make_country_df(countries)

    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)
    result = processor.apply(test_df)

    assert "European Union" not in result.region
    assert "European Union and United Kingdom" not in result.region


def test_eu27_uk_aggregation_with_uk():
    """Test both EU27 and EU27+UK are produced when UK is present."""
    countries = EU27_NAMES[:EU27_MIN_COUNTRIES] + [UK_NAME]
    test_df = _make_country_df(countries)

    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)
    result = processor.apply(test_df)

    assert "European Union" in result.region
    assert "European Union and United Kingdom" in result.region

    # EU values: sum of 23 countries at value=1.0
    eu_value = float(EU27_MIN_COUNTRIES)
    eu_data = result.filter(region="European Union")
    assert (eu_data.data["value"] == eu_value).all()
    eu_uk_data = result.filter(region="European Union and United Kingdom")
    assert (eu_uk_data.data["value"] == eu_value + 1.0).all()


def test_eu27_aggregation_without_uk():
    """Test only EU27 (not EU27+UK) is produced when UK is absent."""
    countries = EU27_NAMES[:EU27_MIN_COUNTRIES]
    test_df = _make_country_df(countries)

    dsd = DataStructureDefinition(NUTS_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)
    result = processor.apply(test_df)

    assert "European Union" in result.region
    assert "European Union and United Kingdom" not in result.region


def test_eu27_aggregation_codelist_gating():
    """Test no EU aggregation is attempted when 'European Union' not in region codelist."""
    test_df = _make_country_df(EU27_NAMES)

    dsd = DataStructureDefinition(NUTS_NO_EU_TEST_DIR / "definitions")
    processor = NutsProcessor.from_definition(dsd)
    result = processor.apply(test_df)

    assert "European Union" not in result.region
    assert "European Union and United Kingdom" not in result.region
