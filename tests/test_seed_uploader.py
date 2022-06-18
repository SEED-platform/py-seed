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
import unittest
from datetime import date
from pathlib import Path

# Local Imports
from pyseed.seed_client_uploader import SeedUploader


class SeedUploaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.organization_id = 1

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path('seed-config.json')
        # The uploader inherits all the methods from SeedClient as well.
        self.uploader = SeedUploader(self.organization_id, connection_config_filepath=config_file)

        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        self.uploader.get_or_create_cycle(
            'pyseed-api-integration-test', date(2021, 6, 1), date(2022, 6, 1), set_cycle_id=True
        )

        return super().setUp()

    def test_upload_datafile(self):
        # Need to get the dataset id, again. Maybe need to clean up eventually.
        dataset = self.uploader.get_or_create_dataset('seed-salesforce-test-data')

        result = self.uploader.upload_datafile(
            dataset['id'],
            'tests/data/test-seed-data.xlsx',
            'Assessed Raw'
        )
        import_file_id = result['import_file_id']
        assert result['success'] is True
        assert import_file_id is not None

        # start processing
        result = self.uploader.start_save_data(result['import_file_id'])
        progress_key = result.get('progress_key', None)
        assert result is not None
        assert result['unique_id'] == import_file_id
        assert progress_key == f":1:SEED:save_raw_data:PROG:{import_file_id}"

        # wait until upload is complete
        result = self.uploader.track_progress_result(progress_key)
        assert result['status'] == 'success'
        assert result['progress'] == 100

        # create/retrieve the column mappings
        result = self.uploader.create_or_update_column_mapping_profile_from_file(
            'new profile',
            'tests/data/test-seed-data-mappings.csv'
        )
        assert len(result['mappings']) > 0

        # set the column mappings for the dataset
        result = self.uploader.set_import_file_column_mappings(import_file_id, result['mappings'])

        # now start the mapping
        result = self.uploader.start_map_data(import_file_id)
        progress_key = result.get('progress_key', None)
        assert result is not None
        assert result['status'] in ['not-started', 'success']
        assert progress_key == f":1:SEED:map_data:PROG:{import_file_id}"

        # wait until upload is complete
        result = self.uploader.track_progress_result(progress_key)
        assert result['status'] == 'success'
        assert result['progress'] == 100

        # save the mappings, call system matching/geocoding
        result = self.uploader.start_system_matching_and_geocoding(import_file_id)
        progress_data = result.get('progress_data', None)
        assert progress_data is not None
        assert progress_data['status'] in ['not-started', 'success']
        progress_key = progress_data.get('progress_key', None)
        assert progress_key == f":1:SEED:match_buildings:PROG:{import_file_id}"

        # wait until upload is complete
        result = self.uploader.track_progress_result(progress_key)
        assert result['status'] == 'success'
        assert result['progress'] == 100

    def test_upload_single_method(self):
        # Get/create the new cycle and upload the data. Make sure to set the cycle ID so that the
        # data end up in the correct cycle
        self.uploader.get_or_create_cycle('pyseed-single-file-upload', date(2021, 6, 1),
                                          date(2022, 6, 1), set_cycle_id=True)

        result = self.uploader.upload_and_match_datafile(
            'single-step-test',
            'tests/data/test-seed-data.xlsx',
            'Single Step Column Mappings',
            'tests/data/test-seed-data-mappings.csv')

        assert result is not None

        # test by listing all the buildings
        buildings = self.uploader.get_buildings()
        assert len(buildings) == 10
