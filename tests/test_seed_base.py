"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

import unittest
import uuid
from datetime import date
from pathlib import Path

import pytest

from pyseed.seed_client import SeedClient


@pytest.mark.integration
class SeedBaseTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """setup for all of the tests below"""
        cls.organization_id = 1

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path("seed-config.json")
        cls.seed_client = SeedClient(cls.organization_id, connection_config_filepath=config_file)

        cls.organization_id = 1

    @classmethod
    def teardown_class(cls):
        # remove all of the test buildings?
        pass

    def test_get_organizations(self):
        organizations = self.seed_client.get_organizations()
        assert len(organizations) > 0

    def test_get_create_delete_cycle(self):
        all_cycles = self.seed_client.get_cycles()
        cycle_count = len(all_cycles)
        assert cycle_count >= 1

        # create a new unique cycle
        unique_id = str(uuid.uuid4())[:8]
        cycle = self.seed_client.get_or_create_cycle(f"test cycle {unique_id}", date(2021, 1, 1), date(2022, 1, 1))
        assert cycle["name"] == f"test cycle {unique_id}"
        cycle_id = cycle["id"]
        all_cycles = self.seed_client.get_cycles()
        assert len(all_cycles) == cycle_count + 1
        # verify that it won't be created again
        cycle = self.seed_client.get_or_create_cycle(f"test cycle {unique_id}", date(2021, 1, 1), date(2022, 1, 1))
        assert cycle_id == cycle["id"]
        all_cycles = self.seed_client.get_cycles()
        assert len(all_cycles) == cycle_count + 1

        # now delete the new cycle
        all_cycles = self.seed_client.get_cycles()
        self.seed_client.delete_cycle(cycle_id)
        all_cycles = self.seed_client.get_cycles()
        assert len(all_cycles) == cycle_count

    def test_create_cycle(self):
        new_cycle_name = "test cycle for test_create_cycle"
        cycle = self.seed_client.create_cycle(new_cycle_name, date(2021, 6, 1), date(2022, 6, 1))
        cycle_id = cycle["id"]
        assert cycle is not None

        # verify that trying to create the same name will fail
        with pytest.raises(Exception) as exc_info:  # noqa: PT011
            self.seed_client.create_cycle(new_cycle_name, date(2021, 6, 1), date(2022, 6, 1))
        assert exc_info.value.args[0] == f"A cycle with this name already exists: '{new_cycle_name}'"

        # test the setting of the ID
        cycle = self.seed_client.get_or_create_cycle(new_cycle_name, None, None, set_cycle_id=True)
        assert self.seed_client.cycle_id == cycle_id

        # clean up the cycle
        self.seed_client.delete_cycle(cycle_id)

    def test_get_cycle_by_name(self):
        cycle = self.seed_client.create_cycle("test cycle for test_get_cycle_by_name", date(2021, 6, 1), date(2022, 6, 1))
        cycle_id = cycle["id"]
        assert cycle is not None

        cycle = self.seed_client.get_cycle_by_name("test cycle for test_get_cycle_by_name", set_cycle_id=True)
        assert cycle is not None
        assert cycle["name"] == "test cycle for test_get_cycle_by_name"
        assert self.seed_client.cycle_id == cycle_id

        # cleanup
        self.seed_client.delete_cycle(cycle_id)

    def test_get_or_create_dataset(self):
        dataset_name = "seed-salesforce-test-data"
        dataset = self.seed_client.get_or_create_dataset(dataset_name)
        assert dataset["name"] == dataset_name
        assert dataset["super_organization"] == self.seed_client.client.org_id
        assert dataset is not None

    def test_get_columns(self):
        result = self.seed_client.get_columns()
        assert result["status"] == "success"
        assert len(result["columns"]) >= 1

    def test_create_column(self):
        result = self.seed_client.create_extra_data_column(
            column_name="test_col",
            display_name="A Test Column",
            inventory_type="Property",
            column_description="this is a test column",
            data_type="string",
        )
        assert result["status"] == "success"
        assert "id" in result["column"]

    def test_create_columns_from_file(self):
        cols_filepath = "tests/data/test-seed-create-columns.csv"
        result = self.seed_client.create_extra_data_columns_from_file(cols_filepath)
        assert len(result)
        assert result[0]["status"]

    def test_get_column_mapping_profiles(self):
        result = self.seed_client.get_column_mapping_profiles()
        assert len(result) >= 1

        # There should only be one default BuildingSync mapping profile
        result = self.seed_client.get_column_mapping_profiles("BuildingSync Default")
        assert len(result) == 1

    def test_get_column_mapping_profile(self):
        result = self.seed_client.get_column_mapping_profile("does not exist")
        assert result is None

        # There should always be a portfolio manager default unless the
        # user removed it.
        result = self.seed_client.get_column_mapping_profile("Portfolio Manager Defaults")
        assert isinstance(result, dict)
        assert len(result["mappings"]) > 0

    def test_create_column_mapping_profile_with_file(self):
        profile_name = "new profile"
        result = self.seed_client.create_or_update_column_mapping_profile_from_file(profile_name, "tests/data/test-seed-data-mappings.csv")
        assert result is not None
        assert len(result["mappings"]) == 14

        # delete some of the mappings and update
        mappings = result["mappings"]
        for index in range(5, 0, -1):
            mappings.pop(index)
        result = self.seed_client.create_or_update_column_mapping_profile(profile_name, mappings)
        assert len(result["mappings"]) == 9

        # restore with the original call
        result = self.seed_client.create_or_update_column_mapping_profile_from_file(profile_name, "tests/data/test-seed-data-mappings.csv")
        assert len(result["mappings"]) == 14

    def test_get_labels(self):
        result = self.seed_client.get_labels()
        assert len(result) > 10

        # find a set of two labels
        result = self.seed_client.get_labels(filter_by_name=["Compliant", "Violation"])
        assert len(result) == 2

        # find single field
        result = self.seed_client.get_labels(filter_by_name=["Call"])
        assert len(result) == 1
        assert result[0]["name"] == "Call"
        assert not result[0]["show_in_list"]

        # find nothing field
        result = self.seed_client.get_labels(filter_by_name=["Does not Exist"])
        assert len(result) == 0

    def test_get_or_create_label(self):
        label_name = "something borrowed"
        label = self.seed_client.get_or_create_label(label_name, "green", show_in_list=True)
        label_id = label["id"]
        assert label is not None
        assert label["name"] == label_name

        # try running it again and make sure it doesn't create a new label (ID should be the same0)
        label = self.seed_client.get_or_create_label(label_name)
        assert label_id == label["id"]

        # now update the color
        label = self.seed_client.update_label(label_name, new_color="blue")
        assert label["color"] == "blue"

        # now update the name and show in list = False
        new_label_name = "something blue"
        label = self.seed_client.update_label(label_name, new_label_name=new_label_name, new_show_in_list=False)
        assert label["name"] == new_label_name

        # cleanup by deleting label
        label = self.seed_client.delete_label(new_label_name)
        # not the best response, but this means it passed
        assert label is None
