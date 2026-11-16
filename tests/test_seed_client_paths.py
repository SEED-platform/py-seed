import json
from datetime import date
from pathlib import Path
from unittest import mock

import pytest

from pyseed.seed_client import SeedClient, SeedClientWrapper


def test_read_connection_config_file_accepts_string_path(tmp_path: Path) -> None:
    config_path = tmp_path / "seed-config.json"
    config = {"base_url": "https://seed.example.org", "username": "user@example.org"}
    config_path.write_text(json.dumps(config), encoding="utf-8")

    assert SeedClientWrapper.read_connection_config_file(str(config_path)) == config


@pytest.mark.parametrize("method_name", ["retrieve_portfolio_manager_property", "retrieve_portfolio_manager_meters"])
def test_portfolio_manager_downloads_accept_string_destination(seed_client: SeedClient, tmp_path: Path, method_name: str) -> None:
    seed_client.client.post.return_value = b"spreadsheet contents"
    destination = tmp_path / f"{method_name}.xlsx"

    if method_name == "retrieve_portfolio_manager_property":
        result = seed_client.retrieve_portfolio_manager_property("username", "password", 123, str(destination))
    else:
        result = seed_client.retrieve_portfolio_manager_meters(
            "username",
            "password",
            ["123"],
            date(2025, 1, 1),
            date(2025, 12, 31),
            str(destination),
        )

    assert result == {"status": "success"}
    assert destination.read_bytes() == b"spreadsheet contents"


def test_update_access_level_instances_accepts_path(seed_client: SeedClient, tmp_path: Path) -> None:
    seed_client.client.org_id = 42
    seed_client.client.post.return_value = {"progress_key": "progress-key"}
    seed_client.track_progress_result = mock.MagicMock(return_value={"status": "success", "progress": 100})
    workbook_path = tmp_path / "access-levels.xlsx"
    workbook_path.write_bytes(b"workbook contents")
    uploaded_file = {}

    def capture_upload(*_args, **kwargs):
        filename, file_handle, content_type = kwargs["files"]["file"]
        uploaded_file.update(filename=filename, content=file_handle.read(), content_type=content_type)
        return {"success": True, "tempfile": "temporary-file.xlsx"}

    seed_client.client.put.side_effect = capture_upload

    result = seed_client.update_organizations_access_level_instances(workbook_path)

    assert result == {"status": "success", "progress": 100}
    assert uploaded_file == {
        "filename": "access-levels.xlsx",
        "content": b"workbook contents",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    seed_client.client.post.assert_called_once_with(
        endpoint="start_org_access_level_instances_file_save",
        url_args={"PK": 42},
        json={"filename": "temporary-file.xlsx"},
    )
    seed_client.track_progress_result.assert_called_once_with("progress-key")
