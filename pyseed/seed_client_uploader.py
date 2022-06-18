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
import logging
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import _NetlocResultMixinStr

# Local Imports
from pyseed import SEEDReadWriteClient
from pyseed.seed_client import SeedProperties
from pyseed.utils import read_map_file

logger = logging.getLogger(__name__)


class SeedUploader(SeedProperties):
    """Class for uploading data to SEED. It includes all of the SeedBuildings methods"""

    def __init__(self, organization_id: int, connection_params: dict = None, connection_config_filepath: Path = None) -> None:
        super().__init__(organization_id, connection_params, connection_config_filepath)

    def upload_and_match_datafile(self, dataset_name: str, datafile: str, column_mapping_profile_name: str, column_mappings_file: str, **kwargs) -> dict:
        """Upload a file to the cycle_id that is defined in the constructor. This carries the
        upload of the file through the whole ingestion process (map, merge, pair, geocode).

        Args:
            dataset_name (str): Name of the dataset to upload to
            datafile (str): Full path to the datafile to upload
            column_mapping_profile_name (str): Name of the column mapping profile to use
            column_mappings_file (str): Mapping that will be uploaded to the column_mapping_profile_name

        Returns:
            dict: {
                matching summary
            }
        """
        datafile_type = kwargs.pop('datafile_type', 'Assessed Raw')
        dataset = self.get_or_create_dataset(dataset_name)
        result = self.upload_datafile(
            dataset['id'],
            datafile,
            datafile_type
        )
        import_file_id = result['import_file_id']

        # start processing
        result = self.start_save_data(import_file_id)
        progress_key = result.get('progress_key', None)

        # wait until upload is complete
        result = self.track_progress_result(progress_key)

        # create/retrieve the column mappings
        result = self.create_or_update_column_mapping_profile_from_file(
            column_mapping_profile_name,
            column_mappings_file
        )

        # set the column mappings for the dataset
        result = self.set_import_file_column_mappings(import_file_id, result['mappings'])

        # now start the mapping
        result = self.start_map_data(import_file_id)
        progress_key = result.get('progress_key', None)

        # wait until upload is complete
        result = self.track_progress_result(progress_key)

        # save the mappings, call system matching/geocoding
        result = self.start_system_matching_and_geocoding(import_file_id)
        progress_data = result.get('progress_data', None)
        progress_key = progress_data.get('progress_key', None)

        # wait until upload is complete
        result = self.track_progress_result(progress_key)

        # return summary
        return self.get_matching_results(import_file_id)
