#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016-2016 Earth Advantage. All rights reserved.
..codeauthor::Paul Munday <paul@paulmunday.net>

Unit tests for pyseed/apibase
"""
# Imports from Standard Library
import sys
import unittest

# Local Imports
from pyseed.apibase import JSONAPI, BaseAPI, add_pk
from pyseed.exceptions import APIClientError
from pyseed.seedclient import _get_urls, _set_default

NO_URL_ERROR = "APIClientError: No url set"
SSL_ERROR = "APIClientError: use_ssl is true but url does not starts with https"
SSL_ERROR2 = "APIClientError: use_ssl is false but url starts with https"

# Constants
SERVICES_DICT = {
    'urls': {'test1': 'test1', 'test2': '/test2'}
}


PY3 = sys.version_info[0] == 3
if PY3:
    from unittest import mock
else:
    import mock


class MockConfig(object):
    """Mock config object"""
    # pylint:disable=too-few-public-methods, no-self-use

    def __init__(self, conf):
        self.conf = conf

    def get(self, var, section=None, default=None):
        if section:                                          # pragma: no cover
            cdict = self.conf.get(section, {})
        else:
            cdict = self.conf
        return cdict.get(var, default)


SERVICES = MockConfig(SERVICES_DICT)


@mock.patch('pyseed.apibase.requests')
class APITests(unittest.TestCase):
    """Tests for API base classes"""
    # pylint: disable=protected-access, no-self-use, unused-argument

    def setUp(self):
        self.url = 'example.org'
        self.api = JSONAPI(self.url)

    def test_ssl_verification(self, mock_requests):
        """Test ssl usage"""
        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            JSONAPI('http://example.org')
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if https is supplied and use_ssl is false
        with self.assertRaises(APIClientError) as conm:
            JSONAPI('https://example.org', use_ssl=False)
        exception = conm.exception
        expected = SSL_ERROR2
        self.assertEqual(expected, str(exception))

        # test defaults to https
        api = JSONAPI('example.org')
        api._get()
        mock_requests.get.assert_called_with(
            'https://example.org', timeout=None, headers=None
        )

        # use_ssl is False
        api = JSONAPI('example.org', use_ssl=False)
        api._get()
        mock_requests.get.assert_called_with(
            'http://example.org', timeout=None, headers=None
        )

    def test_get(self, mock_requests):
        """Test _get method."""
        self.api._get(id=1, foo='bar')
        mock_requests.get.assert_called_with(
            'https://example.org', params={'id': 1, 'foo': 'bar'},
            timeout=None, headers=None
        )

    def test_post(self, mock_requests):
        """Test _get_post."""
        params = {'id': 1}
        files = {'file': 'mock_file'}
        data = {'foo': 'bar', 'test': 'test'}
        self.api._post(params=params, files=files, foo='bar', test='test')
        mock_requests.post.assert_called_with(
            'https://example.org', params=params, files=files,
            json=data, timeout=None, headers=None
        )

        # Not json
        api = BaseAPI('example.org')
        api._post(params=params, files=files, foo='bar', test='test')
        mock_requests.post.assert_called_with(
            'https://example.org', params=params, files=files,
            data=data, timeout=None, headers=None
        )

    def test_patch(self, mock_requests):
        """Test _get_patch."""
        params = {'id': 1}
        files = {'file': 'mock_file'}
        data = {'foo': 'bar', 'test': 'test'}
        self.api._patch(params=params, files=files, foo='bar', test='test')
        mock_requests.patch.assert_called_with(
            'https://example.org', params=params, files=files,
            json=data, timeout=None, headers=None
        )

        # Not json
        api = BaseAPI('example.org')
        api._patch(params=params, files=files, foo='bar', test='test')
        mock_requests.patch.assert_called_with(
            'https://example.org', params=params, files=files,
            data=data, timeout=None, headers=None
        )

    def test_delete(self, mock_requests):
        """Test _delete method."""
        self.api._delete(id=1, foo='bar')
        mock_requests.delete.assert_called_with(
            'https://example.org', params={'id': 1, 'foo': 'bar'},
            timeout=None, headers=None
        )

    def test_construct_payload(self, mock_requests):
        """Test construct_payload  method."""
        with self.assertRaises(APIClientError):
            api = BaseAPI('example.org', compulsory_params=['id'])
            api._get(foo='bar')
        api._get(id=1)
        self.assertTrue(mock_requests.get.called)

        url = self.url

        class TestAPI(BaseAPI):
            """test class"""
            # pylint: disable=too-few-public-methods

            def __init__(self):
                self.compulsory_params = ['id', 'comp']
                super(TestAPI, self).__init__(url)
                self.comp = 1
        with self.assertRaises(APIClientError) as conm:
            api = TestAPI()
            api._get()
        exception = conm.exception
        self.assertEqual(
            'APIClientError: id is a compulsory field', str(exception)
        )
        api._get(id=1)
        self.assertTrue(mock_requests.get.called)

    def test_check_call_success(self, mock_requests):
        """Test check_call_success method."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        mock_requests.codes.ok = 200
        response = self.api._get(id=1)
        self.assertTrue(self.api.check_call_success(response))

    def test_construct_url(self, mock_requests):
        """Test _construct_url method."""
        api = BaseAPI(use_ssl=False)

        # ensure error is raised if no url  is supplied
        with self.assertRaises(APIClientError) as conm:
            api._construct_url(None)
        exception = conm.exception
        expected = NO_URL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if https is supplied and use_ssl is false
        with self.assertRaises(APIClientError) as conm:
            api._construct_url('https://www.example.org', use_ssl=False)
        exception = conm.exception
        expected = SSL_ERROR2
        self.assertEqual(expected, str(exception))

    def test_construct_url_ssl_explicit(self, mock_requests):
        """Test _construct_url method."""
        api = BaseAPI(use_ssl=True)

        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            api._construct_url('http://example.org', use_ssl=True)
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if http is supplied and use_ssl is default
        with self.assertRaises(APIClientError) as conm:
            api._construct_url('http://example.org')
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

    def test_construct_url_ssl_implicit(self, mock_requests):
        """Test _construct_url method."""
        api = BaseAPI()

        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            api._construct_url('http://example.org', use_ssl=True)
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if http is supplied and use_ssl is default
        with self.assertRaises(APIClientError) as conm:
            api._construct_url('http://example.org')
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))


