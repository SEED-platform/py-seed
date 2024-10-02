"""
copyright (c) 2016 Earth Advantage. All rights reserved.
..codeauthor::Paul Munday <paul@paulmunday.net>

Functionality for interacting with the SEED API.

This should be considered a private API.

Use the classes and functions from gbr/common/data/seedrecords.py and
gbr/common/api.py for general use.

N.B. Only a Read Only client (with public methods) is supplied.
This is a deliberate design decision. There is no general purpose client that
can write to the db, this ensures caching is transparent and always valid.

You *must* always use the class corresponding to the relevant model, i.e.,
one that inherits from SEEDRecord to be able to write to the db.
You *should* generally this for reading too, in order to get the benefits of
caching.

"""

import inspect

import requests

from pyseed.apibase import JSONAPI, OAuthMixin, UserAuthMixin, add_pk
from pyseed.exceptions import SEEDError

# Constants (Should end with a slash)
URLS = {
    "v3": {
        "column_mapping_profiles": "/api/v3/column_mapping_profiles/",
        "column_mapping_profiles_filter": "/api/v3/column_mapping_profiles/filter/",
        "columns": "/api/v3/columns/",
        "cycles": "/api/v3/cycles/",
        "datasets": "/api/v3/datasets/",
        "gbr_properties": "/api/v3/gbr_properties/",
        "green_assessment": "/api/v3/green_assessments/",
        "green_assessment_property": "/api/v3/green_assessment_properties/",
        "green_assessment_url": "/api/v3/green_assessment_urls/",
        "import_files": "/api/v3/import_files/",
        "import_files_reuse_inventory_file_for_meters": "/api/v3/import_files/reuse_inventory_file_for_meters/",
        "labels": "/api/v3/labels/",
        "labels_property": "/api/v3/labels_property/",
        "labels_taxlot": "/api/v3/labels_taxlot/",
        "organizations": "/api/v3/organizations/",
        "portfolio_manager_report": "/api/v3/portfolio_manager/report/",
        "portfolio_manager_report_templates": "/api/v3/portfolio_manager/template_list/",
        "properties": "/api/v3/properties/",
        "properties_labels": "/api/v3/properties/labels/",
        "properties_search": "/api/v3/properties/search/",
        "property_views": "/api/v3/property_views/",
        "taxlots": "/api/v3/taxlots/",
        "upload": "/api/v3/upload/",
        "users": "/api/v3/users/",
        # No versioning endpoints
        "version": "/api/version/",
        # POSTs with replaceable keys
        "import_files_check_meters_tab_exists_pk": "/api/v3/import_files/PK/check_meters_tab_exists/",
        "import_files_start_map_data_pk": "/api/v3/import_files/PK/map/",
        "import_files_start_matching_pk": "/api/v3/import_files/PK/start_system_matching_and_geocoding/",
        "import_files_start_save_data_pk": "/api/v3/import_files/PK/start_save_data/",
        "org_column_mapping_import_file": "api/v3/organizations/ORG_ID/column_mappings/",
        "portfolio_manager_property_download": "/api/v3/portfolio_manager/PK/download/",
        # PUTs with replaceable keys:
        "properties_update_with_buildingsync": "api/v3/properties/PK/update_with_building_sync/",
        "properties_upload_inventory_document": "api/v3/properties/PK/upload_inventory_document",
        "property_update_with_espm": "api/v3/properties/PK/update_with_espm/",
        # GETs with replaceable keys
        "analyses_views": "/api/v3/analyses/PK/views/ANALYSIS_VIEW_PK/",
        "audit_template_building_xml": "/api/v3/audit_template/PK/get_building_xml",
        "audit_template_submission": "/api/v3/audit_template/PK/get_submission",
        "import_files_matching_results": "/api/v3/import_files/PK/matching_and_geocoding_results/",
        "properties_cross_cycle_data": "/api/v3/properties/PK/links/",
        "progress": "/api/v3/progress/PROGRESS_KEY/",
        "properties_analyses": "/api/v3/properties/PK/analyses/",
        "properties_meter_usage": "/api/v3/properties/PK/meter_usage/",
        "properties_meters": "/api/v3/properties/PK/meters/",
        # GET & POST with replaceable keys
        "properties_meters_reading": "/api/v3/properties/PK/meters/METER_PK/readings/",
    },
}


# Private Classes and Functions
def _get_urls(base_url, url_map=None, version=None):
    """Populate URL"""
    version = version if version else "v3"
    if not url_map:
        url_map = URLS[version]
    return {key: "{}/{}".format(base_url.rstrip("/"), val.lstrip("/")) for key, val in url_map.items()}


