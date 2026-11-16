from datetime import date
from unittest import mock

from pyseed.seed_client import SeedClient


def test_get_cycles_returns_unwrapped_cycles(seed_client: SeedClient) -> None:
    cycles = [{"id": 1, "name": "Default Cycle"}]
    seed_client.client.list.return_value = cycles

    result = seed_client.get_cycles()

    assert result == cycles
    seed_client.client.list.assert_called_once_with(endpoint="cycles", data_name="cycles")


def test_create_cycle_returns_unwrapped_cycle(seed_client: SeedClient) -> None:
    seed_client.get_cycles = mock.MagicMock(return_value=[])
    cycle = {"id": 2, "name": "2018 Calendar Year"}
    seed_client.client.post.return_value = cycle

    result = seed_client.create_cycle("2018 Calendar Year", date(2018, 1, 1), date(2019, 1, 1))

    assert result == cycle
    seed_client.client.post.assert_called_once_with(
        endpoint="cycles",
        data_name="cycles",
        json={
            "name": "2018 Calendar Year",
            "start": "2018-01-01",
            "end": "2019-01-01",
        },
    )
