"""
copyright (c) 2016-2016 Earth Advantage. All rights reserved.
..codeauthor::Paul Munday <paul@paulmunday.net>

Unit tests for pyseed/apibase
"""

import unittest
from unittest import mock

import pytest

from pyseed.apibase import JSONAPI, BaseAPI, add_pk
from pyseed.exceptions import APIClientError
from pyseed.seed_client_base import _get_urls, _set_default

NO_URL_ERROR = "No url set"
SSL_ERROR = "use_ssl is true but url does not starts with https"
SSL_ERROR2 = "use_ssl is false but url starts with https"

# Constants
SERVICES_DICT = {"urls": {"test1": "test1", "test2": "/test2"}}


class MockConfig:
    """Mock config object"""

    # pylint:disable=too-few-public-methods, no-self-use

    def __init__(self, conf):
        self.conf = conf

    def get(self, var, section=None, default=None):
        cdict = self.conf.get(section, {}) if section else self.conf  # pragma: no cover
        return cdict.get(var, default)


SERVICES = MockConfig(SERVICES_DICT)


@mock.patch("pyseed.apibase.requests")
class APITests(unittest.TestCase):
    """Tests for API base classes"""

    # pylint: disable=protected-access, no-self-use, unused-argument

    def setUp(self):
        self.url = "example.org"
        self.api = JSONAPI(self.url)

    def test_ssl_verification(self, mock_requests):
        """Test ssl usage"""
        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            JSONAPI("http://example.org")
        assert conm.value.error == SSL_ERROR

        # ensure error is raised if https is supplied and use_ssl is false
        with pytest.raises(APIClientError) as conm:
            JSONAPI("https://example.org", use_ssl=False)
        assert conm.value.error == SSL_ERROR2

        # test defaults to https
        api = JSONAPI("example.org")
        api._get()
        mock_requests.get.assert_called_with("https://example.org", timeout=None, headers=None)

        # use_ssl is False
        api = JSONAPI("example.org", use_ssl=False)
        api._get()
        mock_requests.get.assert_called_with("http://example.org", timeout=None, headers=None)

    def test_get(self, mock_requests):
        """Test _get method."""
        self.api._get(id=1, foo="bar")
        mock_requests.get.assert_called_with("https://example.org", params={"id": 1, "foo": "bar"}, timeout=None, headers=None)

    def test_post(self, mock_requests):
        """Test _get_post."""
        params = {"id": 1}
        files = {"file": "mock_file"}
        data = {"foo": "bar", "test": "test"}
        self.api._post(params=params, files=files, foo="bar", test="test")
        mock_requests.post.assert_called_with("https://example.org", params=params, files=files, json=data, timeout=None, headers=None)

        # Not json
        api = BaseAPI("example.org")
        api._post(params=params, files=files, foo="bar", test="test")
        mock_requests.post.assert_called_with("https://example.org", params=params, files=files, data=data, timeout=None, headers=None)

    def test_patch(self, mock_requests):
        """Test _get_patch."""
        params = {"id": 1}
        files = {"file": "mock_file"}
        data = {"foo": "bar", "test": "test"}
        self.api._patch(params=params, files=files, foo="bar", test="test")
        mock_requests.patch.assert_called_with("https://example.org", params=params, files=files, json=data, timeout=None, headers=None)

        # Not json
        api = BaseAPI("example.org")
        api._patch(params=params, files=files, foo="bar", test="test")
        mock_requests.patch.assert_called_with("https://example.org", params=params, files=files, data=data, timeout=None, headers=None)

    def test_delete(self, mock_requests):
        """Test _delete method."""
        self.api._delete(id=1, foo="bar")
        mock_requests.delete.assert_called_with("https://example.org", params={"id": 1, "foo": "bar"}, timeout=None, headers=None)

    def test_construct_payload(self, mock_requests):
        """Test construct_payload  method."""
        api = BaseAPI("example.org", compulsory_params=["id"])
        with pytest.raises(APIClientError):
            api._get(foo="bar")
        api._get(id=1)
        assert mock_requests.get.called

        url = self.url

        class TestAPI(BaseAPI):
            """test class"""

            # pylint: disable=too-few-public-methods

            def __init__(self):
                self.compulsory_params = ["id", "comp"]
                super().__init__(url)
                self.comp = 1

        api = TestAPI()
        with pytest.raises(APIClientError) as conm:
            api._get()
        assert conm.value.error == "id is a compulsory field"
        api._get(id=1)
        assert mock_requests.get.called

    def test_check_call_success(self, mock_requests):
        """Test check_call_success method."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        mock_requests.codes.ok = 200
        response = self.api._get(id=1)
        assert self.api.check_call_success(response)

    def test_construct_url(self, mock_requests):  # noqa: ARG002
        """Test _construct_url method."""
        api = BaseAPI(use_ssl=False)

        # ensure error is raised if no url  is supplied
        with pytest.raises(APIClientError) as conm:
            api._construct_url(None)
        assert conm.value.error == NO_URL_ERROR

        # ensure error is raised if https is supplied and use_ssl is false
        with pytest.raises(APIClientError) as conm:
            api._construct_url("https://www.example.org", use_ssl=False)
        assert conm.value.error == SSL_ERROR2

    def test_construct_url_ssl_explicit(self, mock_requests):  # noqa: ARG002
        """Test _construct_url method."""
        api = BaseAPI(use_ssl=True)

        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            api._construct_url("http://example.org", use_ssl=True)
        assert conm.value.error == SSL_ERROR

        # ensure error is raised if http is supplied and use_ssl is default
        with pytest.raises(APIClientError) as conm:
            api._construct_url("http://example.org")
        assert conm.value.error == SSL_ERROR

    def test_construct_url_ssl_implicit(self, mock_requests):  # noqa: ARG002
        """Test _construct_url method."""
        api = BaseAPI()

        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            api._construct_url("http://example.org", use_ssl=True)
        assert conm.value.error == SSL_ERROR

        # ensure error is raised if http is supplied and use_ssl is default
        with pytest.raises(APIClientError) as conm:
            api._construct_url("http://example.org")
        assert conm.value.error == SSL_ERROR


@mock.patch("pyseed.apibase.requests")
class APITestsNoURL(unittest.TestCase):
    """Tests for API base classes with no self.url set"""

    # pylint: disable=protected-access, no-self-use, unused-argument

    def setUp(self):
        self.url = "example.org"
        self.api = JSONAPI()

    def test_no_url(self, mock_requests):
        """Test ssl usage"""

    def test_get(self, mock_requests):
        """Test _get method."""
        self.api._get(self.url, id=1, foo="bar")
        mock_requests.get.assert_called_with("https://example.org", params={"id": 1, "foo": "bar"}, timeout=None, headers=None)

        # ensure error is raised if https is supplied and use_ssl is false
        api = BaseAPI("example.org", use_ssl=False)
        with pytest.raises(APIClientError) as conm:
            api._get(url="https://www.example.org", use_ssl=False)
        assert conm.value.error == SSL_ERROR2

        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            self.api._get(url="http://example.org")
        assert conm.value.error == SSL_ERROR

        # ensure error is raised if no url  is supplied
        with pytest.raises(APIClientError) as conm:
            self.api._get()
        assert conm.value.error == NO_URL_ERROR

        # test defaults to http
        self.api._get(url=self.url)
        mock_requests.get.assert_called_with("https://example.org", timeout=None, headers=None)

        # use_ssl is False
        api = BaseAPI("example.org", use_ssl=False)
        api._get(url=self.url, use_ssl=False)
        mock_requests.get.assert_called_with("http://example.org", timeout=None, headers=None)

    def test_post(self, mock_requests):
        """Test _get_post."""
        params = {"id": 1}
        files = {"file": "mock_file"}
        data = {"foo": "bar", "test": "test"}
        self.api._post(url=self.url, params=params, files=files, foo="bar", test="test")
        mock_requests.post.assert_called_with("https://example.org", params=params, files=files, json=data, timeout=None, headers=None)

        # Not json
        api = BaseAPI()
        api._post(url=self.url, params=params, files=files, foo="bar", test="test")
        mock_requests.post.assert_called_with("https://example.org", params=params, files=files, data=data, timeout=None, headers=None)

        # ensure error is raised if no url  is supplied
        with pytest.raises(APIClientError) as conm:
            self.api._post(params=params, files=files, foo="bar", test="test")
        assert conm.value.error == NO_URL_ERROR

        # ensure error is raised if https is supplied and use_ssl is false
        api = BaseAPI("example.org", use_ssl=False)
        with pytest.raises(APIClientError) as conm:
            api._post(url="https://example.org", use_ssl=False, params=params, files=files, foo="bar", test="test")
        assert conm.value.error == SSL_ERROR2

        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            self.api._post(url="http://example.org", use_ssl=True, params=params, files=files, foo="bar", test="test")
        assert conm.value.error == SSL_ERROR

    def test_patch(self, mock_requests):
        """Test _get_patch."""
        params = {"id": 1}
        files = {"file": "mock_file"}
        data = {"foo": "bar", "test": "test"}
        self.api._patch(url=self.url, params=params, files=files, foo="bar", test="test")
        mock_requests.patch.assert_called_with("https://example.org", params=params, files=files, json=data, timeout=None, headers=None)

        # Not json
        api = BaseAPI("example.org")
        api._patch(url=self.url, params=params, files=files, foo="bar", test="test")
        mock_requests.patch.assert_called_with("https://example.org", params=params, files=files, data=data, timeout=None, headers=None)

        # ensure error is raised if no url  is supplied
        with pytest.raises(APIClientError) as conm:
            self.api._patch(params=params, files=files, foo="bar", test="test")
        assert conm.value.error == NO_URL_ERROR

        # ensure error is raised if https is supplied and use_ssl is false
        api = BaseAPI("example.org", use_ssl=False)
        with pytest.raises(APIClientError) as conm:
            api._patch(url="https://example.org", use_ssl=False, params=params, files=files, foo="bar", test="test")
        assert conm.value.error == SSL_ERROR2

        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            self.api._patch(url="http://example.org", use_ssl=True, params=params, files=files, foo="bar", test="test")
        assert conm.value.error == SSL_ERROR

    def test_delete(self, mock_requests):
        """Test _delete method."""
        self.api._delete(url=self.url, id=1, foo="bar")
        mock_requests.delete.assert_called_with("https://example.org", params={"id": 1, "foo": "bar"}, timeout=None, headers=None)

        # ensure error is raised if https is supplied and use_ssl is false
        api = BaseAPI("example.org", use_ssl=False)
        with pytest.raises(APIClientError) as conm:
            api._delete(url="https://www.example.org")
        assert conm.value.error == SSL_ERROR2

        # ensure error is raised if http is supplied and use_ssl is true
        with pytest.raises(APIClientError) as conm:
            self.api._delete(url="http://example.org")
        assert conm.value.error == SSL_ERROR

        # ensure error is raised if no url  is supplied
        with pytest.raises(APIClientError) as conm:
            self.api._delete()
        assert conm.value.error == NO_URL_ERROR

        # test defaults to http
        self.api._delete(url=self.url)
        mock_requests.delete.assert_called_with("https://example.org", timeout=None, headers=None)

        # use_ssl is False
        api = BaseAPI("example.org", use_ssl=False)
        api._delete(url=self.url, use_ssl=False)
        mock_requests.delete.assert_called_with("http://example.org", timeout=None, headers=None)


class APIFunctionTest(unittest.TestCase):
    def testadd_pk(self):
        """Test add_pk helper function."""
        # Error checks
        with pytest.raises(APIClientError) as conm:
            add_pk("url", None)
        assert conm.value.error == "id/pk must be supplied"

        with pytest.raises(TypeError) as conm:
            add_pk("url", "a")
        assert conm.value.args[0] == "id/pk must be a positive integer"

        with pytest.raises(TypeError) as conm:
            add_pk("url", 1.2)
        assert conm.value.args[0] == "id/pk must be a positive integer"

        with pytest.raises(TypeError) as conm:
            add_pk("url", -1)
        assert conm.value.args[0] == "id/pk must be a positive integer"

        # adds ints
        result = add_pk("url", 1)
        assert result == "url/1"

        # converts strings if digit
        result = add_pk("url", "1")
        assert result == "url/1"

        # id not required
        result = add_pk("url", None, required=False)
        assert result == "url"

        # adds_slash
        result = add_pk("url", 1, slash=True)
        assert result == "url/1/"

        # does not repeat /
        result = add_pk("url/", 1)
        assert result == "url/1"

    def test_set_default(self):
        """Test _set_default helper method"""
        obj = mock.MagicMock()
        obj.key = "val"
        # make sure nokey is not set on mock
        del obj.nokey

        # raises error if attribute not set and val is none
        with pytest.raises(AttributeError) as conm:
            _set_default(obj, "nokey", None)
        assert conm.value.args[0] == "nokey is not set"

        result = _set_default(obj, "key", None)
        assert result is not None
        assert result == "val"

        # returns obj.key if not value is supplied
        result = _set_default(obj, "key", None)
        assert result is not None
        assert result == "val"

        # return value if supplied
        result = _set_default(obj, "key", "other")
        assert result is not None
        assert result == "other"

        # Return None if val and attr not set and required = False
        result = _set_default(obj, "nokey", None, required=False)
        assert result is None

    def test_get_urls(self):
        """test _get_urls correctly formats urls"""
        expected = {"test1": "base_url/test1", "test2": "base_url/test2"}
        result = _get_urls("base_url/", {"test1": "test1", "test2": "test2"})
        assert expected == result
