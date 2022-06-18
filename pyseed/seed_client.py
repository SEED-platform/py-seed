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

# Imports from Standard Library
from typing import Any, Dict, List, Optional, Set, Tuple

# Imports from Third Party Modules
import json
import logging
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import _NetlocResultMixinStr

# Local Imports
from pyseed.seed_client_base import SEEDReadWriteClient
from pyseed.utils import read_map_file

logger = logging.getLogger(__name__)


class SeedClient(object):
    """This is a wrapper around the SEEDReadWriteClient. If you need access
    to the READOnly client, or the OAuth client, then you will need to create another class"""

    def __init__(self, organization_id: int, connection_params: Optional[dict] = None, connection_config_filepath: Optional[Path] = None) -> None:
        """wrapper around SEEDReadWriteClient.

        Args:
            organization_id (int): _description_
            connection_params (dict, optional): parameters to connect to SEED. Defaults to None.
            connection_config_filepath (Path, optional): path to the parameters (JSON file). Defaults to None.

        Raises:
            Exception: SeedClient
        """
        if not connection_params and not connection_config_filepath:
            raise Exception("Must provide either connection_params or connection_config_filepath")

        # favor the connection params over the config file
        if connection_params:
            # the connetion params are simply squashed on SEEDReadWriteClient init
            payload = connection_params
        elif connection_config_filepath:
            payload = SeedClient.read_connection_config_file(connection_config_filepath)
            # read in from config file

        self.client = SEEDReadWriteClient(
            organization_id,
            **payload
        )

    @classmethod
    def read_connection_config_file(cls, filepath: Path) -> dict:
        """Read in the connection config file and return the connection params. This
        file can be mostly created by calling the following from the SEED root directory:

        ./manage.py create_test_user_json --username user@seed-platform.org --host http://localhost:80 --pyseed --file api_test_user.json

        Args:
            filepath (str): path to the connection config file
        """
        if not filepath.exists():
            raise Exception(f"Cannot find connection config file: {str(filepath)}")

        connection_params = json.load(open(filepath))
        return connection_params


