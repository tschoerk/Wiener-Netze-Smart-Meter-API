"""Tests for get_anlagendaten functionality in the WNAPIClient.

This module verifies that:
  - When a meter identifier (zaehlpunkt) is provided, get_anlagendaten returns a dictionary
    containing the specific meter details.
  - When no meter identifier is provided, get_anlagendaten returns a dictionary with the aggregated
    data for all meters, including the 'resultType' parameter.

A fake implementation of make_authenticated_request is used to simulate API responses.

Usage:
    python -m pytest tests/test_get_anlagendaten.py
"""  # noqa: E501

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

    from wiener_netze_smart_meter_api.client import WNAPIClient


def fake_make_authenticated_request_anlagendaten(
    endpoint: str,
    method: str = "GET",  # noqa: ARG001
    params: dict | None = None,
) -> dict:
    """Fake implementation of make_authenticated_request for get_anlagendaten tests.

    Args:
        endpoint (str): The API endpoint URL.
        method (str, optional): HTTP method. Defaults to "GET".
        params (dict | None, optional): Query parameters.

    Returns:
        dict: A fake API response.

    """
    if "zaehlpunkte/TEST_METER" in endpoint:
        return {"zaehlpunkt": "TEST_METER", "data": "meter details"}
    if endpoint.endswith("zaehlpunkte") and params is not None:
        assert params.get("resultType") == "ALL"
        return {"data": "all meters", "resultType": "ALL"}
    return {}


def test_get_anlagendaten_with_meter(
    monkeypatch: pytest.MonkeyPatch, client: WNAPIClient,
) -> None:
    """Test that get_anlagendaten returns specific meter details when a meter identifier is provided.

    This test monkeypatches make_authenticated_request to return a fake response containing
    details for a meter with identifier "TEST_METER" and asserts that the response is as expected.
    """  # noqa: E501
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_anlagendaten,
    )
    result = client.get_anlagendaten("TEST_METER")
    assert isinstance(result, dict)
    assert result["zaehlpunkt"] == "TEST_METER"


def test_get_anlagendaten_without_meter(
    monkeypatch: pytest.MonkeyPatch, client: WNAPIClient,
) -> None:
    """Test that get_anlagendaten returns aggregated data when no meter identifier is provided.

    This test monkeypatches make_authenticated_request to return a fake aggregated response
    (with a resultType of "ALL") and asserts that the response matches the expected structure.
    """  # noqa: E501
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_anlagendaten,
    )
    result = client.get_anlagendaten()
    assert isinstance(result, dict)
    assert result.get("resultType") == "ALL"
