"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

# Imports from Standard Library
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Imports from Third Party Modules
import json
import logging
import time
from collections import Counter
from csv import DictReader
from datetime import date
from pathlib import Path
from urllib.parse import _NetlocResultMixinStr

# Local Imports
from pyseed.seed_client_base import SEEDReadWriteClient
from pyseed.utils import read_map_file

logger = logging.getLogger(__name__)


class SeedClientWrapper(object):
    """This is a wrapper around the SEEDReadWriteClient. If you need access
    to the READOnly client, or the OAuth client, then you will need to create another class"""

    def __init__(
        self,
        organization_id: int,
        connection_params: Optional[dict] = None,
        connection_config_filepath: Optional[Path] = None,
    ) -> None:
        """wrapper around SEEDReadWriteClient.

        Args:
            organization_id (int): _description_
            connection_params (dict, optional): parameters to connect to SEED. Defaults to None. If using, then must contain the following:
                {
                    "name": "not used - can be any string",
                    "base_url": "http://127.0.0.1",
                    "username": "user@somedomain.com",
                    "api_key": "1b5ea1ee220c8628789c61d66253d90398e6ad03",
                    "port": 8000,
                    "use_ssl": false
                }
            connection_config_filepath (Path, optional): path to the parameters (JSON file). Defaults to None.

        Raises:
            Exception: SeedClientWrapper
        """
        if not connection_params and not connection_config_filepath:
            raise Exception(
                "Must provide either connection_params or connection_config_filepath"
            )

        # favor the connection params over the config file
        self.payload = {}
        if connection_params:
            # the connection params are simply squashed on SEEDReadWriteClient init
            self.payload = connection_params
        elif connection_config_filepath:
            self.payload = SeedClientWrapper.read_connection_config_file(
                connection_config_filepath
            )
            # read in from config file

        self.client = SEEDReadWriteClient(organization_id, **self.payload)

    @classmethod
    def read_connection_config_file(cls, filepath: Path) -> dict:
        """Read in the connection config file and return the connection params. This
        file can be mostly created by calling the following from the SEED root directory:

        ./manage.py create_test_user_json --username user@seed-platform.org --host http://localhost:80 --pyseed --file api_test_user.json

        Content must contain:
            {
                "name": "not used - can be any string",
                "base_url": "http://127.0.0.1",
                "username": "user@somedomain.com",
                "api_key": "1b5ea1ee220c8628789c61d66253d90398e6ad03",
                "port": 8000,
                "use_ssl": false,
                "seed_org_name": "test-org"
            }

        Args:
            filepath (str): path to the connection config file
        """
        if not filepath.exists():
            raise Exception(f"Cannot find connection config file: {str(filepath)}")

        connection_params = json.load(open(filepath))
        return connection_params


