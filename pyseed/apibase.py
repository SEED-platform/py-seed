"""
copyright (c) 2016 Earth Advantage. All rights reserved.
..codeauthor::Paul Munday <paul@paulmunday.net>

Functionality for calls to external APIs"""

import re

import requests

from pyseed.exceptions import APIClientError


def add_pk(url, pk, required=True, slash=False):
    """Add id/primary key to url"""
    if required and not pk:
        raise APIClientError("id/pk must be supplied")
    if pk:
        if isinstance(pk, str) and not pk.isdigit() or (not isinstance(pk, (int, str)) or int(pk) < 0):
            raise TypeError("id/pk must be a positive integer")
        url = f"{url}/{pk}" if not url.endswith("/") else f"{url}{pk}"
    # Only add the trailing slash if it's not already there
    if slash and not url.endswith("/"):
        url = f"{url}/"
    return url


class BaseAPI:
    """
    Base class for API Calls
    """

    # pylint: disable=too-few-public-methods, too-many-instance-attributes

    def __init__(self, url=None, use_ssl=True, timeout=None, use_json=False, use_auth=False, auth=None, **kwargs):
        # pylint: disable=too-many-arguments
        """Set url,api key, auth usage, ssl usage, timeout etc.

        :param url: url to use, http(s):// can be omitted, an error will
                   be used if it is supplied and does not match `use_ssl`
        :param: use_ssl: connect over https, defaults to True
        :param use_auth: use authentication

        ..Note:
            If `use_auth` is True the default is to use http basic
            authentication if self.auth is not set. (You will need to
            do this by overriding __init__ and setting this before
            calling super.

            This requires username and password to be supplied as
            keyword arguments. N.B. api keys using basic auth e.g., SEED
            should be supplied as password.

            To use Digest Authentication set auth_method='digest'

            If `use_ssl` is False and the url you supply starts with https
            an error will be thrown.
        """
        self.timeout = timeout
        self.use_ssl = use_ssl
        self.use_json = use_json
        self.use_auth = use_auth
        self.auth = auth
        self.url = None
        self.url = self._construct_url(url) if url else None
        for key, val in kwargs.items():
            setattr(self, key, val)

    def _construct_payload(self, params):
        """Construct parameters for an api call.
        .
                :param params: A dictionary of key-value pairs to include
                    in the request.
                :return: A dictionary of k-v pairs to send to the server
                    in the request.
        """
        compulsory = getattr(self, "compulsory_params", [])
        for param in compulsory:
            if param not in params:
                try:
                    params[param] = getattr(self, param)
                except AttributeError:
                    msg = f"{param} is a compulsory field"
                    raise APIClientError(msg)
        return params

    def _construct_url(self, urlstring, use_ssl=None):
        """Construct url"""
        # self.use_ssl takes priority to enforce ssl use
        use_ssl = self.use_ssl if self.use_ssl is not None else use_ssl
        if not urlstring and not self.url:
            raise APIClientError("No url set")
        elif not urlstring:
            url = self.url
        elif urlstring.startswith("https://") and not use_ssl:
            # We strip off url prefix
            # raise an error if https is used  in url without use_ssl
            raise APIClientError("use_ssl is false but url starts with https")
        elif urlstring.startswith("http://") and use_ssl:
            # We strip off url prefix
            # raise an error if http is used in url with use_ssl
            raise APIClientError("use_ssl is true but url does not starts with https")
        else:
            # strip http(s):// off url
            regex = re.compile("^https?://")
            urlstring = regex.sub("", urlstring)
            start = "https://" if use_ssl else "http://"
            url = f"{start}{urlstring}"
        return url

    def check_call_success(self, response):
        """Return true if api call was successful."""
        # pylint: disable=no-self-use, no-member
        return response.status_code == requests.codes.ok

    def _get(self, url=None, use_ssl=None, **kwargs):
        """Internal method to make api calls using GET."""
        url = self._construct_url(url, use_ssl=use_ssl)
        params = self._construct_payload(kwargs)
        payload = {"timeout": self.timeout, "headers": params.pop("headers", None)}
        if params:
            payload["params"] = params
        if self.auth:  # pragma: no cover
            payload["auth"] = self.auth
        # timeout is specified in the payload
        api_call = requests.get(url, **payload)  # noqa: S113
        return api_call

    def _post(self, url=None, use_ssl=None, params=None, files=None, **kwargs):
        """Internal method to make api calls using POST."""
        url = self._construct_url(url, use_ssl=use_ssl)
        if not params:
            params = {}
        params = self._construct_payload(params)
        payload = {"timeout": self.timeout, "headers": params.pop("headers", None)}
        if params:
            payload["params"] = params
        if files:
            payload["files"] = files
        if self.auth:  # pragma: no cover
            payload["auth"] = self.auth
        if self.use_json:
            data = kwargs.pop("json", None)
            if data:
                payload["json"] = data
            else:
                # just put the remaining kwargs into the json field
                payload["json"] = kwargs
        else:
            data = kwargs.pop("data", None)
            if data:
                payload["data"] = data
            else:
                # just put the remaining kwargs into the data field
                payload["data"] = kwargs

        # if there are any remaining kwargs, then put them into the params
        if "params" not in payload:
            payload["params"] = {}
        payload["params"].update(**kwargs)

        # now do the actual call to post!
        # timeout is specified in the payload
        api_call = requests.post(url, **payload)  # noqa: S113
        return api_call

    def _put(self, url=None, use_ssl=None, params=None, files=None, **kwargs):
        """Internal method to make api calls using PUT."""
        url = self._construct_url(url, use_ssl=use_ssl)
        if not params:
            params = {}
        params = self._construct_payload(params)
        payload = {"timeout": self.timeout, "headers": params.pop("headers", None)}
        if params:
            payload["params"] = params
        if files:  # pragma: no cover
            payload["files"] = files
        if self.auth:  # pragma: no cover
            payload["auth"] = self.auth
        if self.use_json:
            data = kwargs.pop("json", None)
            if data:
                payload["json"] = data
            else:
                # just put the remaining kwargs into the json field
                payload["json"] = kwargs
        else:
            data = kwargs.pop("data", None)
            if data:
                payload["data"] = data
            else:
                # just put the remaining kwargs into the data field
                payload["data"] = kwargs

        # if there are any remaining kwargs, then put them into the params
        if "params" not in payload:
            payload["params"] = {}
        payload["params"].update(**kwargs)
        # timeout is specified in the payload
        api_call = requests.put(url, **payload)  # noqa: S113
        return api_call

    def _patch(self, url=None, use_ssl=None, params=None, files=None, **kwargs):
        """Internal method to make api calls using PATCH."""
        url = self._construct_url(url, use_ssl=use_ssl)
        if not params:
            params = {}
        params = self._construct_payload(params)
        payload = {"timeout": self.timeout, "headers": params.pop("headers", None)}
        if params:
            payload["params"] = params
        if files:
            payload["files"] = files
        if self.auth:  # pragma: no cover
            payload["auth"] = self.auth
        if self.use_json:
            data = kwargs.pop("json", None)
            if data:
                payload["json"] = data
            else:
                # just put the remaining kwargs into the json field
                payload["json"] = kwargs
        else:
            data = kwargs.pop("data", None)
            if data:
                payload["data"] = data
            else:
                # just put the remaining kwargs into the data field
                payload["data"] = kwargs

        # if there are any remaining kwargs, then put them into the params
        if "params" not in payload:
            payload["params"] = {}
        payload["params"].update(**kwargs)
        # timeout is specified in the payload
        api_call = requests.patch(url, **payload)  # noqa: S113
        return api_call

    def _delete(self, url=None, use_ssl=None, **kwargs):
        """Internal method to make api calls using DELETE."""
        url = self._construct_url(url, use_ssl=use_ssl)
        params = self._construct_payload(kwargs)
        payload = {"timeout": self.timeout, "headers": params.pop("headers", None)}
        if params:
            payload["params"] = params
        if self.auth:  # pragma: no cover
            payload["auth"] = self.auth
        # timeout is specified in the payload
        api_call = requests.delete(url, **payload)  # noqa: S113
        return api_call