class SeedProperties(SeedClient):
    """SEED Client with several property related
    helper methods implemented."""

    def __init__(self, organization_id: int, connection_params: dict = None, connection_config_filepath: Path = None) -> None:
        super().__init__(organization_id, connection_params, connection_config_filepath)

    def get_buildings(self) -> list:
        self.client.list(endpoint='properties', data_name='pagination', per_page=1)['total']
        buildings = self.client.list(endpoint='properties', data_name='results', per_page=100, cycle=self.cycle_id)

        # TODO: what to do with this if paginated?
        return buildings

    def search_buildings(self, identifier_filter: str = None, identifier_exact: str = None) -> dict:
        payload = {
            "cycle": self.cycle_id,
        }
        if identifier_filter is not None:
            payload["identifier"] = identifier_filter

        if identifier_exact is not None:
            payload["identifier_exact"] = identifier_exact

        properties = self.client.get(None, required_pk=False, endpoint='property_search', **payload)
        return properties

    def get_labels(self, filter_by_name: list = None) -> list:
        """Get a list of all the labels in the organization. Filter by name if desired.

        Args:
            filter_by_name (list, optional): List of subset of labels to return. Defaults to None.

        Returns:
            list: [
                {
                    'id': 8,
                    'name': 'Call',
                    'color': 'blue',
                    'organization_id': 1,
                    'show_in_list': False
                }, {
                    'id': 14,
                    'name': 'Change of Ownership',
                    'color': 'blue',
                    'organization_id': 1,
                    'show_in_list': False
                }, ...
            ]
        """
        labels = self.client.list(endpoint='labels')
        if filter_by_name is not None:
            labels = [label for label in labels if label['name'] in filter_by_name]
        return labels

    def get_or_create_label(self, label_name: str) -> dict:
        pass

    def update_label(self, label_id: int, label_name: str) -> dict:
        pass

    def get_view_ids_with_label(self, label_names: list = []) -> list:
        """Get the view IDs of the properties with a given label name.

        Note that with labels, the data.selected field is for property view ids! SEED was updated
        in June 2022 to add in the label_names to filter on.

        Args:
            label_names (list, optional): list of the labels to filter on. Defaults to [].

        Returns:
            list: list of labels and the views they are associated with
        """
        properties = self.client.post(
            endpoint='properties_labels',
            cycle=self.cycle_id,
            json={"label_names": label_names})
        return properties

    def update_labels_of_buildings(self, add_label_names: list, remove_label_names: list, building_ids: list, inventory_type: str = 'property') -> dict:
        """Add label names to the passed building ids.

        Args:
            add_label_names (list): list of label names to add, will be converted to IDs
            remove_label_names (list): list of label names to remove, will be converted to IDs
            building_ids (list): list of building IDs to add/remove labels
            inventory_type (str, optional): taxlot or property inventory. Defaults to 'property'.

        Raises:
            ValueError: if you don't pass the inventory type correction it will error out

        Returns:
            dict: {
                'status': 'success',
                'num_updated': 3,
                'labels': [
                    {'id': 3, 'color': 'blue', 'name': 'Violation'}
                    {'id': 16, 'color': 'green', 'name': 'Complied'}
                ]
            }
        """
        if inventory_type == 'property':
            endpoint = 'labels_property'
        elif inventory_type == 'tax_lot':
            endpoint = 'labels_taxlot'
        else:
            raise ValueError('inventory_type must be either property or tax_lot')

        # first make sure that the labels exist
        labels = self.client.list(endpoint='labels')
        # create a label id look up
        label_id_lookup = {label['name']: label['id'] for label in labels}

        # now find the IDs of the labels that we want to add and remove
        add_label_ids = []
        remove_label_ids = []
        for label_name in add_label_names:
            if label_name in label_id_lookup:
                add_label_ids.append(label_id_lookup[label_name])
            else:
                logger.warning(f'label name {label_name} not found in SEED, skipping')

        for label_name in remove_label_names:
            if label_name in label_id_lookup:
                remove_label_ids.append(label_id_lookup[label_name])
            else:
                logger.warning(f'label name {label_name} not found in SEED, skipping')

        payload = {
            "inventory_ids": building_ids,
            "add_label_ids": add_label_ids,
            "remove_label_ids": remove_label_ids,
        }
        result = self.client.put(None, required_pk=False, endpoint=endpoint, json=payload)
        return result

    def get_cycles(self) -> dict:
        """list all the existing cycles"""
        # first list the cycles
        cycles = self.client.list(endpoint='cycles')
        return cycles

    def create_cycle(self, cycle_name: str, start_date: date, end_date: date) -> dict:
        """Name of the cycle to create. If the cycle already exists, then it will
        create a new one. This is the default behavior of SEED.

        Args:
            cycle_name (str): Name of the cycle
            start_date (date): MM/DD/YYYY of start date cycle
            end_date (date): MM/DD/YYYY of end data for cycle

        Returns:
            dict: {
                'status': 'success',
                'cycles': {
                    'name': 'new cycle 351cd7e1',
                    'start': '2021-01-01T00:00:00-08:00',
                    'end': '2022-01-01T00:00:00-08:00',
                    'organization': 1,
                    'user': 1,
                    'id': 24
                    }
                }
        """
        post_data = {
            "name": cycle_name,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        }

        cycles = self.client.post(endpoint='cycles', json=post_data)
        return cycles

    def get_or_create_cycle(self, cycle_name: str, start_date: date, end_date: date, set_cycle_id: bool = False) -> dict:
        """Get or create a new cycle. If the cycle_name already exists, then it simply returns the existing cycle. However, if the cycle_name does not exist, then it will create a new cycle.

        Args:
            cycle_name (str): name of the cycle to get or create
            start_date (date): MM/DD/YYYY of start date cycle
            end_date (date): MM/DD/YYYY of end data for cycle
            set_cycle_id (str): Set the object's cycle_id to the resulting cycle that is returned (either   existing or newly created)

        Returns:
            dict: {
                'status': 'success',
                'cycles': {
                    'name': 'new cycle 351cd7e1',
                    'start': '2021-01-01T00:00:00-08:00',
                    'end': '2022-01-01T00:00:00-08:00',
                    'organization': 1,
                    'user': 1,
                    'id': 24
                    }
                }

        """
        cycles = self.get_cycles()

        # note that this picks the first one it finds, even if there are more
        # than one cycle with the name name
        cycle_names = [cycle['name'] for cycle in cycles['cycles']]
        counts = Counter(cycle_names)
        for i_cycle_name, count in counts.items():
            if count > 1:
                msg = f"More than one cycle named '{i_cycle_name}' exists [found {count}]. Using the first one."
                logger.warning(msg)
                print(msg)

        selected = None
        for cycle in cycles['cycles']:
            if cycle['name'] == cycle_name:
                selected = cycle
                break

        if selected is None:
            cycle = self.create_cycle(cycle_name, start_date, end_date)
            # only return the cycle portion of the response so that it
            # matches the result from the "already exists"-case
            selected = cycle['cycles']

        if set_cycle_id:
            self.cycle_id = selected['id']

        # to keep the response consistent add back in the status
        return {'status': 'success', 'cycles': selected}

    def delete_cycle(self, cycle_id: str) -> dict:
        """Delete the cycle. This will only work if there are no properties or tax lots in the cycle

        Args:
            cycle_id (str): ID of the cycle to delete

        Returns:
            dict:
        """
        return self.client.delete(cycle_id, endpoint='cycles')

    def get_or_create_dataset(self, dataset_name: str) -> dict:
        """Get or create a SEED dataset which is used to hold
        data files that are uploaded to SEED.

        Args:
            dataset_name (str): dataset name to get or create. Names can be duplicated!

        Returns:
            dict: resulting dataset record
        """
        post_data = {
            'name': dataset_name
        }
        selected = {}
        datasets = self.client.list(endpoint='datasets', data_name='datasets')
        for dataset in datasets:
            if dataset['name'] == dataset_name:
                logger.info(f"Dataset already created, returning {dataset['name']}")
                selected = dataset
                break

        # create a new dataset - this doesn't return the entire dict back
        # so after creating go and get the individual dataset
        dataset = self.client.post(endpoint='datasets', json=post_data)
        if dataset['status'] == 'success':
            selected = self.client.get(dataset['id'], endpoint='datasets', data_name='dataset')

        return selected

    def upload_datafile(self, dataset_id: int, data_file: str, upload_datatype: str) -> dict:
        """Upload a datafile file

        Args:
            dataset_id (int): id of the SEED dataset to where the data file will be saved
            data_file (str): full path to file
            upload_datatype (str): Type of data in file ('Assessed Raw', 'Portfolio Raw')

        Returns:
            dict: uploaded file record
                {
                    "import_file_id": 54,
                    "success": true,
                    "filename": "DataforSEED_dos15.csv"
                }
        """
        params = {
            'import_record': dataset_id,
            'source_type': upload_datatype,
        }

        files_params = [
            ('file', (Path(data_file).name, open(Path(data_file).resolve(), 'rb'))),
        ]

        return self.client.post(
            'upload',
            params=params,
            files=files_params,
        )

    def track_progress_result(self, progress_key) -> dict:
        """Delays the sequence until progress is at 100 percent

        Args:
            progress_key (str): the key to track

        Returns:
            dict: progress_result
                {
                    'status': 'success',
                    'status_message': '',
                    'progress': 100,
                    'progress_key': ':1:SEED:save_raw_data:PROG:57',
                    'unique_id': 57,
                    'func_name': 'save_raw_data',
                    'message': None,
                    'stacktrace': None,
                    'summary': None,
                    'total': 1
                }

        """
        if not progress_key:
            raise Exception('No progress key provided')
        try:
            progress_result = self.client.get(
                None, required_pk=False,
                endpoint='progress',
                url_args={'PROGRESS_KEY': progress_key}
            )
        except Exception:
            logger.error("Other unknown exception caught")
            progress_result = None

        if progress_result and progress_result['progress'] == 100:
            return progress_result
        else:
            # wait a couple seconds before checking the status again
            time.sleep(2)
            progress_result = self.track_progress_result(progress_key)

        return progress_result

    def get_column_mapping_profiles(self, profile_type: str = 'All') -> dict:
        """get the list of column mapping profiles. If profile_type is provided
        then return the list of profiles of that type.

        Args:
            profile_type (str, optional): Type of column mappings to return, can be 'Normal', 'BuildingSync Default'. Defaults to 'All', which includes both Normal and BuildingSync.

        Returns:
            dict: column mapping profiles
        """
        result = self.client.post(endpoint='column_mapping_profiles_filter')
        indices_to_remove = []
        for index, item in enumerate(result):
            if profile_type == 'All':
                continue
            elif item['profile_type'] != profile_type:
                indices_to_remove.append(index)

        # return only the unmarked indices
        if indices_to_remove:
            result = [item for index, item in enumerate(result) if index not in indices_to_remove]

        return result

    def get_column_mapping_profile(self, column_mapping_profile_name: str) -> Optional[dict]:
        """get a specific column mapping profile. Currently, filter does not take an
        argument by name, so return them all and find the one that matches the
        column_mapping_profile_name.

        Args:
            column_mapping_profile_name (str): Name of column_mapping_profile to return

        Returns:
            dict: single column mapping profile
        """
        results = self.client.post(endpoint='column_mapping_profiles_filter')
        for item in results:
            if item['name'] == column_mapping_profile_name:
                return item

        # if nothing, then return none
        return None

    def create_or_update_column_mapping_profile(self, mapping_profile_name: str, mappings: list) -> dict:
        """Create or update an existing mapping profile from a list of mappings

        This only works for 'Normal' column mapping profiles, that is, it does not work for
        BuildingSync column mapping profiles. Use this with caution since it will update
        an already existing profile if it is there.

        Args:
            mapping_profile_name (str): cription_
            mappings (list): list of mappings in the form of
                [
                    {
                        "from_field": "Address 1",
                        "from_units": null,
                        "to_table_name": "PropertyState"
                        "to_field": "address_line_1",
                    },
                    {
                        "from_field": "address1",
                        "from_units": null,
                        "to_table_name": "PropertyState"
                        "to_field": "address_line_1",
                    },
                    ...
                ]

        Returns:
            dict: {
                'id': 1
                'profile_type': 'Normal',
                'name': 'Profile Name',
                'mappings': [
                    ...
                ]
            }
        """
        # see if the column mapping profile already exists
        profile = self.get_column_mapping_profile(mapping_profile_name)
        result = None
        if not profile:
            # The profile doesn't exist, so create a new one. Note that seed does not
            # enforce uniqueness of the name, so we can use the same name for multiple
            # column mapping profiles (for better or worse)
            payload = {
                'name': mapping_profile_name,
                'mappings': mappings,
                'profile_type': 'Normal',
            }
            result = self.client.post(endpoint='column_mapping_profiles', json=payload)
        else:
            payload = {
                'mappings': mappings,
            }
            result = self.client.put(profile['id'], endpoint='column_mapping_profiles', json=payload)

        return result

    def create_or_update_column_mapping_profile_from_file(self, mapping_profile_name: str, mapping_file: str) -> dict:
        """creates or updates a mapping profile. The format of the mapping file is a CSV with the following format:

        # Raw Columns,    units, SEED Table,    SEED Columns
        # PM Property ID,      , PropertyState, pm_property_id
        # Building ID,         , PropertyState, custom_id_1
        # ...

        This only works for 'Normal' column mapping profiles, that is, it does not work for
        BuildingSync column mapping profiles. Use this with caution since it will update
        an already existing profile if it is there.

        Args:
            mapping_profile_name (str): _description_
            mapping_file (str): _description_

        Returns:
            dict: {
                'id': 1
                'profile_type': 'Normal',
                'name': 'Profile Name',
                'mappings': [
                    ...
                ]
            }
        """
        # grab the mappings from the file, then pass to the other method
        if not Path(mapping_file).exists():
            raise Exception("Could not find mapping file: {mapping_file}")

        return self.create_or_update_column_mapping_profile(
            mapping_profile_name, read_map_file(mapping_file)
        )

    def set_import_file_column_mappings(self, import_file_id: int, mappings: list) -> dict:
        """Sets the column mappings onto the import file record.

        Args:
            import_file_id (int): ID of the import file of interet
            mappings (list): list of column mappings in the form of the results of column mapping profiles

        Returns:
            dict: dict of status
        """
        return self.client.post(
            'org_column_mapping_import_file',
            url_args={'ORG_ID': self.client.org_id},
            params={'import_file_id': import_file_id},
            json={"mappings": mappings}
        )

    def start_save_data(self, import_file_id: int) -> dict:
        """start the background process to save the data file to the database.
        This is the state before the mapping.

        Args:
            import_file_id (int): id of the import file to save

        Returns:
            dict: progress key
                {
                    "status": "success",
                    "progress_key": ":1:SEED:start_save_data:PROG:90",
                    "unique_id": "90",
                }
        """
        return self.client.post(
            'import_files_start_save_data_pk',
            url_args={'PK': import_file_id},
            json={'cycle_id': self.cycle_id}
        )

    def start_map_data(self, import_file_id: int) -> dict:
        """start the background process to save the data file to the database.
        This is the state before the mapping.

        Args:
            import_file_id (int): id of the import file to save

        Returns:
            dict: progress key
                {
                    "status": "success",
                    "progress_key": ":1:SEED:map_data:PROG:90",
                    "unique_id": "90",
                }
        """
        return self.client.post(
            'import_files_start_map_data_pk',
            url_args={'PK': import_file_id},
            json={"remap": True},
        )

    def start_system_matching_and_geocoding(self, import_file_id: int) -> dict:
        """start the background process save mappings and start system matching/geocoding.
        This is the state after the mapping.

        Args:
            import_file_id (int): id of the import file to save

        Returns:
            dict: progress key
                {
                    "progress_data": {
                        "status": "success",
                        "status_message": "Pairing data",
                        "progress": 100,
                        "progress_key": ":1:SEED:match_buildings:PROG:106",
                        "unique_id": "106",
                        "func_name": "match_buildings",
                        "message": null,
                        "stacktrace": null,
                        "summary": null,
                        "total": 5
                    },
                    "sub_progress_data": {
                        "status": "not-started",
                        "status_message": "",
                        "progress": 0,
                        "progress_key": ":1:SEED:match_sub_progress:PROG:106",
                        "unique_id": "106",
                        "func_name": "match_sub_progress",
                        "message": null,
                        "stacktrace": null,
                        "summary": null,
                        "total": 100
                    }
                }
        """
        return self.client.post(
            'import_files_start_matching_pk',
            url_args={'PK': import_file_id}
        )

    def get_matching_results(self, import_file_id: int) -> dict:
        """matching results summary

        Args:
            import_file_id (int): ID of the import file

        Returns:
            dict: {
                'initial_incoming': 0,
                'duplicates_against_existing': 0,
                'duplicates_within_file': 0,
                'merges_against_existing': 0,
                'merges_between_existing': 0,
                'merges_within_file': 0,
                'new': 0,
                'geocoded_high_confidence': 0,
                'geocoded_low_confidence': 0,
                'geocoded_manually': 0,
                'geocode_not_possible': 0
            }
        """
        return self.client.get(None, required_pk=False, endpoint='import_files_matching_results', url_args={'PK': import_file_id})
