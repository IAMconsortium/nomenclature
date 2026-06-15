"""Tests for CountryProcessor - country to regional aggregation (R5/R9/R10)."""

import pandas as pd
import pytest
from pathlib import Path
from pyam import IamDataFrame, assert_iamframe_equal
from pyam.utils import IAMC_IDX
from conftest import clean_up_external_repos

from nomenclature import DataStructureDefinition
from nomenclature.processor.countries import CountryProcessor

here = Path(__file__).parent
TEST_DATA_DIR = here / "data"
COUNTRY_TEST_DIR = TEST_DATA_DIR / "country_processing" / "dsd"


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

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "definitions")
    try:
        # Load DSD and apply CountryProcessor
        processor = CountryProcessor.from_definition(dsd)

        result = processor.apply(test_df)

        # Check that aggregated regions are present
        assert "Asia (R5)" in result.region
        assert "OECD & EU (R5)" in result.region
        assert "China (R9)" in result.region
        assert "Other OECD (R9)" in result.region
        assert "China+ (R10)" in result.region
        assert "Pacific OECD (R10)" in result.region

        # Check original countries are still present
        assert "China" in result.region
        assert "Japan" in result.region
        assert "Brazil" in result.region

        asia_data = result.filter(region="Asia (R5)")
        assert len(asia_data) > 0
        assert asia_data.filter(year=2005)["value"].values[0] == 15.0  # 10 + 5
        assert asia_data.filter(year=2010)["value"].values[0] == 18.0  # 12 + 6

        oecd_data = result.filter(region="OECD & EU (R5)")
        assert len(oecd_data) > 0
        assert oecd_data.filter(year=2005)["value"].values[0] == 25.0  # 20 + 2 + 3
        assert oecd_data.filter(year=2010)["value"].values[0] == 29.0  # 22 + 3 + 4

        china_r9 = result.filter(region="China (R9)")
        assert len(china_r9) > 0
        assert china_r9.filter(year=2005)["value"].values[0] == 10.0
        assert china_r9.filter(year=2010)["value"].values[0] == 12.0

        other_oecd_r9 = result.filter(region="Other OECD (R9)")
        assert len(other_oecd_r9) > 0
        assert other_oecd_r9.filter(year=2005)["value"].values[0] == 3.0
        assert other_oecd_r9.filter(year=2010)["value"].values[0] == 4.0

        china_r10 = result.filter(region="China+ (R10)")
        assert len(china_r10) > 0
        assert china_r10.filter(year=2005)["value"].values[0] == 10.0
        assert china_r10.filter(year=2010)["value"].values[0] == 12.0

        pacific_oecd_r10 = result.filter(region="Pacific OECD (R10)")
        assert len(pacific_oecd_r10) > 0
        assert pacific_oecd_r10.filter(year=2005)["value"].values[0] == 3.0
        assert pacific_oecd_r10.filter(year=2010)["value"].values[0] == 4.0
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_country_skips_missing_hierarchy_levels(monkeypatch):
    """Test that hierarchy levels not present in the mapping are skipped."""

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "definitions")
    try:
        processor = CountryProcessor.from_definition(dsd)

        monkeypatch.setattr(
            CountryProcessor,
            "regional_aggregates_by_level",
            property(lambda self: {"R5": {"Asia (R5)": ["China", "India"]}}),
        )

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

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "definitions")
    try:
        processor = CountryProcessor.from_definition(dsd)

        # model_b is not in the processor configuration, should return unchanged
        result = processor.apply(test_df)
        assert_iamframe_equal(result, test_df)
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_country_from_definition_no_models():
    """Test that from_definition raises error when no models are configured."""

    # Create a minimal DSD without country processor configuration
    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "definitions")

    try:
        # Override the processor configuration to be empty
        dsd.config.processor.countries = []

        with pytest.raises(
            ValueError, match="No models configured for Country processor"
        ):
            CountryProcessor.from_definition(dsd)
    finally:
        clean_up_external_repos(dsd.config.repositories)


def test_country_regional_aggregates_property():
    """Test the regional_aggregates property returns correct mappings."""

    dsd = DataStructureDefinition(COUNTRY_TEST_DIR / "definitions")
    try:
        processor = CountryProcessor.from_definition(dsd)

        aggregates = processor.regional_aggregates

        # Check expected R5 regions are present
        assert "Asia (R5)" in aggregates
        assert "OECD & EU (R5)" in aggregates

        # Check that China and India are in Asia, while Japan belongs to OECD & EU
        assert "China" in aggregates["Asia (R5)"]
        assert "India" in aggregates["Asia (R5)"]
        assert "Japan" not in aggregates["Asia (R5)"]
        assert "Japan" in aggregates["OECD & EU (R5)"]
    finally:
        clean_up_external_repos(dsd.config.repositories)