class JSONAPI(BaseAPI):
    """
    Base class for Json API Calls. See BaseAPI for documentation.
    """

    # pylint: disable=too-few-public-methods, too-many-arguments

    def __init__(self, url=None, use_ssl=True, timeout=None, use_auth=False, auth=None, **kwargs):
        super().__init__(url=url, use_ssl=use_ssl, timeout=timeout, use_json=True, use_auth=use_auth, auth=auth, **kwargs)


class UserAuthMixin:
    """
    Mixin to provide basic or digest api client authentication via username
    and password(or api_key)."""

    # pylint:disable=too-few-public-methods

    def _get_auth(self):
        """Get basic or digest auth by username/password"""
        username = getattr(self, "username", None)
        password = getattr(self, "password", None)
        # support using api_key as password in basic auth
        # as used by SEED (if supplied as api_key not password)
        if not password:
            password = getattr(self, "api_key", None)
        if getattr(self, "auth_method", None) == "digest":
            auth = requests.auth.HTTPDigestAuth(username, password)
        else:
            auth = requests.auth.HTTPBasicAuth(username, password)
        return auth

    def _construct_payload(self, params):
        """Construct parameters for an api call.
        .
                :param params: A dictionary of key-value pairs to include
                    in the request.
                :return: A dictionary of k-v pairs to send to the server
                    in the request.
        """
        if getattr(self, "use_auth", None) and not getattr(self, "auth", None):
            self.auth = self._get_auth()
        return super()._construct_payload(params)


class OAuthMixin:
    """
    Mixin to provide api client authentication via OAuth access tokens based
    on the JWTGrantClient found in jwt-oauth2lib.

    see https://github.com/GreenBuildingRegistry/jwt_oauth2
    """

    _token_type = "Bearer"  # noqa: S105
    oauth_client = None

    def _get_access_token(self):
        """Generate OAuth access token"""
        private_key_file = getattr(self, "private_key_location", None)
        client_id = getattr(self, "client_id", None)
        username = getattr(self, "username", None)
        with open(private_key_file) as pk_file:
            sig = pk_file.read()
            oauth_client = self.oauth_client(sig, username, client_id, pvt_key_password=getattr(self, "pvt_key_password", None))
            return oauth_client.get_access_token()

    def _construct_payload(self, params):
        """Construct parameters for an api call.

        :param params: A dictionary of key-value pairs to include
            in the request.
        :return: A dictionary of k-v pairs to send to the server
            in the request.
        """
        params = super()._construct_payload(params)
        token = getattr(self, "token", None) or self._get_access_token()
        params["headers"] = {"Authorization": f"{self._token_type} {token}"}
        return params
