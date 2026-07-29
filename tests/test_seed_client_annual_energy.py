"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

from unittest import mock

from pyseed.seed_client import SeedClient


def _make_client() -> SeedClient:
    # Bypass SeedClient.__init__ (which requires real connection config) since
    # get_annual_energy_from_meter_data only depends on get_meters/get_meter_data.
    return SeedClient.__new__(SeedClient)


def test_get_annual_energy_from_meter_data_uses_year_interval_and_forwards_exclusions() -> None:
    client = _make_client()
    meters = [{"alias": "Electric - Grid", "type": "Electric - Grid"}]
    usage = {"readings": [{"year": 2022, "Electric - Grid": 1000}]}

    client.get_meters = mock.MagicMock(return_value=meters)
    client.get_meter_data = mock.MagicMock(return_value=usage)

    with mock.patch("pyseed.seed_client.annual_energy_from_meter_data") as mock_normalize:
        mock_normalize.return_value = {"year": 2022, "energy_kbtu": {"total": 3412.0}}

        result = client.get_annual_energy_from_meter_data(123, year=2022, excluded_meter_ids=[5, 6])

    client.get_meters.assert_called_once_with(123)
    client.get_meter_data.assert_called_once_with(123, interval="Year", excluded_meter_ids=[5, 6])
    mock_normalize.assert_called_once_with({"meters": meters, "usage": usage}, year=2022)
    assert result == {"year": 2022, "energy_kbtu": {"total": 3412.0}}


def test_get_annual_energy_from_meter_data_defaults_excluded_meter_ids_and_year() -> None:
    client = _make_client()
    client.get_meters = mock.MagicMock(return_value=[])
    client.get_meter_data = mock.MagicMock(return_value={"readings": []})

    with mock.patch("pyseed.seed_client.annual_energy_from_meter_data") as mock_normalize:
        mock_normalize.return_value = {"year": 2021, "energy_kbtu": {"total": 0.0}}

        result = client.get_annual_energy_from_meter_data(123)

    client.get_meter_data.assert_called_once_with(123, interval="Year", excluded_meter_ids=[])
    mock_normalize.assert_called_once_with({"meters": [], "usage": {"readings": []}}, year=None)
    assert result == {"year": 2021, "energy_kbtu": {"total": 0.0}}
