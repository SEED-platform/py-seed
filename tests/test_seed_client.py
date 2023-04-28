"""
****************************************************************************************************
:copyright (c) 2019-2022, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

Redistribution of this software, without modification, must refer to the software by the same
designation. Redistribution of a modified version of this software (i) may not refer to the
modified version by the same designation, or by any confusingly similar designation, and
(ii) must refer to the underlying software originally provided by Alliance as “URBANopt”. Except
to comply with the foregoing, the term “URBANopt”, or any confusingly similar designation may
not be used to refer to any modified version of this software or any modified version of the
underlying software originally provided by Alliance without the prior written consent of Alliance.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""

# Imports from Third Party Modules
import pytest
import unittest
from datetime import date
from pathlib import Path

# Local Imports
from pyseed.seed_client import SeedClient


@pytest.mark.integration
class SeedClientTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """setup for all of the tests below"""
        cls.output_dir = Path("tests/output")
        if not cls.output_dir.exists():
            cls.output_dir.mkdir()

        cls.organization_id = 1

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path("seed-config.json")
        cls.seed_client = SeedClient(
            cls.organization_id, connection_config_filepath=config_file
        )

        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        cls.seed_client.get_or_create_cycle(
            "pyseed-api-test", date(2021, 6, 1), date(2022, 6, 1), set_cycle_id=True
        )

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
        assert set(("version", "sha")).issubset(info.keys())

    def test_seed_buildings(self):
        buildings = self.seed_client.get_buildings()
        assert len(buildings) == 10

    def test_search_buildings(self):
        properties = self.seed_client.search_buildings(identifier_exact="B-1")
        assert len(properties) == 1

        prop = self.seed_client.get_property(properties[0]["id"])
        assert prop["state"]["address_line_1"] == "111 Street Lane, Chicago, IL"
        assert prop["state"]["extra_data"]["EUI Target"] == 120

        # test the property view (same as previous, just less data). It
        # is recommended to use `get_property` instead.
        prop = self.seed_client.get_property_view(properties[0]["id"])
        print(prop)
        assert prop["id"] == properties[0]["id"]
        assert prop["cycle"]["name"] == "pyseed-api-test"

        # There are 2 if filtering, because B-1 and B-10
        properties = self.seed_client.search_buildings(identifier_filter="B-1")
        assert len(properties) == 2

    def test_create_update_building(self):
        # create a new building (property, propertyState, propertyView)
        # Update the building
        completion_date = "02/02/2023"
        year = '2023'
        print(f" ORGANIZATION: {self.organization_id}")
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
            "extra_data": {
                "pathway": "new",
                "completion_date": completion_date
            }
        }

        params = {'state': state, 'cycle_id': cycle["id"]}

        result = self.seed_client.create_building(params=params)
        assert result["status"] == "success"
        assert result["view"]["id"] is not None
        view_id = result["view"]["id"]

        # update that property (by ID)
        state['property_name'] = 'New Name Building'

        properties = self.seed_client.search_buildings(identifier_exact=state['custom_id_1'])
        assert len(properties) == 1

        params2 = {'state': state}
        result2 = self.seed_client.update_building(view_id, params=params2)
        # print(f" !!! results2 are: {result2}")
        assert result2["status"] == "success"

    def test_add_label_to_buildings(self):
        # get seed buildings
        prop_ids = []
        for search in ["B-1", "B-3", "B-7"]:
            properties = self.seed_client.search_buildings(identifier_exact=search)
            assert len(properties) == 1
            prop_ids.append(properties[0]["id"])

        result = self.seed_client.update_labels_of_buildings(
            ["Violation"], [], prop_ids
        )
        assert result["status"] == "success"
        assert result["num_updated"] == 3
        # verify that the 3 buildings have the Violation label
        properties = self.seed_client.get_view_ids_with_label(label_names=["Violation"])
        assert all(item in properties[0]["is_applied"] for item in prop_ids)

        # now remove the violation label and add compliant
        result = self.seed_client.update_labels_of_buildings(
            ["Compliant"], ["Violation"], prop_ids
        )
        assert result["status"] == "success"
        assert result["num_updated"] == 3
        properties = self.seed_client.get_view_ids_with_label(label_names=["Violation"])
        # should no longer have violation
        assert not all(item in properties[0]["is_applied"] for item in prop_ids)
        properties = self.seed_client.get_view_ids_with_label(label_names=["Compliant"])
        # should all have complied
        assert all(item in properties[0]["is_applied"] for item in prop_ids)

        # now remove all
        result = self.seed_client.update_labels_of_buildings(
            [], ["Violation", "Compliant"], prop_ids
        )
        assert result["status"] == "success"
        assert result["num_updated"] == 3
        # no labels on the properties
        properties = self.seed_client.get_view_ids_with_label(
            label_names=["Compliant", "Violation"]
        )
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

        result = self.seed_client.upload_datafile(
            dataset["id"], "tests/data/test-seed-data.xlsx", "Assessed Raw"
        )
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
        result = self.seed_client.create_or_update_column_mapping_profile_from_file(
            "new profile", "tests/data/test-seed-data-mappings.csv"
        )
        assert len(result["mappings"]) > 0

        # set the column mappings for the dataset
        result = self.seed_client.set_import_file_column_mappings(
            import_file_id, result["mappings"]
        )

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
        assert len(meter_data['readings']) == 24

    # def test_get_buildings_with_labels(self):
    #     buildings = self.seed_client.get_view_ids_with_label(['In Violation', 'Compliant', 'Email'])
    #     for building in buildings:
    #         print(building)

    #     assert len(buildings) == 3
