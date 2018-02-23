#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016  Earth Advantage.
All rights reserved

Tests for SEEDClient
"""

# Imports from Standard Library
import json
import sys
import unittest

# Imports from Third Party Modules
import requests

# Local Imports
from pyseed.exceptions import SEEDError
from pyseed.seedclient import (  # SEEDReadWriteClient,
    ReadMixin,
    SEEDBaseClient,
    SEEDOAuthReadWriteClient,
)

PY3 = sys.version_info[0] == 3
if PY3:
    from unittest import mock
else:
    import mock

# Constants
URLS = {
    'test1': 'api/v2/test',
    'test2': 'api/v2/test2',
    'test3': 'api/v2/test3',
}

CONFIG_DICT = {
    'port': 1337,
    'urls_key': 'urls',
    'base_url': 'example.org'
}

SERVICES_DICT = {
    'seed': {
        'urls': URLS,

    }
}


class MockConfig(object):
    """Mock config object"""
    # pylint:disable=too-few-public-methods, no-self-use

    def __init__(self, conf):
        self.conf = conf

    def get(self, var, section=None, default=None):
        if section:
            cdict = self.conf.get(section, {})
        else:
            cdict = self.conf
        return cdict.get(var, default)


CONFIG = MockConfig(CONFIG_DICT)
SERVICES = MockConfig(SERVICES_DICT)


# Helper Functions & Classes
class MySeedClient(ReadMixin, SEEDBaseClient):
    # pylint:disable=too-few-public-methods
    endpoint = 'test1'


class MockOAuthClient(object):

    def __init__(self, sig, username, client_id):
        pass

    def get_access_token(self):
        return 'dfghjk'


def get_mock_response(data=None, data_name='data', error=False,
                      status_code=200, method='get',
                      base_url=CONFIG_DICT['base_url'],
                      endpoint='test1', extra=None, https=False,
                      content=True):
    """Create mock response in the style of SEED"""
    # pylint:disable=too-many-arguments
    status = 'error' if error else 'success'
    mock_request = mock.MagicMock()
    url = "{}://{}/{}/".format(
        'https' if https else 'http',
        base_url,
        URLS[endpoint]
    )
    if extra:                                                # pragma: no cover
        url = url + extra
    mock_request.url = url
    mock_request.method = method
    mock_response = mock.MagicMock()
    mock_response.status_code = status_code
    mock_response.request = mock_request
    # SEED old style
    if content:
        if error:
            data_name = 'message'
        content_dict = {'status': status, data_name: data}
        mock_response.content = json.dumps(content_dict)
        mock_response.json.return_value = content_dict
    else:
        mock_response.content = None
    return mock_response


# Tests
@mock.patch('pyseed.apibase.requests')
class SEEDClientErrorHandlingTests(unittest.TestCase):
    """
    The error handling uses the inspect module to examine the stack
    to get the calling function for the error message.

    Since SEEDBaseClient is only intended for inheritance the stack
    inspections counts up to get the right function name
    """

    def setUp(self):
        self.port = 1137
        self.urls_map = URLS
        self.base_url = 'example.org'
        print(self.urls_map)
        self.client = MySeedClient(
            1, username='test@example.org', access_token='dfghj',
            base_url=self.base_url, port=self.port, url_map=self.urls_map
        )

    def test_check_response_inheritance(self, mock_requests):
        """
        Ensure errors are correctly reported.

        SEEDError should show the calling method where the error occured.
        It uses the inspect module to get the calling method from the stack.

        Error called in _check_response(), this also tests that method
        as well as _raise_error().
        """
        url = 'http://example.org/api/v2/test/'
        # Old SEED Style 200 (sic) with error message
        mock_requests.get.return_value = get_mock_response(
            data="No llama!", error=True
        )
        with self.assertRaises(SEEDError) as conm:
            self.client.get(1)

        self.assertEqual(conm.exception.error, 'No llama!')
        self.assertEqual(conm.exception.service, 'SEED')
        self.assertEqual(conm.exception.url, url)
        self.assertEqual(conm.exception.caller, 'MySeedClient.get')
        self.assertEqual(conm.exception.verb.upper(), 'GET')
        self.assertEqual(conm.exception.status_code, 200)

        # newer/correct using status codes (no message)
        mock_requests.get.return_value = get_mock_response(
            status_code=404, data="No llama!", error=True, content=False
        )
        with self.assertRaises(SEEDError) as conm:
            self.client.get(1)

        self.assertEqual(
            conm.exception.error, 'SEED returned status code: 404'
        )
        self.assertEqual(conm.exception.service, 'SEED')
        self.assertEqual(conm.exception.url, url)
        self.assertEqual(conm.exception.caller, 'MySeedClient.get')
        self.assertEqual(conm.exception.verb.upper(), 'GET')
        self.assertEqual(conm.exception.status_code, 404)

        # newer/correct using status codes (with message)
        mock_requests.get.return_value = get_mock_response(
            status_code=404, data="No llama!", error=True, content=True
        )
        with self.assertRaises(SEEDError) as conm:
            self.client.get(1)

        self.assertEqual(
            conm.exception.error, 'No llama!'
        )
        self.assertEqual(conm.exception.service, 'SEED')
        self.assertEqual(conm.exception.url, url)
        self.assertEqual(conm.exception.caller, 'MySeedClient.get')
        self.assertEqual(conm.exception.verb.upper(), 'GET')
        self.assertEqual(conm.exception.status_code, 404)

    def test_get_result(self, mock_requests):
        """Test errors raised in _get_result"""
        url = 'http://example.org/api/v2/test/'
        mock_requests.get.return_value = get_mock_response(
            data="No llama!", data_name='bar', error=False,
        )
        with self.assertRaises(SEEDError) as conm:
            self.client.get(1)

        self.assertEqual(
            conm.exception.error, 'Could not find result using data_name test.'
        )
        self.assertEqual(conm.exception.service, 'SEED')
        self.assertEqual(conm.exception.url, url)
        self.assertEqual(conm.exception.verb.upper(), 'GET')
        self.assertEqual(conm.exception.status_code, 200)


class SEEDClientMethodTests(unittest.TestCase):

    def setUp(self):
        self.port = 1137
        self.urls_map = URLS
        self.base_url = 'example.org'
        self.client = MySeedClient(
            1, username='test@example.org', access_token='dfghj',
            base_url=self.base_url, port=self.port, url_map=self.urls_map
        )

    def test_init(self):
        """Test init sets params correctly"""
        urls = {
            key: "{}:{}/{}".format(
                self.base_url, self.port, val
            ) for key, val in URLS.items()
        }
        self.assertTrue(self.client.use_ssl)
        self.assertTrue(self.client.use_json)
        self.assertEqual(1, self.client.org_id)
        self.assertEqual(
            "{}:{}/".format(
                self.base_url, self.port
            ),
            self.client.base_url
        )
        self.assertEqual('test1', self.client.endpoint)
        self.assertEqual(None, self.client.data_name)
        self.assertEqual(urls, self.client.urls)
        self.assertEqual(URLS.keys(), self.client.endpoints)
        self.assertEqual('test1', self.client.endpoint)

    def test_get_result(self):
        """Test _get_result method."""
        response = get_mock_response(data='test')
        result = self.client._get_result(response)
        self.assertEqual('test', result)


@mock.patch('pyseed.apibase.requests')
class MixinTests(unittest.TestCase):
    """Test Mixins via SEEDReadWriteClient"""

    def setUp(self):
        self.port = 1337
        self.urls_map = URLS
        self.base_url = 'example.org'
        self.client = SEEDOAuthReadWriteClient(
            1, username='test@example.org',
            access_token='dfghjk', base_url=self.base_url,
            port=self.port, url_map=self.urls_map, oauth_client=MockOAuthClient
        )
        self.call_dict = {
            'headers': {'Authorization': 'Bearer dfghjk'},
            'params': {
                'org_id': 1,
                'headers': {'Authorization': 'Bearer dfghjk'}
            },
            'timeout': None
        }

    def test_delete(self, mock_requests):
        # pylint:disable=no-member
        url = 'https://example.org:1337/api/v2/test/1/'
        mock_requests.delete.return_value = get_mock_response(
            status_code=requests.codes.no_content
        )
        result = self.client.delete(1, endpoint='test1')
        self.assertEqual(None, result)
        mock_requests.delete.assert_called_with(url, **self.call_dict)

    def test_get(self, mock_requests):
        url = 'https://example.org:1337/api/v2/test/1/'
        mock_requests.get.return_value = get_mock_response(data="Llama!")
        result = self.client.get(1, endpoint='test1')
        self.assertEqual('Llama!', result)
        mock_requests.get.assert_called_with(url, **self.call_dict)

    def test_list(self, mock_requests):
        url = 'https://example.org:1337/api/v2/test/'
        mock_requests.get.return_value = get_mock_response(data=["Llama!"])
        result = self.client.list(endpoint='test1')
        self.assertEqual(['Llama!'], result)
        mock_requests.get.assert_called_with(url, **self.call_dict)

    def test_patch(self, mock_requests):
        url = 'https://example.org:1337/api/v2/test/1/'
        mock_requests.patch.return_value = get_mock_response(data="Llama!")
        result = self.client.patch(1, endpoint='test1', foo='bar')
        self.assertEqual('Llama!', result)

        call_dict = self.call_dict.copy()
        call_dict['json'] = {'org_id': 1, 'foo': 'bar'}
        del call_dict['params']['org_id']
        mock_requests.patch.assert_called_with(url, **call_dict)

    def test_put(self, mock_requests):
        url = 'https://example.org:1337/api/v2/test/1/'
        mock_requests.put.return_value = get_mock_response(data="Llama!")
        result = self.client.put(1, endpoint='test1', foo='bar')
        self.assertEqual('Llama!', result)

        call_dict = self.call_dict.copy()
        call_dict['json'] = {'org_id': 1, 'foo': 'bar'}
        del call_dict['params']['org_id']
        mock_requests.put.assert_called_with(url, **call_dict)

    def test_post(self, mock_requests):
        url = 'https://example.org:1337/api/v2/test/'
        mock_requests.post.return_value = get_mock_response(data="Llama!")
        result = self.client.post(endpoint='test1', foo='bar')
        self.assertEqual('Llama!', result)

        call_dict = self.call_dict.copy()
        call_dict['json'] = {'org_id': 1, 'foo': 'bar'}
        del call_dict['params']['org_id']
        mock_requests.post.assert_called_with(url, **call_dict)
