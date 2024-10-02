"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

import os
import unittest
from datetime import date
from pathlib import Path

import pytest

from pyseed.seed_client import SeedClient

# For CI the test org is 1, but for local testing it may be different
ORGANIZATION_ID = 1


@pytest.mark.integration
class SeedClientTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """setup for all of the tests below"""
        cls.output_dir = Path("tests/output")
        if not cls.output_dir.exists():
            cls.output_dir.mkdir()

        cls.organization_id = ORGANIZATION_ID

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path("seed-config.json")
        cls.seed_client = SeedClient(cls.organization_id, connection_config_filepath=config_file)

        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        cls.seed_client.get_or_create_cycle("pyseed-api-test", date(2021, 6, 1), date(2022, 6, 1), set_cycle_id=True)

        cls.seed_client.upload_and_match_datafile(
            "pyseed-properties-test",
            "tests/data/test-seed-data.xlsx",
            "Single Step Column Mappings",
            "tests/data/test-seed-data-mappings.csv",
        )

    @classmethod
    def teardown_class(cls):
        # remove all of the test buildings?
        pass

    def test_seed_orgs(self):
        orgs = self.seed_client.get_organizations()
        assert len(orgs) > 0

    def test_seed_client_info(self):
        info = self.seed_client.instance_information()
        assert set(("version", "sha")).issubset(info.keys())  # noqa: C405

    def test_create_organization(self):
        # create a new organization. This test requires that the
        # org does not already exist, which is common in the CI.
        org = self.seed_client.create_organization("NEW ORG")
        assert org["organization"]["id"] is not None

        # try to create again and it should raise an error
        with pytest.raises(Exception) as excpt:  # noqa: PT011
            self.seed_client.create_organization("NEW ORG")
        assert "already exists" in excpt.value.args[0]

    def test_seed_buildings(self):
        # set cycle before retrieving (just in case)
        self.seed_client.get_cycle_by_name("pyseed-api-test", set_cycle_id=True)
        buildings = self.seed_client.get_buildings()
        # ESPM test creates a building now too, assert building count is 10 or 11?
        assert len(buildings) == 10

    def test_get_pm_report_template_names(self):
        pm_un = os.environ.get("SEED_PM_UN", False)
        pm_pw = os.environ.get("SEED_PM_PW", False)
        if not pm_un or not pm_pw:
            self.fail(f"Somehow PM test was initiated without {pm_un} or {pm_pw} in the environment")
        response = self.seed_client.get_pm_report_template_names(pm_un, pm_pw)
        templates = response["templates"]
        # loop through the array templates and make a list of all the name keys
        template_names = []
        for template in templates:
            template_names.append(template["name"])
        assert isinstance(template_names, list)
        assert len(template_names) >= 17
        assert "BPS Workflow 2021" in template_names
        assert "AT Properties" in template_names
        # check that the status is success
        assert response["status"] == "success"

    def test_search_buildings(self):
        # set cycle
        self.seed_client.get_cycle_by_name("pyseed-api-test", set_cycle_id=True)
        properties = self.seed_client.search_buildings(identifier_exact="B-1")
        assert len(properties) == 1

        prop = self.seed_client.get_property(properties[0]["id"])
        assert prop["state"]["address_line_1"] == "111 Street Lane, Chicago, IL"
        assert prop["state"]["extra_data"]["EUI Target"] == 120

        # test the property view (same as previous, just less data). It
        # is recommended to use `get_property` instead.
        prop = self.seed_client.get_property_view(properties[0]["id"])
        assert prop["id"] == properties[0]["id"]
        assert prop["cycle"]["name"] == "pyseed-api-test"

        # There are 2 if filtering, because B-1 and B-10
        properties = self.seed_client.search_buildings(identifier_filter="B-1")
        assert len(properties) == 2

    def test_create_update_building(self):
        # create a new building (property, propertyState, propertyView)
        # Update the building
        completion_date = "02/02/2023"
        year = "2023"
        cycle = self.seed_client.get_or_create_cycle(
            "pyseed-api-integration-test",
            date(int(year), 1, 1),
            date(int(year), 12, 31),
            set_cycle_id=True,
        )

        state = {
            "organization_id": self.organization_id,
            "custom_id_1": "123456",
            "address_line_1": "123 Testing St",
            "city": "Beverly Hills",
            "state": "CA",
            "postal_code": "90210",
            "property_name": "Test Building",
            "property_type": None,
            "gross_floor_area": None,
            "conditioned_floor_area": None,
            "occupied_floor_area": None,
            "site_eui": None,
            "site_eui_modeled": None,
            "source_eui_weather_normalized": None,
            "source_eui": None,
            "source_eui_modeled": None,
            "site_eui_weather_normalized": None,
            "total_ghg_emissions": None,
            "total_marginal_ghg_emissions": None,
            "total_ghg_emissions_intensity": None,
            "total_marginal_ghg_emissions_intensity": None,
            "generation_date": None,
            "recent_sale_date": None,
            "release_date": None,
            "extra_data": {"pathway": "new", "completion_date": completion_date},
        }

        params = {"state": state, "cycle_id": cycle["id"]}

        result = self.seed_client.create_building(params=params)
        assert result["status"] == "success"
        assert result["view"]["id"] is not None
        view_id = result["view"]["id"]

        # update that property (by ID)
        state["property_name"] = "New Name Building"

        properties = self.seed_client.search_buildings(identifier_exact=state["custom_id_1"])
        assert len(properties) == 1

        params2 = {"state": state}
        result2 = self.seed_client.update_building(view_id, params=params2)
        assert result2["status"] == "success"

    def test_add_label_to_buildings(self):
        # get seed buildings
        prop_ids = []
        for search in ["B-1", "B-3", "B-7"]:
            properties = self.seed_client.search_buildings(identifier_exact=search)
            assert len(properties) == 1
            prop_ids.append(properties[0]["id"])

        result = self.seed_client.update_labels_of_buildings(["Violation"], [], prop_ids)
        assert result["status"] == "success"
        assert result["num_updated"] == 3
        # verify that the 3 buildings have the Violation label
        properties = self.seed_client.get_view_ids_with_label(label_names=["Violation"])
        assert all(item in properties[0]["is_applied"] for item in prop_ids)

        # now remove the violation label and add compliant
        result = self.seed_client.update_labels_of_buildings(["Compliant"], ["Violation"], prop_ids)
        assert result["status"] == "success"
        assert result["num_updated"] == 3
        properties = self.seed_client.get_view_ids_with_label(label_names=["Violation"])
        # should no longer have violation
        assert not all(item in properties[0]["is_applied"] for item in prop_ids)
        properties = self.seed_client.get_view_ids_with_label(label_names=["Compliant"])
        # should all have complied
        assert all(item in properties[0]["is_applied"] for item in prop_ids)

        # now remove all
        result = self.seed_client.update_labels_of_buildings([], ["Violation", "Compliant"], prop_ids)
        assert result["status"] == "success"
        assert result["num_updated"] == 3
        # no labels on the properties
        properties = self.seed_client.get_view_ids_with_label(label_names=["Compliant", "Violation"])
        assert not all(item in properties[0]["is_applied"] for item in prop_ids)
        assert not all(item in properties[1]["is_applied"] for item in prop_ids)

    def test_upload_datafile(self):
        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        self.seed_client.get_or_create_cycle(
            "pyseed-api-integration-test",
            date(2021, 6, 1),
            date(2022, 6, 1),
            set_cycle_id=True,
        )

        # Need to get the dataset id, again. Maybe need to clean up eventually.
        dataset = self.seed_client.get_or_create_dataset("pyseed-uploader-test-data")

        result = self.seed_client.upload_datafile(dataset["id"], "tests/data/test-seed-data.xlsx", "Assessed Raw")
        import_file_id = result["import_file_id"]
        assert result["success"] is True
        assert import_file_id is not None

        # start processing
        result = self.seed_client.start_save_data(result["import_file_id"])
        progress_key = result.get("progress_key", None)
        assert result is not None
        assert result["unique_id"] == import_file_id
        assert progress_key == f":1:SEED:save_raw_data:PROG:{import_file_id}"

        # wait until upload is complete
        result = self.seed_client.track_progress_result(progress_key)
        assert result["status"] == "success"
        assert result["progress"] == 100

        # create/retrieve the column mappings
        result = self.seed_client.create_or_update_column_mapping_profile_from_file("new profile", "tests/data/test-seed-data-mappings.csv")
        assert len(result["mappings"]) > 0

        # set the column mappings for the dataset
        result = self.seed_client.set_import_file_column_mappings(import_file_id, result["mappings"])

        # now start the mapping
        result = self.seed_client.start_map_data(import_file_id)
        progress_key = result.get("progress_key", None)
        assert result is not None
        assert result["status"] in ["not-started", "success"]
        assert progress_key == f":1:SEED:map_data:PROG:{import_file_id}"

        # wait until upload is complete
        result = self.seed_client.track_progress_result(progress_key)
        assert result["status"] == "success"
        assert result["progress"] == 100

        # save the mappings, call system matching/geocoding
        result = self.seed_client.start_system_matching_and_geocoding(import_file_id)
        progress_data = result.get("progress_data", None)
        assert progress_data is not None
        assert progress_data["status"] in ["not-started", "success", "parsing"]
        progress_key = progress_data.get("progress_key", None)
        assert progress_key == f":1:SEED:match_buildings:PROG:{import_file_id}"

        # wait until upload is complete
        result = self.seed_client.track_progress_result(progress_key)
        assert result["status"] == "success"
        assert result["progress"] == 100

        # check if there are meter fields (which there are not in this file)
        meters_exist = self.seed_client.check_meters_tab_exist(import_file_id)
        assert not meters_exist

    def test_upload_single_method(self):
        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        self.seed_client.get_or_create_cycle(
            "pyseed-single-file-upload",
            date(2021, 6, 1),
            date(2022, 6, 1),
            set_cycle_id=True,
        )

        result = self.seed_client.upload_and_match_datafile(
            "pyseed-single-step-test",
            "tests/data/test-seed-data.xlsx",
            "Single Step Column Mappings",
            "tests/data/test-seed-data-mappings.csv",
        )

        assert result is not None

        # test by listing all the buildings
        buildings = self.seed_client.get_buildings()
        assert len(buildings) == 10

    def test_upload_single_method_with_meters(self):
        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        self.seed_client.get_or_create_cycle(
            "pyseed-single-file-upload",
            date(2021, 6, 1),
            date(2022, 6, 1),
            set_cycle_id=True,
        )

        result = self.seed_client.upload_and_match_datafile(
            "pyseed-single-step-test",
            "tests/data/test-seed-data-with-meters.xlsx",
            "Single Step Column Mappings",
            "tests/data/test-seed-data-mappings.csv",
            import_meters_if_exist=True,
        )

        assert result is not None

        # test by listing all the buildings
        buildings = self.seed_client.get_buildings()
        assert len(buildings) == 10

        # look at the meters of a single building
        building = self.seed_client.search_buildings(identifier_exact=11111)
        assert len(building) == 1

        meters = self.seed_client.get_meters(building[0]["id"])
        assert len(meters) == 4  # elec, elec cost, gas, gas cost
        meter_data = self.seed_client.get_meter_data(building[0]["id"])
        assert len(meter_data["readings"]) == 24

    def test_download_espm_property(self):
        # For testing, read in the ESPM username and password from
        # environment variables.

        save_file = self.output_dir / "espm_test_22178850.xlsx"
        if save_file.exists():
            save_file.unlink()

        self.seed_client.retrieve_portfolio_manager_property(
            username=os.environ.get("SEED_PM_UN"),
            password=os.environ.get("SEED_PM_PW"),
            pm_property_id=22178850,
            save_file_name=save_file,
        )

        assert save_file.exists()

        # redownload and show an error
        with pytest.raises(Exception) as excpt:  # noqa: PT011
            self.seed_client.retrieve_portfolio_manager_property(
                username=os.environ.get("SEED_PM_UN"),
                password=os.environ.get("SEED_PM_PW"),
                pm_property_id=22178850,
                save_file_name=save_file,
            )

        assert excpt.value.args[0] == f"Save filename already exists, save to a new file name: {save_file!s}"

    def test_upload_espm_property_to_seed(self):
        file = Path("tests/data/portfolio-manager-single-22482007.xlsx")

        # need a building
        buildings = self.seed_client.get_buildings()
        building = None
        if buildings:
            building = buildings[0]
        assert building

        # need a column mapping profile
        mapping_file = Path("tests/data/test-seed-data-mappings.csv")
        mapping_profile = self.seed_client.create_or_update_column_mapping_profile_from_file("ESPM Test", mapping_file)
        assert "id" in mapping_profile

        response = self.seed_client.import_portfolio_manager_property(
            building["id"],
            self.seed_client.cycle_id,
            mapping_profile["id"],
            file,
        )
        assert response["status"] == "success"

    # def test_retrieve_at_building_and_update(self):
    #     # NOTE: commenting this out as we cannot set the AT credentials in SEED from py-seed

    #     # need a building
    #     buildings = self.seed_client.get_buildings()
    #     building = None
    #     if buildings:
    #         building = buildings[0]
    #     self.assertTrue(building)

    #     # need an Audit Template Building ID (use envvar for this)
    #     at_building_id=os.environ.get('SEED_AT_BUILDING_ID'),

    #     response = self.seed_client.retrieve_at_building_and_update(self, at_building_id, self.cycle_id, building['id'])
    #     self.assertTrue(response['status'] == 'success')


