import pytest

from pyseed.exceptions import SEEDVersionError
from pyseed.seed_client import SeedClient


def test_resolve_result_column_ignores_trailing_seed_column_ids() -> None:
    rows = [
        {"site_eui_111": 42.0, "address_line_1_222": "100 A St"},
        {"site_eui_111": 51.0, "address_line_1_222": "200 B St"},
    ]

    result = SeedClient.resolve_result_column(rows, ["total_site_eui", "Site EUI"])

    assert result["ok"] is True
    assert result["display_name"] == "Site EUI"
    assert result["column_name"] == "site_eui_111"
    assert result["non_null_numeric_count"] == 2


def test_numeric_field_values_from_rows_filters_range() -> None:
    rows = [
        {"site_eui_111": -60},
        {"site_eui_111": -50},
        {"site_eui_111": 0},
        {"site_eui_111": 100},
        {"site_eui_111": 101},
        {"site_eui_111": None},
    ]

    result = SeedClient.numeric_field_values_from_rows(
        rows,
        common_names=["site_eui"],
        min_value=-50,
        max_value=100,
    )

    assert result["ok"] is True
    assert result["value_count"] == 3
    assert result["values"] == [-50.0, 0.0, 100.0]
    assert result["below_range_count"] == 1
    assert result["above_range_count"] == 1
    assert result["null_or_non_numeric_count"] == 1


def test_fixed_range_histogram_counts_right_edge_in_last_bin() -> None:
    values = [-50, -49, 0, 99.9, 100]

    bins = SeedClient._build_fixed_range_histogram(
        values=values,
        min_value=-50,
        max_value=100,
        bins=3,
    )

    assert bins == [
        {"min": -50.0, "max": 0.0, "count": 2},
        {"min": 0.0, "max": 50.0, "count": 1},
        {"min": 50.0, "max": 100.0, "count": 2},
    ]


def test_find_matching_columns_from_stats_ranks_matches_by_populated_count() -> None:
    stats_result = {
        "status": "success",
        "total_records": 10,
        "stats": [
            {"column_name": "site_eui", "display_name": "Site EUI", "is_extra_data": False, "count": 3},
            {"column_name": "weather_site_eui", "display_name": "Weather Site EUI", "is_extra_data": True, "count": 8},
            {"column_name": "address_line_1", "display_name": "Address Line 1", "is_extra_data": False, "count": 10},
            {"column_name": "site_energy", "display_name": "Site Energy", "is_extra_data": True, "count": 0},
        ],
    }

    result = SeedClient.find_matching_columns_from_stats(stats_result, ["site eui"], limit=5)

    assert result["ok"] is True
    assert result["total_records"] == 10
    assert [column["column_name"] for column in result["columns"]] == ["weather_site_eui", "site_eui"]
    assert result["columns"][0]["populated_fraction"] == 0.8
    assert result["top_populated_columns"][0]["column_name"] == "address_line_1"


def test_find_matching_columns_from_stats_rejects_empty_search_names() -> None:
    result = SeedClient.find_matching_columns_from_stats({"stats": []}, ["", "  "])

    assert result["ok"] is False
    assert result["error"] == "search_names is required"


def test_get_property_column_summary_by_cycle_calls_properties_column_summary_endpoint() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return {"status": "success", "stats": []}

    client = SeedClient.__new__(SeedClient)
    fake_api_client = FakeClient()
    client.client = fake_api_client
    client.cycle_id = 99
    client._cached_seed_version = (3, 4, 1)

    result = client.get_property_column_summary_by_cycle(
        cycle_id=22,
        column_names=["Site EUI", ""],
        include_raw_data=True,
        raw_data_limit=25,
    )

    assert result["status"] == "success"
    assert fake_api_client.calls[0]["endpoint"] == "properties_column_summary"
    assert fake_api_client.calls[0]["data_name"] == "all"
    assert fake_api_client.calls[0]["cycle_ids"] == "22"
    assert fake_api_client.calls[0]["column_names"] == "Site EUI"
    assert fake_api_client.calls[0]["include_raw_data"] is True
    assert fake_api_client.calls[0]["raw_data_limit"] == 25


def test_get_property_column_summary_by_cycle_defaults_column_names_to_all() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return {"status": "success", "stats": []}

    client = SeedClient.__new__(SeedClient)
    fake_api_client = FakeClient()
    client.client = fake_api_client
    client.cycle_id = 99
    client._cached_seed_version = (3, 4, 1)

    client.get_property_column_summary_by_cycle(cycle_id=22)

    assert fake_api_client.calls[0]["column_names"] == "all"


