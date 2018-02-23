#!/usr/bin/env python
# encoding: utf-8
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

You *must* always use the class corresponding to the relevant model, i.e.
one that inherits from SEEDRecord to be able to write to the db.
You *should* generally this for reading too, in order to get the benefits of
caching.

"""

# Imports from Standard Library
import inspect

# Imports from Third Party Modules
import requests

# Local Imports
from pyseed.apibase import JSONAPI, OAuthMixin, UserAuthMixin, add_pk
from pyseed.exceptions import SEEDError

# Constants
URLS = {
    'columns': '/api/v2/columns/',
    'column_mappings': '/api/v2/column_mappings/',
    'cycles': '/api/v2/cycles/',
    'datasets': '/api/v2/datasets/',
    'gbr_properties': '/api/v2/gbr_properties/',
    'green_assessment': '/api/v2/green_assessments/',
    'green_assessment_property': '/api/v2/green_assessment_properties/',
    'green_assessment_url': '/api/v2/green_assessment_urls/',
    'labels': '/api/v2/labels/',
    'import_files': '/api/v2/import_files/',
    'projects': '/api/v2/projects/',
    'properties': '/api/v2/properties/',
    'property_states': '/api/v2/property_states/',
    'property_views': '/api/v2/property_views/',
    'taxlots': '/api/v2/taxlots/',
    'users': '/api/v2/users/',
}


# Private Classes and Functions
def _get_urls(base_url, url_map=None):
    """Populate URL"""
    if not url_map:
        url_map = URLS
    return {
        key: '{}/{}'.format(base_url.rstrip('/'), val.lstrip('/'))
        for key, val in url_map.items()
    }


def _set_default(obj, key, val, required=True):
    """
    Sets val to obj.key if val is None and obj.key is set.
    Raises Attribute error is neither are set and required is True.

    :returns: val
    """
    if not val:
        val = getattr(obj, key, None)
    if not val and required:
        msg = '{} is not set'.format(key)
        raise AttributeError(msg)
    return val


# Public Classes and Functions


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

    endpoint refers to the endpoint name. This allow you to call an
    endpoint without having to know the full url.

    Endpoint names are set in config, and can be accessed as self.endpoints.

    data_name is set as an attribute on the view called.
    This constrains the actual response data.
    If not set it is derived from the url (typically its the view name).
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
    :param endpoint: seed endpoint e.g properties for /api/v2/properties/
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

    def __init__(self, org_id, username=None, password=None, access_token=None,
                 endpoint=None, data_name=None, use_ssl=None,
                 base_url=None, port=None, url_map=None, **kwargs):
        use_ssl = use_ssl if use_ssl is not None else True
        super(SEEDBaseClient, self).__init__(
            username=username, password=password, use_ssl=use_ssl,
            use_auth=True, access_token=access_token, **kwargs
        )
        self.org_id = org_id
        self.token = access_token
        # prevent overriding if set in sublcass as class attr
        if not getattr(self, 'endpoint', None):
            self.endpoint = endpoint
        if not getattr(self, 'data_name', None):
            self.data_name = data_name
        if not getattr(self, 'base_url', None):
            self.base_url = base_url if base_url else 'localhost'
        if not getattr(self, 'port', None):
            self.port = port if port else None
        if self.port:
            self.base_url = '{}:{}'.format(self.base_url, self.port)
        if not self.base_url.endswith('/'):
            self.base_url = self.base_url + '/'
        self.urls = _get_urls(self.base_url, url_map)
        self.endpoints = self.urls.keys()

    def _check_response(self, response, *args, **kwargs):
        """Verify we have got a response without any errors.

        *Never* call this directly in your methods,
        *Always use self._get() etc, otherwise errors will not
        be reported correctly.
        """
        error = False
        error_msg = "Unknown error from SEED API"
        # OK, Created , Accepted
        if response.status_code not in [200, 201, 202]:
            error = True
            error_msg = "SEED returned status code: {}".format(
                response.status_code
            )
        # SEED adds a status key to the response to indicate success/error
        # This is superfluous as status codes should be used to indicate an
        # error, but theyt are not always set correctly.
        elif response.json().get('status', None) == 'error':
            error = True
        if error:
            if response.content:
                try:
                    error_msg = response.json().get(
                        'message', 'Unknown SEED Error'
                    )
                except ValueError:
                    error_msg = 'Unknown SEED Error'
            if args:
                kwargs['args'] = args
            self._raise_error(response, error_msg, stack_pos=1, **kwargs)

    def _get_result(self, response, data_name=None, **kwargs):
        """Extract result data from response."""
        if not data_name:
            url = response.request.url
            # take the last part of the url unless it's a digit
            # in which case take the previous part
            durl = url.lstrip(self.base_url).rstrip('/').rsplit('/', 1)
            if durl[1].isdigit():
                data_name = durl[0].rsplit('/', 2)[1]
            else:
                data_name = durl[1]
        # actual results should be under data_name or the fallbacks
        for dname in [data_name, 'data', 'detail']:
            try:
                result = response.json().get(dname)
                if result is not None:
                    break
            except KeyError:
                pass
        if result is None:
            error_msg = "Could not find result using data_name {}.".format(
                data_name
            )
            self._raise_error(response, error_msg, stack_pos=2, **kwargs)
        return result

    def _raise_error(self, response, error_msg, stack_pos=0, *args, **kwargs):
        """
        Raise SEEDError on bad response.

        This method is intended for use only by self_get() etc and the methods
        called there. For most purposes you should raise SEEDError directly.

        This method uses the inspect module to derive the method name.
        stack_pos indicates where in the stack to find this: it corresponds
        to the depth of function calls.

        Thus if the error occurs directly in the function calling _raise_error
        stack_pos=0, if that function is called by another function add 1 etc.
        Note techically *this* method (_raise_error) is at the bottom of the
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
        # e.g. MyClass.method
        caller = '{}.{}'.format(
            self.__class__.__name__, inspect.stack()[stack_pos + 1][3]
        )
        if args:
            kwargs['args'] = args
        raise SEEDError(
            error_msg, url=url, caller=caller, verb=verb,
            status_code=status_code, **kwargs
        )

    def _set_params(self, params):
        """Add org_id"""
        params['org_id'] = self.org_id
        return params


