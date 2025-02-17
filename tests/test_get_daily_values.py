"""Tests for get_daily_values functionality in the WNAPIClient.

These tests verify that:
  - When a specific meter ("test_meter") is requested without pagination, get_daily_values returns a full-range response as a dictionary.
  - When pagination is enabled for a single meter, the aggregated response (a dict) matches the full-range response.
  - When no meter is specified and multiple meter responses are returned, get_daily_values aggregates them into a list.

Fake implementations of get_messwerte are used to simulate API responses.

Usage:
    python -m pytest tests/test_get_daily_values.py
"""  # noqa: E501

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

    from wiener_netze_smart_meter_api.client import WNAPIClient


def fake_get_messwerte_day(
    wertetyp: str,
    zaehlpunkt: str | None,
    datum_von: str,
    datum_bis: str,
) -> dict | None:
    """Fake get_messwerte for DAY tests for a single meter 'test_meter'.

    Returns a fake full-range response when the full date range is provided, and chunk responses
    for sub-ranges.
    """  # noqa: E501
    if wertetyp != "DAY" or zaehlpunkt != "test_meter":
        return None
    if datum_von == "2025-01-01" and datum_bis == "2025-01-04":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 1000,
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 1100,
                            "zeitVon": "2025-01-02T23:00:00.000Z",
                            "zeitBis": "2025-01-03T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 1200,
                            "zeitVon": "2025-01-03T23:00:00.000Z",
                            "zeitBis": "2025-01-04T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-01" and datum_bis == "2025-01-02":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 1000,
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-02" and datum_bis == "2025-01-03":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 1100,
                            "zeitVon": "2025-01-02T23:00:00.000Z",
                            "zeitBis": "2025-01-03T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-03" and datum_bis == "2025-01-04":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 1200,
                            "zeitVon": "2025-01-03T23:00:00.000Z",
                            "zeitBis": "2025-01-04T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    return None


def test_get_daily_values_non_paginated(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_daily_values without pagination returns the full-range response as a dict for a single meter."""  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_day)
    result = client.get_daily_values("test_meter", "2025-01-01", "2025-01-04")
    expected = fake_get_messwerte_day("DAY", "test_meter", "2025-01-01", "2025-01-04")
    assert isinstance(result, dict)
    assert result == expected


def test_get_daily_values_paginated(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_daily_values with pagination aggregates chunk responses correctly for a single meter.

    This test simulates a full-range response and verifies that the paginated aggregation
    returns the same result.
    """  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_day)
    expected = fake_get_messwerte_day("DAY", "test_meter", "2025-01-01", "2025-01-04")
    result = client.get_daily_values(
        "test_meter",
        "2025-01-01",
        "2025-01-04",
        paginate=True,
        chunk_days=1,
    )
    assert isinstance(result, dict)
    assert result == expected


def fake_get_daily_values_multiple_zp(
    wertetyp: str,
    zaehlpunkt: str | None,
    datum_von: str,  # noqa: ARG001
    datum_bis: str,  # noqa: ARG001
) -> list[dict] | None:
    """Fake get_daily_values for simulating responses for multiple meters when no specific meter is requested.

    Returns a list of responses for two different meters.
    """  # noqa: E501
    if wertetyp != "DAY" or zaehlpunkt is not None:
        return None

    return [
        {
            "zaehlpunkt": "AT0010000000000000001000000000001",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 11000,
                            "qualitaet": "VAL",
                            "zeitVon": "2024-12-31T23:00:00.000Z",
                            "zeitBis": "2025-01-01T23:00:00.000Z",
                        },
                        {
                            "messwert": 10000,
                            "qualitaet": "VAL",
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                        },
                    ],
                },
            ],
        },
        {
            "zaehlpunkt": "AT0010000000000000001000000000002",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:2.9.0",
                    "messwerte": [
                        {
                            "messwert": 40,
                            "qualitaet": "VAL",
                            "zeitVon": "2024-12-31T23:00:00.000Z",
                            "zeitBis": "2025-01-01T23:00:00.000Z",
                        },
                        {
                            "messwert": 20,
                            "qualitaet": "VAL",
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                        },
                    ],
                },
            ],
        },
    ]


def test_get_daily_values_paginated_multiple_zp(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_daily_values with pagination aggregates responses correctly when multiple meters are returned.

    This test simulates a scenario where the API returns data for two different meters.
    When no specific meter is requested, the paginated call should return a list containing two dictionaries,
    one per meter, with the correct meter identifiers.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """  # noqa: E501
    expected_multiple_zp_list_length = 2
    monkeypatch.setattr(client, "get_messwerte", fake_get_daily_values_multiple_zp)
    result = client.get_daily_values(
        None,
        "2025-01-01",
        "2025-01-04",
        paginate=True,
        chunk_days=10,
    )
    assert isinstance(result, list)
    assert len(result) == expected_multiple_zp_list_length
    meter_ids = {meter.get("zaehlpunkt") for meter in result}
    expected_ids = {
        "AT0010000000000000001000000000001",
        "AT0010000000000000001000000000002",
    }
    assert meter_ids == expected_ids