def _set_default(obj, key, val, required=True):
    """
    Sets val to obj.key if val is None and obj.key is set.
    Raises Attribute error is neither are set and required is True.

    :returns: val
    """
    if not val:
        val = getattr(obj, key, None)
    if not val and required:
        msg = f"{key} is not set"
        raise AttributeError(msg)
    return val


def _replace_url_args(url, url_args):
    """Replace any custom string URL items with values in args"""
    if url_args:
        for key, value in url_args.items():
            url = url.replace(f"/{key}/", f"/{value}/")
    return url


class SEEDBaseClient(JSONAPI):
    """Interact with SEED API.

    Raises a SEEDError on an API Error. No further logging or error
    handling is done. This the responsibility of the caller.

    This should never be used directly, instead inherit from
    one of the SEED Read or ReadWrite classes with mixins.

    Note subclasses of these should not themselves be inherited from due
    to the way error handling works, this should not be needed, other classes
    can inherit from them directly and overwrite methods/use mixins as
    appropriate.

    endpoint refers to the endpoint name. This allows you to call an
    endpoint without having to know the full url.

    Endpoint names are set in config, and can be accessed as self.endpoints.

    data_name is set as an attribute on the view called.
    This constrains the actual response data.
    If not set it is derived from the url (typically it's the view name).
    In either case 'data' is used as a fallback, then detail.

    This is an annoyance, but SEED adds an unnecessary 'status'
    to its return values to indicate success/failure rather than
    using status codes (though some endpoints also do this) and returning
    the result directly.

    :param org_id: organization id of org owning records
    :type org_id: int
    :param username: username (email) of user who can access records
    :type username: string (email address)
    :param api_key: api_key of use who can access records
    :type api_key: string
    :param endpoint: seed endpoint e.g., properties for /api/v3/properties/
    :type endpoint: string
    :param data_name: name of json key in api results containing data
                      not always needed
    :type data_name: string (result are json keys: 'status', data_name)
    :param config: config object
    :type config: gbr.common.config.GBRConfig
    :param config_urls_key: key for urls in config object (default urls)
    :type config_urls_key: str
    """

    # pylint:disable=too-few-public-methods,too-many-arguments
    # pylint:disable=too-many-instance-attributes

    def __init__(
        self,
        org_id,
        username=None,
        password=None,
        access_token=None,
        endpoint=None,
        data_name=None,
        use_ssl=None,
        base_url=None,
        port=None,
        url_map=None,
        version=None,
        **kwargs,
    ):
        use_ssl = use_ssl if use_ssl is not None else True
        super().__init__(username=username, password=password, use_ssl=use_ssl, use_auth=True, access_token=access_token, **kwargs)
        self.org_id = org_id
        self.token = access_token
        # prevent overriding if set in subclass as class attr
        if not getattr(self, "endpoint", None):
            self.endpoint = endpoint
        if not getattr(self, "data_name", None):
            self.data_name = data_name
        if not getattr(self, "base_url", None):
            self.base_url = base_url if base_url else "localhost"
        if not getattr(self, "port", None):
            self.port = port if port else None
        if self.port:
            self.base_url = f"{self.base_url}:{self.port}"
        if not self.base_url.endswith("/"):
            self.base_url = self.base_url + "/"
        self.username = username
        self.urls = _get_urls(self.base_url, url_map=url_map, version=version)
        self.endpoints = self.urls.keys()

    def _check_response(self, response, *args, **kwargs):
        """Verify we have got a response without any errors.

        *Never* call this directly in your methods,
        *Always use self._get() etc., otherwise errors will not
        be reported correctly.
        """
        error = False
        error_msg = "Unknown error from SEED API"

        # grab the response content type to determine json, spreadsheet, or text
        response_content_types = response.headers.get("Content-Type", [])

        # OK, Created, Accepted, No-Content
        if response.status_code not in [200, 201, 202, 204]:
            error = True
            error_msg = f"SEED returned status code: {response.status_code}"
        # SEED adds a status key to the response to indicate success/error
        # This is superfluous as status codes should be used to indicate an
        # error, but they are not always set correctly.
        elif response.status_code == 204:
            # there will not be response content with a 204
            error = False
        elif "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response_content_types:
            # spreadsheet response
            error = False
        elif "application/pdf" in response_content_types:
            # PDF report response
            error = False
        elif "application/json" not in response_content_types:
            # get as text
            if not response.content:
                error = True
        elif isinstance(response.json(), dict):
            status_field = response.json().get("status", None)
            has_progress_key = "progress_key" in response.json()
            if status_field:
                if has_progress_key:
                    # For the delete cycles, the data returned have a status and a progress_key,
                    # but no progress_data. In lieu of updating SEED, this check is added
                    # specifically for this case
                    error = status_field not in ["not-started", "success", "parsing"]
                elif status_field == "error":
                    error = True
                elif status_field == "success":
                    # continue
                    error = False
            elif "success" in response.json():
                success_flag = response.json().get("success", None)
                # For file uploads the response key is 'success'
                error = not success_flag
            elif "progress_data" in response.json():
                # this is a system matching response, which is okay. return the success flag of this
                status_flag = response.json()["progress_data"].get("status", None)
                error = status_flag not in ["not-started", "success", "parsing"]
            elif not any(
                key in ["results", "readings", "data", "status", "id", "organizations", "sha", "users"] for key in response.json()
            ):
                # In some cases there is not a 'status' field, so check if there are
                # any other keys in the response that depict a success:
                # readings - this comes from meters
                # data - lots of responses just return the data flag
                # status - sometimes the status comes back as complete
                # id - For some object creates, the response is simply the object back in JSON format with an ID field.
                # organizations - this is the only key when returning the list of orgs
                # sha - When parsing the version of SEED
                error = True

        elif not isinstance(response.json(), list):
            error = True

        if error:
            if response.content:
                try:
                    if getattr(response.json(), "get", None):
                        error_msg = response.json().get("message", f"Unknown SEED Error {response.status_code}: {response.json()}")
                    else:
                        error_msg = f"Unknown SEED Error {response.status_code}: {response.json()}"
                except ValueError:
                    error_msg = "Unknown SEED Error: No response returned"
            if args:
                kwargs["args"] = args
            self._raise_error(response, error_msg, stack_pos=1, **kwargs)

    def _get_result(self, response, data_name=None, **kwargs):
        """Extract result data from response. If no data_name is given, then this method
        tries to determine what the first element of the resulting JSON is which is then used as
        the base for the rest of the response. This is not always desired, so pass data_name='all' if
        you want to get the entire response back."""

        # grab the response content type to determine json, spreadsheet, or text
        response_content_types = response.headers.get("Content-Type", [])

        # pass through for spreadsheet (?)
        if "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response_content_types:
            return response.content
        if "application/json" not in response_content_types:
            return {"status": "success", "content": response.content}
        if not data_name:
            url = response.request.url
            # take the last part of the url unless it's a digit
            # in which case take the previous part
            durl = url.lstrip(self.base_url).rstrip("/").rsplit("/", 1)
            data_name = durl[0].rsplit("/", 2)[1] if durl[1].isdigit() else durl[1]
        # actual results should be under data_name or the fallbacks
        # handle a 204
        result = None
        result = {"status": "success"} if response.status_code == 204 else response.json()
        if result is None:
            error_msg = "No results returned"
            self._raise_error(response, error_msg, stack_pos=2, **kwargs)

        constrained_result = None
        if data_name != "all":
            for dname in [data_name, "data", "detail"]:
                try:
                    # allow a list to be valid (this is the case with labels)
                    if isinstance(result, dict):
                        constrained_result = result.get(dname)
                    if constrained_result is not None:
                        result = constrained_result
                        break
                except KeyError:
                    pass

        if result is None:
            error_msg = f"Could not find result using data_name {data_name}."
            self._raise_error(response, error_msg, stack_pos=2, **kwargs)

        return result

    def _raise_error(self, response, error_msg, stack_pos=0, *args, **kwargs):
        """
        Raise SEEDError on bad response.

        This method is intended for use only by self_get(), etc., and the methods
        called there. For most purposes you should raise SEEDError directly.

        This method uses the inspect module to derive the method name.
        stack_pos indicates where in the stack to find this: it corresponds
        to the depth of function calls.

        Thus, if the error occurs directly in the function calling _raise_error
        stack_pos=0, if that function is called by another function add 1 etc.
        Note technically *this* method (_raise_error) is at the bottom of the
        stack, but we add 1 to stack_pos so counting starts at the method
        that calls this one.


        :param response: response object
        :param error_msg: error message
        :param stack_pos: indicates depth of stack
        :type stack_pos: integer
        """
        status_code = response.status_code
        url = response.request.url
        verb = response.request.method
        # e.g., MyClass.method
        caller = f"{self.__class__.__name__}.{inspect.stack()[stack_pos + 1][3]}"
        if args:
            kwargs["args"] = args
        raise SEEDError(error_msg, url=url, caller=caller, verb=verb, status_code=status_code, **kwargs)

    def _set_params(self, params):
        """Add org_id"""
        params["organization_id"] = self.org_id
        return params


