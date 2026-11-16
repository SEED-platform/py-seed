import sys
from unittest import mock

import pytest

from pyseed.seed_client import SeedClient

PROGRESS_KEY = ":1:SEED:save_raw_data:PROG:57"


def test_get_progress_returns_current_progress_without_waiting(seed_client: SeedClient) -> None:
    progress = {"status": "parsing", "progress": 42, "progress_key": PROGRESS_KEY}
    seed_client.client.get.return_value = progress

    with mock.patch("pyseed.seed_client.time.sleep") as sleep:
        result = seed_client.get_progress(PROGRESS_KEY)

    assert result == progress
    sleep.assert_not_called()
    seed_client.client.get.assert_called_once_with(
        None,
        required_pk=False,
        endpoint="progress",
        url_args={"PROGRESS_KEY": PROGRESS_KEY},
    )


def test_get_progress_requires_progress_key(seed_client: SeedClient) -> None:
    with pytest.raises(ValueError, match="No progress key provided"):
        seed_client.get_progress("")

    seed_client.client.get.assert_not_called()


def test_get_progress_does_not_swallow_request_errors(seed_client: SeedClient) -> None:
    seed_client.client.get.side_effect = RuntimeError("connection refused")

    with pytest.raises(RuntimeError, match="connection refused"):
        seed_client.get_progress(PROGRESS_KEY)


def test_track_progress_result_polls_until_complete(seed_client: SeedClient) -> None:
    finished = {"status": "success", "progress": 100, "progress_key": PROGRESS_KEY}
    seed_client.client.get.side_effect = [
        {"status": "parsing", "progress": 10},
        RuntimeError("temporary failure"),
        {"status": "parsing", "progress": 60},
        finished,
    ]

    with mock.patch("pyseed.seed_client.time.sleep") as sleep:
        result = seed_client.track_progress_result(PROGRESS_KEY)

    assert result == finished
    assert seed_client.client.get.call_count == 4
    assert sleep.call_count == 3


def test_track_progress_result_survives_more_polls_than_the_recursion_limit(seed_client: SeedClient) -> None:
    polls = sys.getrecursionlimit() + 100
    finished = {"status": "success", "progress": 100, "progress_key": PROGRESS_KEY}
    seed_client.client.get.side_effect = [{"status": "parsing", "progress": 50}] * polls + [finished]

    with mock.patch("pyseed.seed_client.time.sleep"):
        result = seed_client.track_progress_result(PROGRESS_KEY)

    assert result == finished
    assert seed_client.client.get.call_count == polls + 1


def test_track_progress_result_requires_progress_key(seed_client: SeedClient) -> None:
    with pytest.raises(Exception, match="No progress key provided"):
        seed_client.track_progress_result(None)


def test_get_datasets_returns_unwrapped_datasets(seed_client: SeedClient) -> None:
    datasets = [{"id": 10, "name": "HQIIS", "importfiles": []}]
    seed_client.client.list.return_value = datasets

    result = seed_client.get_datasets()

    assert result == datasets
    seed_client.client.list.assert_called_once_with(endpoint="datasets", data_name="datasets")


def test_get_dataset_returns_dataset_with_import_files(seed_client: SeedClient) -> None:
    dataset = {
        "id": 10,
        "name": "HQIIS",
        "importfiles": [{"id": 55, "name": "AMC-1.xlsx", "mapping_done": True, "matching_done": False}],
    }
    seed_client.client.get.return_value = dataset

    result = seed_client.get_dataset(10)

    assert result == dataset
    seed_client.client.get.assert_called_once_with(10, endpoint="datasets", data_name="dataset")


def test_get_or_create_dataset_fetches_the_new_dataset(seed_client: SeedClient) -> None:
    dataset = {"id": 11, "name": "MDMS", "importfiles": []}
    seed_client.client.list.return_value = []
    seed_client.client.post.return_value = {"status": "success", "id": 11, "name": "MDMS"}
    seed_client.client.get.return_value = dataset

    result = seed_client.get_or_create_dataset("MDMS")

    assert result == dataset
    seed_client.client.get.assert_called_once_with(11, endpoint="datasets", data_name="dataset")


def test_get_import_file_returns_unwrapped_import_file(seed_client: SeedClient) -> None:
    import_file = {"id": 55, "raw_save_done": True, "mapping_done": False, "matching_done": False}
    seed_client.client.get.return_value = import_file

    result = seed_client.get_import_file(55)

    assert result == import_file
    seed_client.client.get.assert_called_once_with(55, endpoint="import_files", data_name="import_file")
