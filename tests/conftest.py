from unittest import mock

import pytest

from pyseed.seed_client import SeedClient


@pytest.fixture
def seed_client() -> SeedClient:
    """SeedClient with a mocked API client; skips __init__, which needs a live SEED connection config."""
    client = SeedClient.__new__(SeedClient)
    client.client = mock.MagicMock()
    return client
