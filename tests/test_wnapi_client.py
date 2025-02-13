"""Tests for the WNAPIClient.

This test suite verifies:
  - The correct calculation of date ranges.
  - Successful and failing token retrieval.
  - Successful GET and POST requests.
  - That proper custom exceptions are raised when maximum retries are exceeded.

Usage:
    pytest tests/test_wnapi_client.py
"""

from __future__ import annotations

import datetime
import time
from typing import Any, ClassVar

import pytest
import requests
from dateutil.relativedelta import relativedelta
from requests.exceptions import RequestException

from wiener_netze_smart_meter_api.client import WNAPIClient
from wiener_netze_smart_meter_api.exceptions import (
    WNAPIAuthenticationError,
    WNAPIRequestError,
)


class FakeResponse:
    """A fake response object to simulate requests.Response for testing purposes.

    Attributes:
        HTTP_ERROR_THRESHOLD (ClassVar[int]): The threshold status code for errors.

    """

    HTTP_ERROR_THRESHOLD: ClassVar[int] = 400

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> None:
        """Initialize a FakeResponse.

        Args:
            status_code (int, optional): HTTP status code. Defaults to 200.
            json_data (dict | None, optional): The JSON data to return. Defaults to {}.
            headers (dict | None, optional): HTTP headers. Defaults to {"Content-Type": "application/json"}.

        """  # noqa: E501
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {"Content-Type": "application/json"}

    def raise_for_status(self) -> None:
        """Raise an HTTPError if the status code is 400 or above."""
        if self.status_code >= self.HTTP_ERROR_THRESHOLD:
            raise requests.HTTPError(response=self)

    def json(self) -> dict:
        """Return the JSON data.

        Returns:
            dict: The stored JSON data.

        """
        return self._json_data


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
        retry_delay=0,  # Set to 0 to speed up tests.
    )


def test_calculate_date_range_both() -> None:
    """Test that when both dates are provided, they are returned unchanged."""
    client_instance = WNAPIClient("id", "secret", "api_key")
    start, end = client_instance.calculate_date_range("2024-01-01", "2024-12-31")
    assert start == "2024-01-01"  # noqa: S101
    assert end == "2024-12-31"  # noqa: S101


def test_calculate_date_range_neither() -> None:
    """Test that when neither date is provided, defaults are set to 3 years ago to today."""  # noqa: E501
    client_instance = WNAPIClient("id", "secret", "api_key")
    start, end = client_instance.calculate_date_range(None, None)
    now = datetime.datetime.now(datetime.timezone.utc)
    expected_start = (now - relativedelta(years=3)).strftime("%Y-%m-%d")
    expected_end = now.strftime("%Y-%m-%d")
    assert start == expected_start  # noqa: S101
    assert end == expected_end  # noqa: S101


def test_calculate_date_range_only_start() -> None:
    """Test that when only the starting date is provided, the ending date defaults to today."""  # noqa: E501
    client_instance = WNAPIClient("id", "secret", "api_key")
    start, end = client_instance.calculate_date_range("2024-01-01", None)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    assert start == "2024-01-01"  # noqa: S101
    assert end == now  # noqa: S101


def test_calculate_date_range_only_end() -> None:
    """Test that when only the ending date is provided, the starting date is 3 years before the ending date."""  # noqa: E501
    client_instance = WNAPIClient("id", "secret", "api_key")
    start, end = client_instance.calculate_date_range(None, "2024-12-31")
    expected_start = (
        datetime.datetime.strptime("2024-12-31", "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc,
        )
        - relativedelta(years=3)
    ).strftime("%Y-%m-%d")
    assert start == expected_start  # noqa: S101
    assert end == "2024-12-31"  # noqa: S101


def test_get_bearer_token_success(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Simulate a successful token retrieval.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(json_data={"access_token": "abc", "expires_in": 300})

    monkeypatch.setattr(client.session, "post", fake_post)
    token = client.get_bearer_token()
    assert token == "abc"  # noqa: S101, S105


def test_get_bearer_token_failure(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Simulate a token retrieval failure and ensure a custom exception is raised.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """

    def fake_post(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401, ARG001
        msg = "Test failure"
        raise RequestException(msg)

    monkeypatch.setattr(client.session, "post", fake_post)
    with pytest.raises(WNAPIAuthenticationError):
        client.get_bearer_token()


def test_make_authenticated_request_get_success(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test a successful GET request.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """
    # Assume token is already valid.
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(json_data={"result": "ok"})

    monkeypatch.setattr(client.session, "get", fake_get)
    result = client.make_authenticated_request("http://example.com", method="GET")
    assert result == {"result": "ok"}  # noqa: S101


def test_make_authenticated_request_post_success(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test a successful POST request.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:  # noqa: ANN401, ARG001
        return FakeResponse(json_data={"result": "posted"})

    monkeypatch.setattr(client.session, "post", fake_post)
    result = client.make_authenticated_request(
        "http://example.com", method="POST", data={"key": "value"},
    )
    assert result == {"result": "posted"}  # noqa: S101


def test_make_authenticated_request_failure(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that an API request failure raises the custom WNAPIRequestError.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """
    client.token = "abc"  # noqa: S105
    client.token_expiry = time.time() + 1000

    def fake_get(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401, ARG001
        msg = "Network error"
        raise RequestException(msg)

    monkeypatch.setattr(client.session, "get", fake_get)
    with pytest.raises(WNAPIRequestError):
        client.make_authenticated_request("http://example.com", method="GET")