@mock.patch('pyseed.apibase.requests')
class APITestsNoURL(unittest.TestCase):
    """Tests for API base classes with no self.url set"""
    # pylint: disable=protected-access, no-self-use, unused-argument

    def setUp(self):
        self.url = 'example.org'
        self.api = JSONAPI()

    def test_no_url(self, mock_requests):
        """Test ssl usage"""

    def test_get(self, mock_requests):
        """Test _get method."""
        self.api._get(self.url, id=1, foo='bar')
        mock_requests.get.assert_called_with(
            'https://example.org', params={'id': 1, 'foo': 'bar'},
            timeout=None, headers=None
        )

        # ensure error is raised if https is supplied and use_ssl is false
        with self.assertRaises(APIClientError) as conm:
            api = BaseAPI('example.org', use_ssl=False)
            api._get(url='https://www.example.org', use_ssl=False)
        exception = conm.exception
        expected = SSL_ERROR2
        self.assertEqual(expected, str(exception))

        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            self.api._get(url='http://example.org')
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if no url  is supplied
        with self.assertRaises(APIClientError) as conm:
            self.api._get()
        exception = conm.exception
        expected = NO_URL_ERROR
        self.assertEqual(expected, str(exception))

        # test defaults to http
        self.api._get(url=self.url)
        mock_requests.get.assert_called_with(
            'https://example.org', timeout=None, headers=None
        )

        # use_ssl is False
        api = BaseAPI('example.org', use_ssl=False)
        api._get(url=self.url, use_ssl=False)
        mock_requests.get.assert_called_with(
            'http://example.org', timeout=None, headers=None
        )

    def test_post(self, mock_requests):
        """Test _get_post."""
        params = {'id': 1}
        files = {'file': 'mock_file'}
        data = {'foo': 'bar', 'test': 'test'}
        self.api._post(
            url=self.url, params=params, files=files, foo='bar', test='test'
        )
        mock_requests.post.assert_called_with(
            'https://example.org', params=params, files=files,
            json=data, timeout=None, headers=None
        )

        # Not json
        api = BaseAPI()
        api._post(url=self.url, params=params, files=files,
                  foo='bar', test='test')
        mock_requests.post.assert_called_with(
            'https://example.org', params=params, files=files,
            data=data, timeout=None, headers=None
        )

        # ensure error is raised if no url  is supplied
        with self.assertRaises(APIClientError) as conm:
            self.api._post(
                params=params, files=files, foo='bar', test='test'
            )
        exception = conm.exception
        expected = NO_URL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if https is supplied and use_ssl is false
        with self.assertRaises(APIClientError) as conm:
            api = BaseAPI('example.org', use_ssl=False)
            api._post(
                url='https://example.org', use_ssl=False,
                params=params, files=files, foo='bar', test='test'
            )
        exception = conm.exception
        expected = SSL_ERROR2
        self.assertEqual(expected, str(exception))

        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            self.api._post(
                url='http://example.org', use_ssl=True,
                params=params, files=files, foo='bar', test='test'
            )
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

    def test_patch(self, mock_requests):
        """Test _get_patch."""
        params = {'id': 1}
        files = {'file': 'mock_file'}
        data = {'foo': 'bar', 'test': 'test'}
        self.api._patch(
            url=self.url, params=params, files=files, foo='bar', test='test'
        )
        mock_requests.patch.assert_called_with(
            'https://example.org', params=params, files=files,
            json=data, timeout=None, headers=None
        )

        # Not json
        api = BaseAPI('example.org')
        api._patch(
            url=self.url, params=params, files=files, foo='bar', test='test'
        )
        mock_requests.patch.assert_called_with(
            'https://example.org', params=params, files=files,
            data=data, timeout=None, headers=None
        )

        # ensure error is raised if no url  is supplied
        with self.assertRaises(APIClientError) as conm:
            self.api._patch(
                params=params, files=files, foo='bar', test='test'
            )
        exception = conm.exception
        expected = NO_URL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if https is supplied and use_ssl is false
        with self.assertRaises(APIClientError) as conm:
            api = BaseAPI('example.org', use_ssl=False)
            api._patch(
                url='https://example.org', use_ssl=False,
                params=params, files=files, foo='bar', test='test'
            )
        exception = conm.exception
        expected = SSL_ERROR2
        self.assertEqual(expected, str(exception))

        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            self.api._patch(
                url='http://example.org', use_ssl=True,
                params=params, files=files, foo='bar', test='test'
            )
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

    def test_delete(self, mock_requests):
        """Test _delete method."""
        self.api._delete(url=self.url, id=1, foo='bar')
        mock_requests.delete.assert_called_with(
            'https://example.org', params={'id': 1, 'foo': 'bar'},
            timeout=None, headers=None
        )

        # ensure error is raised if https is supplied and use_ssl is false
        with self.assertRaises(APIClientError) as conm:
            api = BaseAPI('example.org', use_ssl=False)
            api._delete(url='https://www.example.org')
        exception = conm.exception
        expected = SSL_ERROR2
        self.assertEqual(expected, str(exception))

        # ensure error is raised if http is supplied and use_ssl is true
        with self.assertRaises(APIClientError) as conm:
            self.api._delete(url='http://example.org')
        exception = conm.exception
        expected = SSL_ERROR
        self.assertEqual(expected, str(exception))

        # ensure error is raised if no url  is supplied
        with self.assertRaises(APIClientError) as conm:
            self.api._delete()
        exception = conm.exception
        expected = NO_URL_ERROR
        self.assertEqual(expected, str(exception))

        # test defaults to http
        self.api._delete(url=self.url)
        mock_requests.delete.assert_called_with(
            'https://example.org', timeout=None, headers=None
        )

        # use_ssl is False
        api = BaseAPI('example.org', use_ssl=False)
        api._delete(url=self.url, use_ssl=False)
        mock_requests.delete.assert_called_with(
            'http://example.org', timeout=None, headers=None
        )