@pytest.mark.integration
class SeedClientMultiCycleTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """setup for all of the tests below"""
        cls.output_dir = Path("tests/output")
        if not cls.output_dir.exists():
            cls.output_dir.mkdir()

        # Use the default organization to create the client,
        # but this will be overwritten in the test class below.
        cls.organization_id = ORGANIZATION_ID

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path("seed-config.json")
        cls.seed_client = SeedClient(cls.organization_id, connection_config_filepath=config_file)

    @classmethod
    def teardown_class(cls):
        # remove all of the test buildings?
        pass

    def test_upload_multiple_cycles_and_read_back(self):
        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        new_org = self.seed_client.create_organization("pyseed-multi-cycle")
        self.seed_client.client.org_id = new_org["organization"]["id"]

        for year_start, year_end in [(2020, 2021), (2021, 2022), (2022, 2023)]:
            self.seed_client.get_or_create_cycle(
                f"pyseed-multi-cycle-test-{year_start}",
                date(year_start, 6, 1),
                date(year_end, 6, 1),
                set_cycle_id=True,
            )

        # due to structure of loop above, the cycle_id is set to the last cycle

        result = self.seed_client.upload_and_match_datafile(
            "pyseed-multiple-cycle-test",
            "tests/data/test-seed-data-with-multiple-cycles.xlsx",
            "Single Step Column Mappings",
            "tests/data/test-seed-data-mappings.csv",
            import_meters_if_exist=False,
            multiple_cycle_upload=True,
        )

        assert result is not None

        # retrieve the single building
        building = self.seed_client.search_buildings(identifier_exact=11111)
        assert len(building) == 1
        property_view_id = building[0]["id"]

        # retrieve cross cycle
        building_cycles = self.seed_client.get_cross_cycle_data(property_view_id)

        assert len(building_cycles) == 3
        # check that the site_euis are correct
        assert building_cycles[0]["site_eui"] == 95
        assert building_cycles[1]["site_eui"] == 181
        assert building_cycles[2]["site_eui"] == 129
