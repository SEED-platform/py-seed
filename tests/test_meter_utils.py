import pytest

from pyseed.meter_utils import annual_energy_from_meter_data


def test_annual_energy_from_meter_data_converts_fuels_and_selects_year() -> None:
    result = annual_energy_from_meter_data(
        {
            "meters": [
                {"alias": "Electric - Grid", "type": "Electric - Grid"},
                {"alias": "Natural Gas", "type": "Natural Gas"},
            ],
            "usage": {
                "readings": [
                    {"year": 2020, "Electric - Grid": 1000, "Natural Gas": 3412},
                    {"year": 2021, "Electric - Grid": 1200, "Natural Gas": 3412},
                ]
            },
        },
        year=2020,
    )

    assert result["year"] == 2020
    assert result["energy_kbtu"]["electricity"] == pytest.approx(3412)
    assert result["energy_kbtu"]["natural_gas"] == pytest.approx(3412)
    assert result["energy_kbtu"]["total"] == pytest.approx(6824)


def test_annual_energy_from_meter_data_uses_latest_year_when_omitted() -> None:
    result = annual_energy_from_meter_data(
        {
            "meters": [{"alias": "Electric", "type": "Electric - Grid"}],
            "readings": [{"year": 2020, "Electric": 1}, {"year": 2021, "Electric": 2}],
        }
    )

    assert result["year"] == 2021
    assert "No meter year was supplied; the latest available year was selected." in result["warnings"]