class APIFunctionTest(unittest.TestCase):

    def testadd_pk(self):
        """Test add_pk helper function."""
        # Error checks
        with self.assertRaises(APIClientError) as conm:
            add_pk('url', None)
        self.assertEqual(
            'APIClientError: id/pk must be supplied', str(conm.exception)
        )

        with self.assertRaises(TypeError) as conm:
            add_pk('url', 'a')
        self.assertEqual(
            'id/pk must be a positive integer', str(conm.exception)
        )

        with self.assertRaises(TypeError) as conm:
            add_pk('url', 1.2)
        self.assertEqual(
            'id/pk must be a positive integer', str(conm.exception)
        )

        with self.assertRaises(TypeError) as conm:
            add_pk('url', -1)
        self.assertEqual(
            'id/pk must be a positive integer', str(conm.exception)
        )

        # adds ints
        result = add_pk('url', 1)
        self.assertEqual('url/1', result)

        # converts strings if digit
        result = add_pk('url', '1')
        self.assertEqual('url/1', result)

        # id not required
        result = add_pk('url', None, required=False)
        self.assertEqual('url', result)

        # adds_slash
        result = add_pk('url', 1, slash=True)
        self.assertEqual('url/1/', result)

        # does not repeat /
        result = add_pk('url/', 1)
        self.assertEqual('url/1', result)

    def test_set_default(self):
        """Test _set_default helper method"""
        obj = mock.MagicMock()
        obj.key = 'val'
        # make sure nokey is not set on mock
        del obj.nokey

        # raises error if attribute not set and val is none
        with self.assertRaises(AttributeError) as conm:
            _set_default(obj, 'nokey', None)
        self.assertEqual('nokey is not set', str(conm.exception))

        result = _set_default(obj, 'key', None)
        self.assertNotEqual(result, None)
        self.assertEqual(result, 'val')

        # returns obj.key if not value is supplied
        result = _set_default(obj, 'key', None)
        self.assertNotEqual(result, None)
        self.assertEqual(result, 'val')

        # return value if supplied
        result = _set_default(obj, 'key', 'other')
        self.assertNotEqual(result, None)
        self.assertEqual(result, 'other')

        # Return None if val and attr not set and required = False
        result = _set_default(obj, 'nokey', None, required=False)
        self.assertEqual(result, None)

    def test_get_urls(self):
        """test _get_urls correctly formats urls"""
        expected = {'test1': 'base_url/test1', 'test2': 'base_url/test2'}
        result = _get_urls(
            'base_url/', {'test1': 'test1', 'test2': 'test2'}
        )
        self.assertDictEqual(expected, result)
