"""Conftest for tests of the Wiener Netze Smart Meter API client.

This module provides common fixtures used across the test suite. In particular,
it defines a 'client' fixture that creates a WNAPIClient instance configured with
fast retry delays to speed up tests.
"""

# tests/conftest.py

import pytest

from wiener_netze_smart_meter_api.client import WNAPIClient


@pytest.fixture
def client() -> WNAPIClient:
    """Create a WNAPIClient instance for testing with fast retry delays.

    Returns:
        WNAPIClient: A configured instance of the client.

    """
    return WNAPIClient(
        client_id="test_id",
        client_secret="test_secret",  # noqa: S106
        api_key="test_api_key",
        max_retries=2,
        retry_delay=0,  # speed up tests
        timeout=5,
    )
