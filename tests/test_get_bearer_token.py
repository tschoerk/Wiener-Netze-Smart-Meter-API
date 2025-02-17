"""Tests for the get_bearer_token method of the WNAPIClient class.

This module verifies that:
  - A successful token retrieval returns the expected token.
  - If JSON decoding fails during token retrieval, a ValueError is raised.
  - If the network call repeatedly fails, a WNAPIAuthenticationError is raised.

Usage:
    python -m pytest tests/test_get_bearer_token.py
"""

from typing import Any

import pytest
import requests

from tests.fake_response import FakeResponse
from wiener_netze_smart_meter_api.client import WNAPIClient
from wiener_netze_smart_meter_api.exceptions import WNAPIAuthenticationError


def test_get_bearer_token_success(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Simulate a successful token retrieval and verify that the returned token is correct."""  # noqa: E501

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(json_data={"access_token": "abc", "expires_in": 300})

    monkeypatch.setattr(client.session, "post", fake_post)
    token = client.get_bearer_token()
    assert token == "abc"  # noqa: S105


def test_get_bearer_token_json_failure(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_bearer_token raises a ValueError when JSON decoding fails."""

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(raise_on_json=True)

    monkeypatch.setattr(client.session, "post", fake_post)
    with pytest.raises(ValueError, match="JSON decoding failed for token response"):
        client.get_bearer_token()


def test_get_bearer_token_network_failure(
    monkeypatch: pytest.MonkeyPatch, client: WNAPIClient,
) -> None:
    """Test that get_bearer_token raises WNAPIAuthenticationError when network failures persist."""  # noqa: E501

    def fake_post(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401, ARG001
        msg = "Network error"
        raise requests.RequestException(msg)

    monkeypatch.setattr(client.session, "post", fake_post)
    with pytest.raises(WNAPIAuthenticationError) as excinfo:
        client.get_bearer_token()
    assert "Max retries reached. Unable to obtain token" in str(excinfo.value)