class SeedClient(SeedClientWrapper):
    """SEED Client with several property related
    helper methods implemented."""

    def __init__(
        self,
        organization_id: int,
        connection_params: dict = None,
        connection_config_filepath: Path = None,
    ) -> None:
        super().__init__(organization_id, connection_params, connection_config_filepath)

        # set org if you can
        if self.payload and self.payload.get('seed_org_name', None):
            self.get_org_by_name(self.payload['seed_org_name'], set_org_id=True)

    def get_org_id(self) -> int:
        """Return the org ID that is set"""
        return self.client.org_id

    def get_org_by_name(self, org_name: str, set_org_id: bool = False) -> dict:
        """Set the current organization by name.

        Args:
            org_name (str): name of the organization to set
            set_org_id (bool): set the org_id on the object for later use. Defaults to None.

        Returns:
            dict: {
                    org data
                }
        """
        orgs = self.get_organizations()
        for org in orgs:
            if org["name"] == org_name:
                if set_org_id:
                    self.client.org_id = org["id"]
                return org

        raise ValueError(f"Organization '{org_name}' not found")

    def instance_information(self) -> dict:
        """Return the instance information.

        Returns:
            dict: instance information
        """
        # http://localhost:8000/api/version/
        # add in URL to the SEED instance
        # add in username (but not the password/api key)
        info = self.client.get(None, required_pk=False, endpoint="version", data_name='all')
        info["host"] = self.client.base_url
        info["username"] = self.client.username
        return info

    def get_organizations(self, brief: bool = True) -> Dict:
        """Get a list organizations (that one is allowed to view)

        Args:
            brief (bool, optional): if True, then only return the organization id with some other basic info. Defaults to True.
        Returns:
            Dict: [
                {
                    "name": "test-org",
                    "org_id": 1,
                    "parent_id": null,
                    "is_parent": true,
                    "id": 1,
                    "user_role": "owner",
                    "display_decimal_places": 2
                },
                ...
            ]
        """
        orgs = self.client.list(
            endpoint="organizations",
            data_name="organizations",
            brief="true" if brief else "false",
        )
        return orgs

    def get_buildings(self) -> List[dict]:
        total_qry = self.client.list(endpoint="properties", data_name="pagination", per_page=100)

        # step through each page of the results
        buildings: List[dict] = []
        for i in range(1, total_qry['num_pages'] + 1):
            buildings = buildings + self.client.list(
                endpoint="properties",
                data_name="results",
                per_page=100,
                page=i,
                cycle=self.cycle_id,
            )
        # print(f"number of buildings retrieved: {len(buildings)}")

        return buildings

    def get_property_view(self, property_view_id: int) -> dict:
        """Return a single property (view and state) by the property view id. It is
        recommended to use the more verbose version of `get_property` below.

        Args:
            property_view_id (int): ID of the property to return. This is the ID that is in the URL http://SEED_URL/app/#/properties/{property_view_id} and resolves to {host}/api/v3/property_views/{property_view_id}

        Returns:
            dict: {
                'id': property_view_id,
                'state': {
                    'extra_data': {},
                },
                'measures': [],
                ...
            }
        """
        return self.client.get(
            property_view_id, endpoint="property_views", data_name="property_views"
        )

    def get_property(self, property_view_id: int) -> dict:
        """Return a single property by the property view id.

        Args:
            property__id (int): ID of the property to return. This is the ID that is in the URL http://SEED_URL/app/#/properties/{property_view_id}

        Returns:
            dict: {
                'state': {
                    'extra_data': {},
                },
                'cycle': {...},
                'property': {...},
                'labels': {...},
                'measures': {...}
                ...
            }
        """
        # NOTE: this seems to be the call that OEP uses (returns property and labels dictionaries)
        return self.client.get(
            property_view_id, endpoint="properties", data_name="properties"
        )

    def search_buildings(
        self, identifier_filter: str = None, identifier_exact: str = None, cycle_id: int = None
    ) -> dict:
        if not cycle_id:
            cycle_id = self.cycle_id
        payload: Dict[str, Any] = {
            "cycle": cycle_id,
        }
        if identifier_filter is not None:
            payload["identifier"] = identifier_filter

        if identifier_exact is not None:
            payload["identifier_exact"] = identifier_exact

        properties = self.client.get(
            None, required_pk=False, endpoint="properties_search", **payload
        )
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
        labels = self.client.list(endpoint="labels")
        if filter_by_name is not None:
            labels = [label for label in labels if label["name"] in filter_by_name]
        return labels

    def get_or_create_label(
        self, label_name: str, color: str = "blue", show_in_list: bool = False
    ) -> dict:
        """_summary_

        Args:
            label_name (str): Name of label. SEED enforces uniqueness of label names within an organization.
            color (str, optional): Default color of the label. Must be from red, blue, light blue, green, white, orange, gray. 'blue' is the default.
            show_in_list (bool, optional): If true, then the label is shown in the inventory list page as part of the column. Defaults to False.

        Returns:
            dict: {
                'id': 87,
                'name': 'label name',
                'color': 'green',
                'organization_id': 1,
                'show_in_list': true
            }
        """
        # First check if the label exists
        label = self.get_labels(filter_by_name=[label_name])
        if len(label) == 1:
            return label[0]

        payload = {"name": label_name, "color": color, "show_in_list": show_in_list}
        return self.client.post(endpoint="labels", json=payload)

    def update_label(
        self,
        label_name: str,
        new_label_name: str = None,
        new_color: str = None,
        new_show_in_list: bool = None,
    ) -> dict:
        """Update an existing label with the new_* fields. If the new_* fields are not provided, then the existing values are used.

        Args:
            label_name (str): Name of existing label. This is required and must match an existing label name for the organization
            new_label_name (str, optional): New name of the label. Defaults to None.
            new_color (str, optional): New color of the label. Must be from red, blue, light blue, green, white, orange, gray. Defaults to None
            new_show_in_list (bool, optional): New boolean on whether to show the label in the inventory list page. Defaults to None.

        Raises:
            Exception: If the label does not exist, then throw an error.

        Returns:
            dict: {
                'id': 87,
                'name': 'label name',
                'color': 'green',
                'organization_id': 1,
                'show_in_list': true
            }
        """
        # color (str, optional): Default color of the label. Must be from red, blue, light blue, green, white, orange, gray. 'blue' is the default.
        # get the existing label
        label = self.get_labels(filter_by_name=[label_name])
        if len(label) != 1:
            raise Exception(f"Could not find label to update of {label_name}")
        current_label = label[0]

        if new_label_name is not None:
            current_label["name"] = new_label_name

        if new_color is not None:
            current_label["color"] = new_color

        if new_show_in_list is not None:
            current_label["show_in_list"] = new_show_in_list

        # remove the org id from the json data
        current_label.pop("organization_id")

        return self.client.put(
            current_label["id"], endpoint="labels", json=current_label
        )

    def delete_label(self, label_name: str) -> dict:
        """Deletes an existing label. This method will look up the ID of the label to delete.

        Args:
            label_name (str): Name of the label to delete.

        Returns:
            dict: _description_
        """
        label = self.get_labels(filter_by_name=[label_name])
        if len(label) != 1:
            raise Exception(f"Could not find label to delete with name {label_name}")
        id = label[0]["id"]

        return self.client.delete(id, endpoint="labels")

    def get_view_ids_with_label(self, label_names: Union[str, list] = []) -> list:
        """Get the view IDs of the properties with a given label name(s). Can be a single
        label or a list of labels.

        Note that with labels, the data.selected field is for property view ids! SEED was updated
        in June 2022 to add in the label_names to filter on.

        Args:
            label_names (str, list, optional): list of the labels to filter on. Defaults to [].

        Returns:
            list: list of labels and the views they are associated with
        """
        # if the label_names is not a list, then make it one
        if not isinstance(label_names, list):
            label_names = [label_names]

        properties = self.client.post(
            endpoint="properties_labels",
            cycle=self.cycle_id,
            json={"label_names": label_names},
        )
        return properties

    def update_labels_of_buildings(
        self,
        add_label_names: list,
        remove_label_names: list,
        building_ids: list,
        inventory_type: str = "property",
    ) -> dict:
        """Add label names to the passed building ids.

        Args:
            add_label_names (list): list of label names to add, will be converted to IDs
            remove_label_names (list): list of label names to remove, will be converted to IDs
            building_ids (list): list of building IDs (property_view_id) to add/remove labels
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
        if inventory_type == "property":
            endpoint = "labels_property"
        elif inventory_type == "tax_lot":
            endpoint = "labels_taxlot"
        else:
            raise ValueError("inventory_type must be either property or tax_lot")

        # first make sure that the labels exist
        labels = self.client.list(endpoint="labels")
        # create a label id look up
        label_id_lookup = {label["name"]: label["id"] for label in labels}

        # now find the IDs of the labels that we want to add and remove
        add_label_ids = []
        remove_label_ids = []
        for label_name in add_label_names:
            if label_name in label_id_lookup:
                add_label_ids.append(label_id_lookup[label_name])
            else:
                logger.warning(f"label name {label_name} not found in SEED, skipping")

        for label_name in remove_label_names:
            if label_name in label_id_lookup:
                remove_label_ids.append(label_id_lookup[label_name])
            else:
                logger.warning(f"label name {label_name} not found in SEED, skipping")

        payload = {
            "inventory_ids": building_ids,
            "add_label_ids": add_label_ids,
            "remove_label_ids": remove_label_ids,
        }
        result = self.client.put(
            None, required_pk=False, endpoint=endpoint, json=payload
        )
        return result

    def create_building(self, params: dict) -> list:
        """
        Creates a building with unique ID (either pm_property_id or custom_id_1 for now)
        Expects params to contain a state dictionary and a cycle id
        Optionally pass in a cycle ID

        Returns the created property_view id
        """
        # first try matching on custom_id_1
        matching_id = params.get('state', {}).get('custom_id_1', None)

        if not matching_id:
            # then try on pm_property_id
            matching_id = params.get('state', {}).get('pm_property_id', None)

            if not matching_id:
                raise Exception(
                    "This property does not have a pm_property_id or a custom_id_1 for matching...cannot create."
                )

        cycle_id = params.get('cycle_id', None)
        # include appropriate cycle in search (if not using the default cycle set on the class)
        buildings = self.search_buildings(identifier_exact=matching_id, cycle_id=cycle_id)

        if len(buildings) > 0:
            raise Exception(
                "A property matching the provided matching ID (pm_property_id or custom_id_1) already exists."
            )

        results = self.client.post(endpoint="properties", json=params)
        return results

    def update_building(self, id, params: dict) -> list:
        """
        Updates a building's property_view
        Expects id and params to contain a state dictionary
        """
        results = self.client.put(id, endpoint="properties", json=params)
        return results

    def get_cycles(self) -> list:
        """Return a list of all the cycles for the organization.

        Returns:
            list: [
                {
                    'name': '2021 Calendar Year',
                    'start': '2020-12-31T23:53:00-08:00',
                    'end': '2021-12-31T23:53:00-08:00',
                    'organization': 1,
                    'user': None,
                    'id': 2
                },
                {
                    'name': '2023',
                    'start': '2023-01-01T00:00:00-08:00',
                    'end': '2023-12-31T00:00:00-08:00',
                    'organization': 1,
                    'user': 1,
                    'id': 3
                }
                ...
            ]
        """
        # first list the cycles
        cycles = self.client.list(endpoint="cycles")
        return cycles["cycles"]

    def create_cycle(self, cycle_name: str, start_date: date, end_date: date) -> dict:
        """Name of the cycle to create. If the cycle already exists, then it will
        create a new one. This is the default behavior of SEED.

        Args:
            cycle_name (str): Name of the cycle
            start_date (date): MM/DD/YYYY of start date cycle
            end_date (date): MM/DD/YYYY of end data for cycle

        Returns:
            dict: {
                    'name': 'new cycle 351cd7e1',
                    'start': '2021-01-01T00:00:00-08:00',
                    'end': '2022-01-01T00:00:00-08:00',
                    'organization': 1,
                    'user': 1,
                    'id': 24
                }
        """
        post_data = {
            "name": cycle_name,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        }

        # before creating, check if the name already exists. SEED allows the same name of cycles,
        # but we really shouldn't
        existing_cycles = self.get_cycles()
        for cycle in existing_cycles:
            if cycle["name"] == cycle_name:
                raise Exception(
                    f"A cycle with this name already exists: '{cycle_name}'"
                )

        cycles = self.client.post(endpoint="cycles", json=post_data)
        return cycles["cycles"]

    def get_or_create_cycle(
        self,
        cycle_name: str,
        start_date: date,
        end_date: date,
        set_cycle_id: bool = False,
    ) -> dict:
        """Get or create a new cycle. If the cycle_name already exists, then it simply returns the existing cycle. However, if the cycle_name does not exist, then it will create a new cycle.

        Args:
            cycle_name (str): name of the cycle to get or create
            start_date (date): MM/DD/YYYY of start date cycle
            end_date (date): MM/DD/YYYY of end data for cycle
            set_cycle_id (str): Set the object's cycle_id to the resulting cycle that is returned (either   existing or newly created)

        Returns:
            dict: {
                    'name': 'Calendar Year 2022',
                    'start': '2021-01-01T00:00:00-08:00',
                    'end': '2022-01-01T00:00:00-08:00',
                    'organization': 1,
                    'user': 1,
                    'id': 24
                }
        """
        cycles = self.get_cycles()

        # force the name of the cycle to be a string!
        cycle_name = str(cycle_name)

        # note that this picks the first one it finds, even if there are more
        # than one cycle with the same name
        cycle_names = [cycle["name"] for cycle in cycles]
        counts = Counter(cycle_names)
        for i_cycle_name, count in counts.items():
            if count > 1:
                msg = f"More than one cycle named '{i_cycle_name}' exists [found {count}]. Using the first one."
                logger.warning(msg)
                print(msg)

        selected = None
        for cycle in cycles:
            if cycle["name"] == cycle_name:
                selected = cycle
                break

        if selected is None:
            cycle = self.create_cycle(cycle_name, start_date, end_date)
            # only return the cycle portion of the response so that it
            # matches the result from the "already exists"-case
            selected = cycle

        if set_cycle_id:
            self.cycle_id = selected["id"]

        # to keep the response consistent add back in the status
        return selected

    def get_cycle_by_name(self, cycle_name: str, set_cycle_id: bool = None) -> dict:
        """Set the current cycle by name.

        Args:
            cycle_name (str): name of the cycle to set
            set_cycle_id (bool): set the cycle_id on the object for later use. Defaults to None.

        Returns:
            dict: {
                        'name': 'Calendar Year 2022',
                        'start': '2021-01-01T00:00:00-08:00',
                        'end': '2022-01-01T00:00:00-08:00',
                        'organization': 1,
                        'user': 1,
                        'id': 24
                }
        """
        cycles = self.get_cycles()
        for cycle in cycles:
            if cycle["name"] == cycle_name:
                if set_cycle_id:
                    self.cycle_id = cycle["id"]
                return cycle

        raise ValueError(f"cycle '{cycle_name}' not found")

    def delete_cycle(self, cycle_id: str) -> dict:
        """Delete the cycle. This will only work if there are no properties or tax lots in the cycle

        Args:
            cycle_id (str): ID of the cycle to delete

        Returns:
            dict:
        """
        result = self.client.delete(cycle_id, endpoint="cycles")
        progress_key = result.get("progress_key", None)

        # wait until delete is complete
        result = self.track_progress_result(progress_key)

        return result

    def get_or_create_dataset(self, dataset_name: str) -> dict:
        """Get or create a SEED dataset which is used to hold
        data files that are uploaded to SEED.

        Args:
            dataset_name (str): dataset name to get or create. Names can be duplicated!

        Returns:
            dict: resulting dataset record
        """
        post_data = {"name": dataset_name}

        datasets = self.client.list(endpoint="datasets", data_name="datasets")
        for dataset in datasets:
            if dataset["name"] == dataset_name:
                logger.info(f"Dataset already created, returning {dataset['name']}")
                return dataset

        # create a new dataset - this doesn't return the entire dict back
        # so after creating go and get the individual dataset
        dataset = self.client.post(endpoint="datasets", json=post_data)
        selected = {}
        if dataset["status"] == "success":
            selected = self.client.get(
                dataset["id"], endpoint="datasets", data_name="dataset"
            )
        return selected

    def upload_datafile(
        self, dataset_id: int, data_file: str, upload_datatype: str
    ) -> dict:
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
                    "filename": "data_for_seed.csv"
                }
        """
        params = {
            "import_record": dataset_id,
            "source_type": upload_datatype,
        }

        files_params = [
            ("file", (Path(data_file).name, open(Path(data_file).resolve(), "rb"))),
        ]

        return self.client.post(
            "upload",
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
                    'status': 'success',  # 'not_started', 'in_progress', 'parsing', 'success', 'error'
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
            raise Exception("No progress key provided")
        try:
            progress_result = self.client.get(
                None,
                required_pk=False,
                endpoint="progress",
                url_args={"PROGRESS_KEY": progress_key},
            )
        except Exception:
            logger.error("Other unknown exception caught")
            progress_result = None

        if progress_result and progress_result["progress"] == 100:
            return progress_result
        else:
            # wait a couple seconds before checking the status again
            time.sleep(2)
            progress_result = self.track_progress_result(progress_key)

        return progress_result

    def get_column_mapping_profiles(self, profile_type: str = "All") -> dict:
        """get the list of column mapping profiles. If profile_type is provided
        then return the list of profiles of that type.

        Args:
            profile_type (str, optional): Type of column mappings to return, can be 'Normal', 'BuildingSync Default'. Defaults to 'All', which includes both Normal and BuildingSync.

        Returns:
            dict: column mapping profiles
        """
        result = self.client.post(endpoint="column_mapping_profiles_filter")
        indices_to_remove = []
        for index, item in enumerate(result):
            if profile_type == "All":
                continue
            elif item["profile_type"] != profile_type:
                indices_to_remove.append(index)

        # return only the unmarked indices
        if indices_to_remove:
            result = [
                item
                for index, item in enumerate(result)
                if index not in indices_to_remove
            ]

        return result

    def get_column_mapping_profile(
        self, column_mapping_profile_name: str
    ) -> Optional[dict]:
        """get a specific column mapping profile. Currently, filter does not take an
        argument by name, so return them all and find the one that matches the
        column_mapping_profile_name.

        Args:
            column_mapping_profile_name (str): Name of column_mapping_profile to return

        Returns:
            dict: single column mapping profile
        """
        results = self.client.post(endpoint="column_mapping_profiles_filter")
        for item in results:
            if item["name"] == column_mapping_profile_name:
                return item

        # if nothing, then return none
        return None

    def create_or_update_column_mapping_profile(
        self, mapping_profile_name: str, mappings: list
    ) -> dict:
        """Create or update an existing mapping profile from a list of mappings

        This only works for 'Normal' column mapping profiles, that is, it does not work for
        BuildingSync column mapping profiles. Use this with caution since it will update
        an already existing profile if it is there.

        Args:
            mapping_profile_name (str): profile name
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
                "name": mapping_profile_name,
                "mappings": mappings,
                "profile_type": "Normal",
            }
            result = self.client.post(endpoint="column_mapping_profiles", json=payload)
        else:
            payload = {
                "mappings": mappings,
            }
            result = self.client.put(
                profile["id"], endpoint="column_mapping_profiles", json=payload
            )

        return result

    def create_or_update_column_mapping_profile_from_file(
        self, mapping_profile_name: str, mapping_file: str
    ) -> dict:
        """creates or updates a mapping profile. The format of the mapping file is a CSV with the following format:

            Raw Columns,    units, SEED Table,    SEED Columns\n
            PM Property ID,      , PropertyState, pm_property_id\n
            Building ID,         , PropertyState, custom_id_1\n
            ...\n

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
            raise Exception(f"Could not find mapping file: {mapping_file}")

        return self.create_or_update_column_mapping_profile(
            mapping_profile_name, read_map_file(mapping_file)
        )

    def set_import_file_column_mappings(
        self, import_file_id: int, mappings: list
    ) -> dict:
        """Sets the column mappings onto the import file record.

        Args:
            import_file_id (int): ID of the import file of interest
            mappings (list): list of column mappings in the form of the results of column mapping profiles

        Returns:
            dict: dict of status
        """
        return self.client.post(
            "org_column_mapping_import_file",
            url_args={"ORG_ID": self.client.org_id},
            params={"import_file_id": import_file_id},
            json={"mappings": mappings},
        )

    def get_columns(self) -> dict:
        """get the list of columns.

        Returns:
            dict: {
                    "status": "success",
                    "columns: [{...}]
                  }
        """
        result = self.client.list(endpoint="columns")
        return result

    def create_extra_data_column(self, column_name: str, display_name: str, inventory_type: str, column_description: str, data_type: str) -> dict:
        """ create an extra data column. If column exists, skip
        Args:
            'column_name': 'project_type',
            'display_name': 'Project Type',
            'inventory_type': 'Property' or 'Taxlot',
            'column_description': 'Project Type (New or Retrofit)',
            'data_type': 'string',

        Returns:
            dict:{
                    "status": "success",
                    "column": {
                      "id": 151,
                      "name": "project_type_151",
                        ...
                    }
                  }
        """

        # get extra data columns (only)
        result = self.client.list(endpoint="columns")
        columns = result['columns']
        extra_data_cols = [item for item in columns if item['is_extra_data']]

        # see if extra data column already exists (for now don't update it, just skip it)
        res = list(filter(lambda extra_data_cols: extra_data_cols['column_name'] == column_name, extra_data_cols))
        if res:
            # column already exists
            result = {"status": "noop", "message": "column already exists"}
        else:
            # create
            payload = {
                "column_name": column_name,
                "display_name": display_name,
                "table_name": "PropertyState" if inventory_type == "Property" else "TaxlotState",
                "column_description": column_description,
                "data_type": data_type,
                "organization_id": self.get_org_id()
            }
            result = self.client.post(endpoint="columns", json=payload)

        return result

    def create_extra_data_columns_from_file(self, columns_csv_filepath: str) -> list:
        """ create extra data columns from a csv file. if column exist, skip.
        Args:
            'columns_csv_filepath': 'path/to/file'
            file is expected to have headers: column_name, display_name, column_description,
            inventory_type (Property or Taxlot), and data_type (SEED column data_types)

            See example file at tests/data/test-seed-create-columns.csv

        Returns:
            list:[{
                    "status": "success",
                    "column": {
                      "id": 151,
                      "name": "project_type_151",
                        ...
                    }
                  }]
        """
        # open file in read mode
        with open(columns_csv_filepath, 'r') as f:
            dict_reader = DictReader(f)
            columns = list(dict_reader)

        results = []
        for col in columns:
            result = self.create_extra_data_column(**col)
            results.append(result)

        return results

    def get_meters(self, property_id: int) -> list:
        """Return the list of meters assigned to a property (the property view id).
        Note that meters are attached to the property (not the state nor the property view).

        Args:
            property_id (int): property id to get the meters

        Returns:
            dict: [
                {
                    'id': 584,
                    'type': 'Cost',
                    'source': 'PM',
                    'source_id': '1',
                    'scenario_id': None,
                    'scenario_name': None
                },
                ...
            ]
        """
        meters = self.client.get(None, required_pk=False, endpoint='properties_meters',
                                 url_args={"PK": property_id})
        return meters

    def get_meter(self, property_view_id: int, meter_type: str, source: str, source_id: str) -> Union[dict, None]:
        """get a meter for a property view.

        Args:
            property_view_id (int): property view id
            meter_type (str): Type of meter, based off the enums in the SEED Meter model
            source (str): Of GreenButton, Portfolio Manager, or Custom Meter
            source_id (str): Identifier, if GreenButton, then format is xpath like

        Returns:
            dict: meter object
        """
        # return all the meters for the property and see if the meter exists, if so, return it
        meters = self.get_meters(property_view_id)
        for meter in meters:
            if meter['type'] == meter_type and meter['source'] == source and meter['source_id'] == source_id:
                return meter
        else:
            return None

    def get_or_create_meter(self, property_view_id: int, meter_type: str, source: str, source_id: str) -> Optional[Dict[Any, Any]]:
        """get or create a meter for a property view.

        Args:
            property_view_id (int): property view id
            meter_type (str): Type of meter, based off the enums in the SEED Meter model
            source (str): Of GreenButton, Portfolio Manager, or Custom Meter
            source_id (str): Identifier, if GreenButton, then format is xpath like

        Returns:
            dict: meter object
        """
        # return all the meters for the property and see if the meter exists, if so, return it
        meter = self.get_meter(property_view_id, meter_type, source, source_id)
        if meter:
            return meter
        else:
            # create the meter
            payload = {
                'type': meter_type,
                'source': source,
                'source_id': source_id,
            }

            meter = self.client.post(
                endpoint='properties_meters', url_args={"PK": property_view_id}, json=payload
            )

            return meter

    def delete_meter(self, property_view_id: int, meter_id: int) -> dict:
        """Delete a meter from the property.

        Args:
            property_view_id (int): property view id
            meter_id (int): meter id

        Returns:
            dict: status of the deletion
        """
        return self.client.delete(
            meter_id, endpoint='properties_meters', url_args={"PK": property_view_id}
        )

    def upsert_meter_readings_bulk(self, property_view_id: int, meter_id: int, data: list) -> dict:
        """Upsert meter readings for a property's meter with the bulk method.

        Args:
            property_view_id (int): property view id
            meter_id (int): meter id
            data (list): list of dictionaries of meter readings

        Returns:
            dict: list of all meter reading objects
        """
        # get the meter data for the property
        readings = self.client.post(
            endpoint='properties_meters_reading', url_args={"PK": property_view_id, "METER_PK": meter_id}, json=data
        )
        return readings

    def get_meter_data(self, property_id, interval: str = 'Exact', excluded_meter_ids: list = []):
        """Return the meter data from the property.

        Args:
            property_id (_type_): property view id
            interval (str, optional): How to aggregate the data, can be 'Exact', 'Month', or 'Year'. Defaults to 'Exact'.
            excluded_meter_ids (list, optional): IDs to exclude. Defaults to []].
        """
        payload = {
            "interval": interval,
            "excluded_meter_ids": excluded_meter_ids,
        }
        meter_data = self.client.post(endpoint='properties_meter_usage', url_args={"PK": property_id}, json=payload)
        return meter_data

    def save_meter_data(self, property_id: int, meter_id: int, meter_data) -> dict:
        pass

    def start_save_data(self, import_file_id: int, multiple_cycle_upload: bool = False) -> dict:
        """start the background process to save the data file to the database.
        This is the state before the mapping.

        Args:
            import_file_id (int): id of the import file to save
            multiple_cycle_upload (bool): whether to use multiple cycle upload

        Returns:
            dict: progress key
                {
                    "status": "success",
                    "progress_key": ":1:SEED:start_save_data:PROG:90",
                    "unique_id": "90",
                }
        """
        return self.client.post(
            "import_files_start_save_data_pk",
            url_args={"PK": import_file_id},
            json={"cycle_id": self.cycle_id,
                  "multiple_cycle_upload": multiple_cycle_upload},
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
            "import_files_start_map_data_pk",
            url_args={"PK": import_file_id},
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
            "import_files_start_matching_pk", url_args={"PK": import_file_id}
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
        return self.client.get(
            None,
            required_pk=False,
            endpoint="import_files_matching_results",
            url_args={"PK": import_file_id},
        )

    def check_meters_tab_exist(self, import_file_id: int) -> bool:
        """Check if the imported file has a meter and meter readings tab. If so
        this tab can be used to import meter data into SEED.

        Args:
            import_file_id (int): ID of the import file to check

        Returns: bool
        """
        response = self.client.get(
            None,
            required_pk=False,
            endpoint="import_files_check_meters_tab_exists_pk",
            url_args={"PK": import_file_id},
        )
        # if the data is set to True, then return such
        return response

    def import_files_reuse_inventory_file_for_meters(self, import_file_id: int) -> dict:
        """Reuse an import file to create all the meter entries. This method is used
        for ESPM related data files. The result will be another import_file ID for the
        meters that will then need to be "re-saved". Note that the returning import_file_id
        is not the same as the argument import file.

        Args:
            import_file_id (int): ID of the import file to reuse.

        Returns:
            dict: {
              "status": "success",
              "import_file_id": 16
            }
        """
        payload = {"import_file_id": import_file_id}
        response = self.client.post(
            endpoint="import_files_reuse_inventory_file_for_meters", json=payload
        )
        return response

    def upload_and_match_datafile(
        self,
        dataset_name: str,
        datafile: str,
        column_mapping_profile_name: str,
        column_mappings_file: str,
        import_meters_if_exist: bool = False,
        **kwargs,
    ) -> dict:
        """Upload a file to the cycle_id that is defined in the constructor. This carries the
        upload of the file through the whole ingestion process (map, merge, pair, geocode).

        Args:
            dataset_name (str): Name of the dataset to upload to
            datafile (str): Full path to the datafile to upload
            column_mapping_profile_name (str): Name of the column mapping profile to use
            column_mappings_file (str): Mapping that will be uploaded to the column_mapping_profile_name
            import_meters_if_exist (bool): If true, will import meters from the meter tab if they exist in the datafile. Defaults to False.
            multiple_cycle_upload (bool): Whether to use multiple cycle upload. Defaults to False.

        Returns:
            dict: {
                matching summary
            }
        """
        datafile_type = kwargs.pop("datafile_type", "Assessed Raw")
        dataset = self.get_or_create_dataset(dataset_name)
        result = self.upload_datafile(dataset["id"], datafile, datafile_type)
        import_file_id = result["import_file_id"]
        multiple_cycle_upload = kwargs.pop("multiple_cycle_upload", False)

        # start processing
        result = self.start_save_data(import_file_id, multiple_cycle_upload)
        progress_key = result.get("progress_key", None)

        # wait until upload is complete
        result = self.track_progress_result(progress_key)

        # create/retrieve the column mappings
        result = self.create_or_update_column_mapping_profile_from_file(
            column_mapping_profile_name, column_mappings_file
        )

        # set the column mappings for the dataset
        result = self.set_import_file_column_mappings(
            import_file_id, result["mappings"]
        )

        # now start the mapping
        result = self.start_map_data(import_file_id)
        progress_key = result.get("progress_key", None)

        # wait until upload is complete
        result = self.track_progress_result(progress_key)

        # save the mappings, call system matching/geocoding
        result = self.start_system_matching_and_geocoding(import_file_id)
        progress_data = result.get("progress_data", None)
        progress_key = progress_data.get("progress_key", None)

        # wait until upload is complete
        result = self.track_progress_result(progress_key)

        # return summary
        matching_results = self.get_matching_results(import_file_id)

        # check if we need to import meters and if they exist
        if import_meters_if_exist and self.check_meters_tab_exist(import_file_id):
            reuse_file = self.import_files_reuse_inventory_file_for_meters(
                import_file_id
            )

            meter_import_file_id = reuse_file["import_file_id"]

            result = self.start_save_data(meter_import_file_id)
            progress_key = result.get("progress_key", None)

            # wait until upload is complete
            result = self.track_progress_result(progress_key)

        return matching_results

    def retrieve_at_building_and_update(self, audit_template_building_id: int, cycle_id: int, seed_id: int) -> dict:
        """Connect to audit template and retrieve audit XML by building ID

        Args:
            audit_template_building_id (int): ID of the building in the audit template
            cycle_id (int): Cycle ID in SEED
            seed_id (int): PropertyView ID in SEED

        Returns:
            dict: Response from the SEED API
        """

        # api/v3/audit_template/pk/get_building_xml
        response = self.client.get(
            None,
            required_pk=False,
            endpoint="audit_template_building_xml",
            url_args={"PK": audit_template_building_id}
        )

        if response['status'] == 'success':
            # now post to api/v3/properties/PK/update_with_buildingsync
            xml_file = response['content']
            filename = 'at_' + str(int(time.time() * 1000)) + '.xml'
            files = [
                ('file', (filename, xml_file)),
                ('file_type', (None, 1))
            ]

            response = self.client.put(
                None,
                required_pk=False,
                endpoint="properties_update_with_buildingsync",
                url_args={"PK": seed_id},
                files=files,
                cycle_id=cycle_id
            )

        return response

    def retrieve_at_submission_and_update(self, audit_template_submission_id: int, cycle_id: int, seed_id: int, report_format: str = 'pdf', filename: str = None) -> dict:
        """Connect to audit template and retrieve audit report by submission ID

        Args:
            audit_template_submission_id (int): ID of the AT submission report (different than building ID)
            cycle_id (int): Cycle ID in SEED (needed for XML but not actually for PDF)
            seed_id (int): PropertyView ID in SEED
            file_format (str): pdf or xml report, defaults to pdf
            filename (str): filename to use to upload to SEED

        Returns:
            dict: Response from the SEED API
            including the PDF file (if that format was requested)
        """

        # api/v3/audit_template/pk/get_submission
        # accepts pdf or xml
        response = self.client.get(
            None,
            required_pk=False,
            endpoint="audit_template_submission",
            url_args={"PK": audit_template_submission_id},
            report_format=report_format
        )

        if response['status'] == 'success':
            if report_format.lower() == 'pdf':
                pdf_file = response['content']
                if not filename:
                    filename = 'at_submission_report_' + str(audit_template_submission_id) + '.pdf'
                files = [
                    ('file', (filename, pdf_file)),
                    ('file_type', (None, 1))
                ]
                response2 = self.client.put(
                    None,
                    required_pk=False,
                    endpoint="properties_upload_inventory_document",
                    url_args={"PK": seed_id},
                    files=files
                )
                response2['pdf_report'] = pdf_file
            else:
                # assume XML
                # now post to api/v3/properties/PK/update_with_buildingsync
                xml_file = response['content']
                if not filename:
                    filename = 'at_' + str(int(time.time() * 1000)) + '.xml'

                files = [
                    ('file', (filename, xml_file)),
                    ('file_type', (None, 1))
                ]

                response2 = self.client.put(
                    None,
                    required_pk=False,
                    endpoint="properties_update_with_buildingsync",
                    url_args={"PK": seed_id},
                    files=files,
                    cycle_id=cycle_id
                )

        return response2

    def retrieve_portfolio_manager_property(self, username: str, password: str, pm_property_id: int, save_file_name: Path) -> dict:
        """Connect to portfolio manager and download an individual properties data in Excel format

        Args:
            username (str): ESPM login username
            password (str): ESPM password
            pm_property_id (int): ESPM ID of the property to download
            save_file_name (Path): Location to save the file, preferably an absolute path

        Returns:
            bool: Did the file download?
        """
        if save_file_name.exists():
            raise Exception(f"Save filename already exists, save to a new file name: {save_file_name}")

        response = self.client.post(
            "portfolio_manager_property_download",
            json={"username": username, "password": password},
            url_args={"PK": pm_property_id}
        )
        result = {'status': 'error'}
        # save the file to the location that was passed
        # note that the data are returned directly (the ESPM URL directly downloads the file)
        if isinstance(response, bytes):
            with open(save_file_name, 'wb') as f:
                f.write(response)
                result['status'] = 'success'
        return result

    def import_portfolio_manager_property(self, seed_id: int, cycle_id: int, mapping_profile_id: int, file_path: str) -> dict:
        """Import the downloaded xlsx file into SEED on a specific propertyID
        Args:
            seed_id (int): Property view ID to update with the ESPM file
            cycle_id (int): Cycle ID
            mapping_profile_id (int): Column Mapping Profile ID
            file: path to file downloaded from the retrieve_portfolio_manager_report method above
        ESPM file will have meter data that we want to handle (electricity and natural gas)
        in the 'Meter Entries' tab"""

        files_params = [
            ("file", (Path(file_path).name, open(Path(file_path).resolve(), "rb"))),
        ]

        response = self.client.put(
            None,
            required_pk=False,
            endpoint="property_update_with_espm",
            url_args={"PK": seed_id},
            files=files_params,
            cycle_id=cycle_id,
            mapping_profile_id=mapping_profile_id
        )

        return response

    def retrieve_analyses_for_property(self, property_id: int) -> dict:
        """Retrieve a list of all the analyses for a single property id. Since this
        is a property ID, then it is all the analyses for the all cycles. Note that this endpoint
        requires the passing of the organization id as a query parameter, otherwise it fails.

        Args:
            property_id (int): Property view id to return the list of analyses

        Returns:
            dict: list of all the analyses that have run (or failed) for the property view
        """
        return self.client.get(
            None,
            required_pk=False,
            endpoint="properties_analyses",
            url_args={"PK": property_id},
            include_org_id_query_param=True,
        )

    def retrieve_analysis_result(self, analysis_id: int, analysis_view_id: int) -> dict:
        """Return the detailed JSON of a single analysis view. The endpoint in SEED is
        typically: https://dev1.seed-platform.org/app/#/analyses/274/runs/14693.

        Args:
            analysis_id (int): ID of the analysis
            analysis_view_id (int): ID of the analysis view

        Returns:
            dict: Return the detailed results of a single analysis view
        """
        return self.client.get(
            None,
            required_pk=False,
            endpoint="analyses_views",
            url_args={"PK": analysis_id, "ANALYSIS_VIEW_PK": analysis_view_id},
            include_org_id_query_param=True,
        )
