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
from pyseed.seed_client import SeedProperties
from pyseed.seed_client_uploader import SeedUploader


@pytest.mark.integration
class SeedBuildingsTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """setup for all of the tests below"""
        cls.output_dir = Path('tests/output')
        if not cls.output_dir.exists():
            cls.output_dir.mkdir()

        cls.organization_id = 1

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path('seed-config.json')
        cls.seed_client = SeedProperties(cls.organization_id, connection_config_filepath=config_file)

        # Include the uploader to upload the buildings for testing
        uploader = SeedUploader(cls.organization_id, connection_config_filepath=config_file)

        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        cycle = uploader.get_or_create_cycle(
            'pyseed-api-test', date(2021, 6, 1), date(2022, 6, 1), set_cycle_id=True
        )
        # also set the seed_client to this cycle id
        cls.seed_client.cycle_id = cycle['cycles']['id']

        uploader.upload_and_match_datafile(
            'single-step-test',
            'tests/data/test-seed-data.xlsx',
            'Single Step Column Mappings',
            'tests/data/test-seed-data-mappings.csv')

    @classmethod
    def teardown_class(cls):
        # remove all of the test buildings?
        pass

    def test_seed_buildings(self):
        buildings = self.seed_client.get_buildings()
        # for building in buildings:
        #     print(building)
        assert len(buildings) == 10

    def test_search_buildings(self):
        properties = self.seed_client.search_buildings(identifier_exact='B-1')
        assert len(properties) == 1

        properties = self.seed_client.search_buildings(identifier_filter='B-1')
        assert len(properties) == 2

    def test_add_label_to_buildings(self):
        # get seed buildings
        prop_ids = []
        for search in ['B-1', 'B-3', 'B-7']:
            properties = self.seed_client.search_buildings(identifier_exact=search)
            assert len(properties) == 1
            prop_ids.append(properties[0]['id'])

        result = self.seed_client.update_labels_of_buildings(['Violation'], [], prop_ids)
        assert result['status'] == 'success'
        assert result['num_updated'] == 3
        # verify that the 3 buildings have the Violation label
        properties = self.seed_client.get_view_ids_with_label(label_names=['Violation'])
        assert all(item in properties[0]['is_applied'] for item in prop_ids)

        # now remove the violation label and add compliant
        result = self.seed_client.update_labels_of_buildings(['Compliant'], ['Violation'], prop_ids)
        assert result['status'] == 'success'
        assert result['num_updated'] == 3
        properties = self.seed_client.get_view_ids_with_label(label_names=['Violation'])
        # should no longer have violation
        assert not all(item in properties[0]['is_applied'] for item in prop_ids)
        properties = self.seed_client.get_view_ids_with_label(label_names=['Compliant'])
        # should all have complied
        assert all(item in properties[0]['is_applied'] for item in prop_ids)

        # now remove all
        result = self.seed_client.update_labels_of_buildings([], ['Violation', 'Compliant'], prop_ids)
        assert result['status'] == 'success'
        assert result['num_updated'] == 3
        # no labels on the properties
        properties = self.seed_client.get_view_ids_with_label(label_names=['Compliant', 'Violation'])
        assert not all(item in properties[0]['is_applied'] for item in prop_ids)
        assert not all(item in properties[1]['is_applied'] for item in prop_ids)

    # def test_get_buildings_with_labels(self):
    #     buildings = self.seed_client.get_view_ids_with_label(['In Violation', 'Compliant', 'Email'])
    #     for building in buildings:
    #         print(building)

    #     assert len(buildings) == 3
