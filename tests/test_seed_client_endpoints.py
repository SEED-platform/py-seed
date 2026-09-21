"""Regression coverage for registered endpoint names and full URLs."""

import json
from unittest import mock

import pytest
import requests

from pyseed.exceptions import APIClientError, SEEDError
from pyseed.seed_client_base import SEEDReadWriteClient

METHODS = ("get", "list", "post", "put", "patch", "delete")
PK_METHODS = ("get", "put", "patch", "delete")


@pytest.fixture
def endpoint_client():
    return SEEDReadWriteClient(
        1,
        username="user@example.org",
        api_key="test-key",
        base_url="https://example.org",
        url_map={"registered": "/api/v3/items/"},
    )


def make_response(method, url, status_code=200):
    response = requests.Response()
    response.status_code = status_code
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps({"status": "success", "data": {"name": "Army"}}).encode()
    response.request = requests.Request(method.upper(), url).prepare()
    return response


def call_endpoint(client, method, pk=7, **kwargs):
    args = (pk,) if method in PK_METHODS else ()
    return getattr(client, method)(*args, **kwargs)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize(
    ("endpoint", "base_url"),
    [
        ("registered", "https://example.org/api/v3/items/"),
        ("https://example.org/api/v3/unregistered", "https://example.org/api/v3/unregistered/"),
        ("https://example.org/api/v3/unregistered/", "https://example.org/api/v3/unregistered/"),
    ],
)
def test_endpoint_names_and_full_urls(endpoint_client, method, endpoint, base_url):
    url = base_url + "7/" if method in PK_METHODS else base_url
    http_method = "get" if method == "list" else method
    response = make_response(http_method, url)
    payload = {"json": {"name": "Army"}} if method in ("post", "put", "patch") else {}

    with mock.patch(f"pyseed.apibase.requests.{http_method}", return_value=response) as request:
        result = call_endpoint(endpoint_client, method, endpoint=endpoint, data_name="all", **payload)

    request.assert_called_once_with(
        url,
        timeout=None,
        headers=None,
        params={"organization_id": 1},
        auth=requests.auth.HTTPBasicAuth("user@example.org", "test-key"),
        **payload,
    )
    assert result == response.json()


@pytest.mark.parametrize("method", METHODS)
def test_complete_http_url_with_template_parameters(endpoint_client, method):
    endpoint_client.use_ssl = False
    endpoint = "http://localhost:8000/api/v3/organizations/ORG_ID/access_levels/INSTANCE_ID/edit_instance/"
    url = "http://localhost:8000/api/v3/organizations/1/access_levels/7/edit_instance/"
    http_method = "get" if method == "list" else method
    response = make_response(http_method, url)
    payload = {"json": {"name": "Army"}} if method in ("post", "put", "patch") else {}
    pk_options = {"required_pk": False} if method in PK_METHODS else {}

    with mock.patch(f"pyseed.apibase.requests.{http_method}", return_value=response) as request:
        result = call_endpoint(
            endpoint_client,
            method,
            pk=None,
            endpoint=endpoint,
            url_args={"ORG_ID": 1, "INSTANCE_ID": 7},
            data_name="all",
            **pk_options,
            **payload,
        )

    request.assert_called_once_with(
        url,
        timeout=None,
        headers=None,
        params={"organization_id": 1},
        auth=requests.auth.HTTPBasicAuth("user@example.org", "test-key"),
        **payload,
    )
    assert result == response.json()


@pytest.mark.parametrize("method", PK_METHODS)
@pytest.mark.parametrize(("pk", "error"), [(None, APIClientError), (-1, TypeError)])
def test_full_urls_preserve_primary_key_validation(endpoint_client, method, pk, error):
    with pytest.raises(error):
        call_endpoint(endpoint_client, method, pk=pk, endpoint="https://example.org/api/v3/items/")


@pytest.mark.parametrize("method", METHODS)
def test_unknown_endpoint_names_preserve_errors(endpoint_client, method):
    if method == "post":
        with pytest.raises(Exception, match="Unknown endpoint: missing"):
            call_endpoint(endpoint_client, method, endpoint="missing")
    else:
        with pytest.raises(KeyError, match="missing"):
            call_endpoint(endpoint_client, method, endpoint="missing")


@pytest.mark.parametrize("method", METHODS)
def test_full_urls_preserve_seed_errors(endpoint_client, method):
    url = "https://example.org/api/v3/items/"
    http_method = "get" if method == "list" else method
    response = make_response(http_method, url, status_code=403)
    pk_options = {"required_pk": False} if method in PK_METHODS else {}

    with mock.patch(f"pyseed.apibase.requests.{http_method}", return_value=response), pytest.raises(SEEDError) as error:
        call_endpoint(endpoint_client, method, pk=None, endpoint=url, **pk_options)

    assert error.value.status_code == 403
    assert error.value.url == url
    assert error.value.verb == http_method.upper()