# SEEDClient Mixins, used to add CRUD Methods
# These should be used with SEEDClient as they rely on its methods


class CreateMixin:
    """Add _post methods"""

    # pylint:disable=too-few-public-methods

    def post(self, endpoint=None, data_name=None, **kwargs):
        """
        Post to SEED API (Create record)

        :param endpoint: endpoint name.
        :param url: url to call
        :param data_name: key response data is stored under

        :returns: dict (from response.json()[data_name])
        """
        # for a post, if the user has sent some url args, then pop them for later
        # parsing.
        url_args = kwargs.pop("url_args", None)
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, "endpoint", endpoint)
        data_name = _set_default(self, "data_name", data_name, required=False)
        # check if the endpoint is to be looked up or is a fully qualified url
        if "/" in endpoint:
            url = endpoint
        elif endpoint in self.urls:
            url = self.urls[endpoint]
        else:
            raise Exception(f"Unknown endpoint: {endpoint}")
        if not url.endswith("/"):
            url = url + "/"
        url = _replace_url_args(url, url_args)
        response = super()._post(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)


class ReadMixin:
    """Add get &  list method"""

    # pylint:disable=too-few-public-methods

    def get(self, pk, endpoint=None, data_name=None, **kwargs):
        """
        Get a single record from SEED.

        :param endpoint: endpoint name.
        :param pk: primary key of record
        :param data_name: key response data is stored under

        :returns: dict (from response.json()[data_name])

        """
        url_args = kwargs.pop("url_args", None)
        org_id_qp = kwargs.pop("include_org_id_query_param", False)
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, "endpoint", endpoint)
        data_name = _set_default(self, "data_name", data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=kwargs.pop("required_pk", True), slash=True)
        url = _replace_url_args(url, url_args)
        if org_id_qp:
            url += f"?organization_id={self.org_id}"
        response = super()._get(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)

    def list(self, endpoint=None, data_name=None, **kwargs):
        """
        Get all records from SEED.

        :param endpoint: endpoint name.
        :param data_name: key response data is stored under

        :returns: dict (from response.json()[data_name])
        """
        url_args = kwargs.pop("url_args", None)
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, "endpoint", endpoint)
        data_name = _set_default(self, "data_name", data_name, required=False)
        url = self.urls[endpoint]
        if not url.endswith("/"):
            url = url + "/"
        url = _replace_url_args(url, url_args)
        response = super()._get(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)


