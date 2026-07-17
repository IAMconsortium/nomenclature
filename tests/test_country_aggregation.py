import pandas as pd
import pytest
from pathlib import Path
from pyam import IamDataFrame, assert_iamframe_equal
from pyam.utils import IAMC_IDX
from conftest import clean_up_external_repos

from nomenclature import DataStructureDefinition
from nomenclature.processor import CountryProcessor

here = Path(__file__).parent
TEST_DATA_DIR = here / "data"
COUNTRY_TEST_DIR = TEST_DATA_DIR / "country_processing"


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


def test_country_simple_aggregation():
    """Test basic country aggregation across R5, R9, and R10."""

    # Create test data with countries
    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", "China", "Primary Energy", "EJ/yr", 10.0, 12.0],
                ["model_a", "scen_a", "India", "Primary Energy", "EJ/yr", 5.0, 6.0],
                ["model_a", "scen_a", "Japan", "Primary Energy", "EJ/yr", 3.0, 4.0],
                [
                    "model_a",
                    "scen_a",
                    "United States",
                    "Primary Energy",
                    "EJ/yr",
                    20.0,
                    22.0,
                ],
                ["model_a", "scen_a", "Germany", "Primary Energy", "EJ/yr", 2.0, 3.0],
                ["model_a", "scen_a", "Brazil", "Primary Energy", "EJ/yr", 4.0, 5.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    expected_values = {
        "OECD & EU (R5)": {2005: 25.0, 2010: 29.0},
        "Asia (R5)": {2005: 15.0, 2010: 18.0},
        "Latin America (R5)": {2005: 4.0, 2010: 5.0},
        "European Union (R9)": {2005: 2.0, 2010: 3.0},
        "USA (R9)": {2005: 20.0, 2010: 22.0},
        "Other OECD (R9)": {2005: 3.0, 2010: 4.0},
        "China (R9)": {2005: 10.0, 2010: 12.0},
        "India (R9)": {2005: 5.0, 2010: 6.0},
        "Latin America (R9)": {2005: 4.0, 2010: 5.0},
        "China+ (R10)": {2005: 10.0, 2010: 12.0},
        "Europe (R10)": {2005: 2.0, 2010: 3.0},
        "India+ (R10)": {2005: 5.0, 2010: 6.0},
        "Latin America (R10)": {2005: 4.0, 2010: 5.0},
        "North America (R10)": {2005: 20.0, 2010: 22.0},
        "Pacific OECD (R10)": {2005: 3.0, 2010: 4.0},
    }
    expected_aggregates = IamDataFrame(
        pd.DataFrame(
            [
                ["model_a", "scen_a", region, "Primary Energy", "EJ/yr", year, value]
                for region, values_by_year in expected_values.items()
                for year, value in values_by_year.items()
            ],
            columns=IAMC_IDX + ["year", "value"],
        )
    )

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "all" / "definitions")
    try:
        # Load DSD and apply RegionProcessor
        processor = CountryProcessor.from_codelist(dsd=dsd, models=["model_a"])

        result = processor.apply(test_df)

        # Check that aggregated regions are present
        assert set(expected_values.keys()).issubset(set(result.region))

        # Check original countries are still present
        assert "China" in result.region
        assert "Japan" in result.region
        assert "Brazil" in result.region

        observed_aggregates = result.filter(region=list(expected_values))

        assert_iamframe_equal(observed_aggregates, expected_aggregates)
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_country_skips_missing_hierarchy_levels(monkeypatch):
    """Test that hierarchy levels not present in the mapping are skipped."""

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "r5" / "definitions")

    try:
        processor = CountryProcessor.from_codelist(dsd=dsd, models=["model_a"])
        result = processor.apply(_make_country_df(["China", "India"]))

        assert "Asia (R5)" in result.region
        assert "China (R9)" not in result.region
        assert "China+ (R10)" not in result.region
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_country_skip_unlisted_model():
    """Test that models not in the configured list are passed through unchanged."""

    test_df = IamDataFrame(
        pd.DataFrame(
            [
                ["model_b", "scen_a", "China", "Primary Energy", "EJ/yr", 10.0, 12.0],
                ["model_b", "scen_a", "India", "Primary Energy", "EJ/yr", 5.0, 6.0],
            ],
            columns=IAMC_IDX + [2005, 2010],
        )
    )

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "all" / "definitions")
    try:
        processor = CountryProcessor.from_codelist(dsd=dsd, models=["model_a"])

        # model_b is not in the processor configuration, should return unchanged
        result = processor.apply(test_df)
        assert_iamframe_equal(result, test_df)
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_country_from_definition_no_models():
    """Test that from_definition raises error when no models are configured."""

    # Create a minimal DSD without country processor configuration
    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "all" / "definitions")

    try:
        # Override the processor configuration to be empty
        dsd.config.processor.country = []

        with pytest.raises(
            ValueError, match="No models configured for country processor"
        ):
            CountryProcessor.from_codelist(dsd=dsd, models=[])
    finally:
        clean_up_external_repos(dsd.config.repositories)