# SEEDClient Mixins, used to add CRUD Methods
# These should be used with SEEDClient as they rely on its methods


class CreateMixin(object):
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
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, 'endpoint', endpoint)
        data_name = _set_default(self, 'data_name', data_name, required=False)
        url = self.urls[endpoint]
        if not url.endswith('/'):
            url = url + '/'
        response = super(CreateMixin, self)._post(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)


class ReadMixin(object):
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
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, 'endpoint', endpoint)
        data_name = _set_default(self, 'data_name', data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=True, slash=True)
        response = super(ReadMixin, self)._get(url=url, **kwargs)
        self._check_response(response, **kwargs)
        result = self._get_result(response, data_name=data_name, **kwargs)
        return result

    def list(self, endpoint=None, data_name=None, **kwargs):
        """
        Get all records from SEED.

        :param endpoint: endpoint name.
        :param data_name: key response data is stored under

        :returns: dict (from response.json()[data_name])
        """
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, 'endpoint', endpoint)
        data_name = _set_default(self, 'data_name', data_name, required=False)
        url = self.urls[endpoint]
        if not url.endswith('/'):
            url = url + '/'
        response = super(ReadMixin, self)._get(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)


class UpdateMixin(object):
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
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, 'endpoint', endpoint)
        data_name = _set_default(self, 'data_name', data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=True, slash=True)
        response = super(UpdateMixin, self)._put(url=url, **kwargs)
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
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, 'endpoint', endpoint)
        data_name = _set_default(self, 'data_name', data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=True, slash=True)
        response = super(UpdateMixin, self)._patch(url=url, **kwargs)
        self._check_response(response, **kwargs)
        return self._get_result(response, data_name=data_name, **kwargs)


class DeleteMixin(object):
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
        kwargs = self._set_params(kwargs)
        endpoint = _set_default(self, 'endpoint', endpoint)
        data_name = _set_default(self, 'data_name', data_name, required=False)
        url = add_pk(self.urls[endpoint], pk, required=True, slash=True)
        response = super(DeleteMixin, self)._delete(url=url, **kwargs)
        # delete should return 204 and no content
        if response.status_code != requests.codes.no_content:
            self._check_response(response, **kwargs)


class SEEDReadOnlyClient(ReadMixin, UserAuthMixin, SEEDBaseClient):
    """Read Ony Client"""
    pass


class SEEDReadWriteClient(CreateMixin, ReadMixin, UpdateMixin, DeleteMixin,
                          UserAuthMixin, SEEDBaseClient):
    """Client with full CRUD Methods"""
    # pylint:disable=too-many-ancestors
    pass


class SEEDOAuthReadOnlyClient(ReadMixin, OAuthMixin, SEEDBaseClient):
    """Read Ony Client"""
    pass


class SEEDOAuthReadWriteClient(CreateMixin, ReadMixin, UpdateMixin,
                               DeleteMixin, OAuthMixin, SEEDBaseClient):
    """Client with full CRUD Methods"""
    # pylint:disable=too-many-ancestors
    pass
