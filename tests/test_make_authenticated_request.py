"""Tests for the make_authenticated_request method of the WNAPIClient.

This module verifies that:
  - A successful GET request returns the expected JSON response.
  - A successful POST request returns the expected JSON response.
  - Unsupported HTTP methods result in a NotImplementedError.
  - When no valid token is available, the method returns None.
  - Timeout exceptions are caught and a warning is logged, eventually raising WNAPIRequestError.
  - Generic RequestExceptions are caught and logged, eventually raising WNAPIRequestError.
  - An HTTP error with a non-401 status code eventually raises WNAPIRequestError.
  - An HTTP 401 error causes token invalidation and, after max retries, raises WNAPIAuthenticationError.

Usage:
    python -m pytest tests/test_make_authenticated_request.py
"""  # noqa: E501

import time
from typing import Any

import pytest
import requests

from tests.fake_response import FakeResponse
from wiener_netze_smart_meter_api.client import WNAPIClient
from wiener_netze_smart_meter_api.exceptions import (
    WNAPIAuthenticationError,
    WNAPIRequestError,
)


def test_make_authenticated_request_get_success(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that a successful GET request returns the expected JSON response."""
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(json_data={"result": "ok"})

    monkeypatch.setattr(client.session, "get", fake_get)
    result = client.make_authenticated_request("http://example.com", method="GET")
    assert result == {"result": "ok"}


def test_make_authenticated_request_post_success(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that a successful POST request returns the expected JSON response."""
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(json_data={"result": "posted"})

    monkeypatch.setattr(client.session, "post", fake_post)
    result = client.make_authenticated_request(
        "http://example.com",
        method="POST",
        data={"key": "value"},
    )
    assert result == {"result": "posted"}


def test_make_authenticated_request_invalid_method(client: WNAPIClient) -> None:
    """Test that an unsupported HTTP method raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        client.make_authenticated_request("http://example.com", method="PUT")
    assert "HTTP method PUT is not supported." in str(excinfo.value)


def test_make_authenticated_request_no_token(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that make_authenticated_request returns None when no valid token is available."""  # noqa: E501
    monkeypatch.setattr(client, "get_bearer_token", lambda: None)
    result = client.make_authenticated_request("http://example.com", method="GET")
    assert result is None


def test_make_authenticated_request_timeout(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a Timeout in make_authenticated_request logs an appropriate warning and raises WNAPIRequestError.

    This test simulates a timeout exception, verifies that a warning containing the timeout message is logged,
    and asserts that a WNAPIRequestError is raised after exhausting retries.
    """  # noqa: E501
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get_timeout(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401, ARG001
        msg = "Simulated timeout"
        raise requests.Timeout(msg)

    monkeypatch.setattr(client.session, "get", fake_get_timeout)

    with pytest.raises(WNAPIRequestError):
        client.make_authenticated_request("http://example.com", method="GET")
    assert "Timeout on GET request to http://example.com" in caplog.text


def test_make_authenticated_request_request_exception(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a generic RequestException in make_authenticated_request is caught, logged, and eventually results in a WNAPIRequestError.

    This test simulates a RequestException, verifies that the log contains "Request error occurred", and asserts that
    a WNAPIRequestError is raised.
    """  # noqa: E501
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get_request_exception(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401, ARG001
        msg = "Simulated request error"
        raise requests.RequestException(msg)

    monkeypatch.setattr(client.session, "get", fake_get_request_exception)
    with pytest.raises(WNAPIRequestError):
        client.make_authenticated_request("http://example.com", method="GET")
    assert "Request error occurred" in caplog.text


def test_make_authenticated_request_http_error_non_unauthorized(
    monkeypatch: pytest.MonkeyPatch, client: WNAPIClient,
) -> None:
    """Test that an HTTP error with a non-401 status code in make_authenticated_request eventually raises WNAPIRequestError.

    This test simulates a 500 error and asserts that after retries, a WNAPIRequestError is raised with an appropriate message.
    """  # noqa: E501
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get_500(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(status_code=500, json_data={"error": "Server error"})

    monkeypatch.setattr(client.session, "get", fake_get_500)
    with pytest.raises(WNAPIRequestError) as excinfo:
        client.make_authenticated_request("http://example.com", method="GET")
    assert "Max retries reached. Unable to complete request" in str(excinfo.value)


def test_make_authenticated_request_http_error_unauthorized(
    monkeypatch: pytest.MonkeyPatch, client: WNAPIClient,
) -> None:
    """Test that an HTTP 401 error causes get_bearer_token to fail and eventually raises WNAPIAuthenticationError, and that the token is invalidated.

    This test simulates a 401 error, verifies that after max retries a WNAPIAuthenticationError is raised,
    and checks that the token is set to None.
    """  # noqa: E501
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(status_code=401, json_data={"error": "Unauthorized"})

    monkeypatch.setattr(client.session, "get", fake_get)
    with pytest.raises(WNAPIAuthenticationError) as excinfo:
        client.make_authenticated_request("http://example.com", method="GET")
    assert "Max retries reached. Unable to obtain token" in str(excinfo.value)
    assert client.token is None