class UpdateMixin:
    """Add _put & _patch methods"""

    # pylint:disable=too-few-public-methods,redefined-builtin

    def put(self, pk, endpoint=None, data_name=None, **kwargs):
        """
        Update a record via PUT.

        :param pk: key to put to
        :param endpoint: endpoint name.
        :param data_name: key response data is stored under

        :returns: dict (from response.json()[data_name])
        """
        url_args = kwargs.pop("url_args", None)
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, "endpoint", endpoint)
        data_name = _set_default(self, "data_name", data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=kwargs.pop("required_pk", True), slash=True)
        url = _replace_url_args(url, url_args)

        response = super()._put(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)

    def patch(self, pk, endpoint=None, data_name=None, **kwargs):
        """
        Update a record via PATCH.

        :param endpoint: endpoint name.
        :param pk: key to put to
        :param data_name: key response data is stored under

        :returns: dict (from response.json()[data_name])
        """
        url_args = kwargs.pop("url_args", None)
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, "endpoint", endpoint)
        data_name = _set_default(self, "data_name", data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=kwargs.pop("required_pk", True), slash=True)
        url = _replace_url_args(url, url_args)
        response = super()._patch(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)


class DeleteMixin:
    """Add _delete methods"""

    # pylint:disable=too-few-public-methods,redefined-builtin

    def delete(self, pk, endpoint=None, data_name=None, **kwargs):
        """
        Delete a record in SEED

        :param endpoint: endpoint name.
        :param pk: key to put to
        :param data_name: key response data is stored under

        :returns: None
        """
        # pylint:disable=no-member
        url_args = kwargs.pop("url_args", None)
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, "endpoint", endpoint)
        data_name = _set_default(self, "data_name", data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=kwargs.pop("required_pk", True), slash=True)
        url = _replace_url_args(url, url_args)
        response = super()._delete(url=url, **kwargs)
        # delete should return 204 and no content, unless it is a background task
        if response.status_code != requests.codes.no_content:
            self._check_response(response, **kwargs)
            return self._get_result(response, data_name=data_name, **kwargs)


class SEEDReadOnlyClient(ReadMixin, UserAuthMixin, SEEDBaseClient):
    """Read Only Client"""


class SEEDReadWriteClient(CreateMixin, ReadMixin, UpdateMixin, DeleteMixin, UserAuthMixin, SEEDBaseClient):
    """Client with full CRUD Methods"""

    # pylint:disable=too-many-ancestors


class SEEDOAuthReadOnlyClient(ReadMixin, OAuthMixin, SEEDBaseClient):
    """Read Ony Client"""


class SEEDOAuthReadWriteClient(CreateMixin, ReadMixin, UpdateMixin, DeleteMixin, OAuthMixin, SEEDBaseClient):
    """Client with full CRUD Methods"""

    # pylint:disable=too-many-ancestors