def test_get_property_column_summary_by_cycle_raises_seed_version_error_when_too_old() -> None:
    client = SeedClient.__new__(SeedClient)
    client.client = None
    client._cached_seed_version = (3, 3, 2)

    with pytest.raises(SEEDVersionError):
        client.get_property_column_summary_by_cycle(cycle_id=22)


def test_get_property_column_summary_by_cycle_raises_seed_version_error_when_not_strictly_newer() -> None:
    client = SeedClient.__new__(SeedClient)
    client.client = None
    # 3.4.0 itself does not satisfy the exclusive "> 3.4.0" requirement.
    client._cached_seed_version = (3, 4, 0)

    with pytest.raises(SEEDVersionError):
        client.get_property_column_summary_by_cycle(cycle_id=22)


def test_get_property_column_stats_by_cycle_delegates_to_column_summary() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return {"status": "success", "stats": []}

    client = SeedClient.__new__(SeedClient)
    fake_api_client = FakeClient()
    client.client = fake_api_client
    client.cycle_id = 77
    client._cached_seed_version = (3, 4, 1)

    result = client.get_property_column_stats_by_cycle()

    assert result["status"] == "success"
    assert fake_api_client.calls[0]["endpoint"] == "properties_column_summary"
    assert fake_api_client.calls[0]["cycle_ids"] == "77"


def test_get_site_eui_benchmark_data_uses_server_default_for_json() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return {"status": "success", "dataset": "category", "data": []}

    client = SeedClient.__new__(SeedClient)
    fake_api_client = FakeClient()
    client.client = fake_api_client
    client._cached_seed_version = (3, 4, 1)

    result = client.get_site_eui_benchmark_data(dataset="category")

    assert result["status"] == "success"
    assert fake_api_client.calls[0]["endpoint"] == "benchmark_data_site_eui"
    assert fake_api_client.calls[0]["data_name"] == "all"
    assert fake_api_client.calls[0]["dataset"] == "category"
    assert "output_format" not in fake_api_client.calls[0]


def test_get_site_eui_benchmark_data_decodes_csv_content() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def list(self, **kwargs):
            self.calls.append(kwargs)
            return {"status": "success", "content": b"a,b\n1,2\n"}

    client = SeedClient.__new__(SeedClient)
    fake_api_client = FakeClient()
    client.client = fake_api_client
    client._cached_seed_version = (3, 4, 1)

    result = client.get_site_eui_benchmark_data(dataset="subcategory", output_format="csv")

    assert result == "a,b\n1,2\n"
    assert fake_api_client.calls[0]["dataset"] == "subcategory"
    assert fake_api_client.calls[0]["output_format"] == "csv"


def test_get_site_eui_benchmark_data_raises_seed_version_error_when_not_strictly_newer() -> None:
    client = SeedClient.__new__(SeedClient)
    client.client = None
    # 3.4.0 itself does not satisfy the exclusive "> 3.4.0" requirement.
    client._cached_seed_version = (3, 4, 0)

    with pytest.raises(SEEDVersionError):
        client.get_site_eui_benchmark_data(dataset="category")


def test_parse_seed_version_parses_dotted_version_string() -> None:
    assert SeedClient._parse_seed_version("3.4.0") == (3, 4, 0)


def test_parse_seed_version_raises_for_unparsable_string() -> None:
    with pytest.raises(ValueError, match="Could not parse SEED version"):
        SeedClient._parse_seed_version("not-a-version")


def test_require_min_seed_version_passes_when_version_meets_inclusive_minimum() -> None:
    client = SeedClient.__new__(SeedClient)
    client._cached_seed_version = (3, 4, 0)

    # Should not raise.
    client._require_min_seed_version((3, 4, 0), feature="some_feature")


def test_require_min_seed_version_raises_when_below_inclusive_minimum() -> None:
    client = SeedClient.__new__(SeedClient)
    client._cached_seed_version = (3, 3, 2)

    with pytest.raises(SEEDVersionError) as exc_info:
        client._require_min_seed_version((3, 4, 0), feature="some_feature", reference="https://example.com/pr/1")

    assert "some_feature" in str(exc_info.value)
    assert ">= 3.4.0" in str(exc_info.value)
    assert "https://example.com/pr/1" in str(exc_info.value)


def test_require_min_seed_version_exclusive_rejects_equal_version() -> None:
    client = SeedClient.__new__(SeedClient)
    client._cached_seed_version = (3, 4, 0)

    with pytest.raises(SEEDVersionError, match=r"> 3\.4\.0"):
        client._require_min_seed_version((3, 4, 0), feature="some_feature", inclusive=False)
