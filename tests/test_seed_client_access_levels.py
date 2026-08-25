from unittest import mock

import pytest

from pyseed.exceptions import SEEDError
from pyseed.seed_client import SeedClient

ACCESS_LEVEL_TREE = {
    "access_level_names": ["Better Buildings", "Sector", "Sub Sector", "Partner Name"],
    "access_level_tree": [
        {
            "id": 1,
            "name": "root",
            "path": {"Better Buildings": "root"},
            "children": [
                {
                    "id": 2,
                    "name": "Public Sector Partner",
                    "path": {"Better Buildings": "root", "Sector": "Public Sector Partner"},
                    "children": [
                        {
                            "id": 3,
                            "name": "Local Government",
                            "path": {
                                "Better Buildings": "root",
                                "Sector": "Public Sector Partner",
                                "Sub Sector": "Local Government",
                            },
                            "children": [
                                {
                                    "id": 204,
                                    "name": "Arvada, CO",
                                    "path": {
                                        "Better Buildings": "root",
                                        "Sector": "Public Sector Partner",
                                        "Sub Sector": "Local Government",
                                        "Partner Name": "Arvada, CO",
                                    },
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}


def make_client() -> SeedClient:
    client = SeedClient.__new__(SeedClient)
    client.get_organization_access_level_tree = mock.MagicMock(return_value=ACCESS_LEVEL_TREE)
    return client


def test_find_organization_access_level_instance_resolves_partner_name() -> None:
    client = make_client()

    result = client.find_organization_access_level_instance("partner name", "arvada, co")

    assert result["id"] == 204
    assert result["path"]["Partner Name"] == "Arvada, CO"


def test_find_organization_access_level_instance_reports_unknown_level() -> None:
    client = make_client()

    with pytest.raises(SEEDError, match="available levels"):
        client.find_organization_access_level_instance("City", "Arvada")


def test_get_properties_by_accountability_hierarchy_filters_full_path() -> None:
    client = make_client()
    client.get_properties_by_criteria = mock.MagicMock(
        return_value=[
            {
                "property_name": "City Hall",
                "Better Buildings": "root",
                "Sector": "Public Sector Partner",
                "Sub Sector": "Local Government",
                "Partner Name": "Arvada, CO",
            },
            {
                "property_name": "Other Building",
                "Better Buildings": "root",
                "Sector": "Public Sector Partner",
                "Sub Sector": "Local Government",
                "Partner Name": "Other City",
            },
        ]
    )

    result = client.get_properties_by_accountability_hierarchy("Partner Name", "Arvada, CO")

    assert result["access_level_instance"]["id"] == 204
    assert result["total_count"] == 1
    assert result["properties"][0]["property_name"] == "City Hall"


def test_get_properties_by_accountability_hierarchy_validates_limit() -> None:
    client = make_client()

    with pytest.raises(ValueError, match="limit must be greater than 0"):
        client.get_properties_by_accountability_hierarchy("Partner Name", "Arvada, CO", limit=0)
