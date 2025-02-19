"""Tests for the get_quarter_hour_values functionality of the WNAPIClient.

These tests verify that:
  - When no pagination is requested, get_quarter_hour_values returns the full-range response as a dict for a single meter.
  - When pagination is enabled, the response is correctly aggregated from multiple chunks.

A fake implementation of get_messwerte (fake_get_messwerte_qh) is used to simulate API responses for a single meter ('test_meter')
with the QUARTER_HOUR wertetyp.

Usage:
    python -m pytest tests/test_get_quarter_hour_values.py
"""  # noqa: E501

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

    from wiener_netze_smart_meter_api.client import WNAPIClient


def fake_get_messwerte_qh(
    wertetyp: str,
    zaehlpunkt: str | None,
    datum_von: str,
    datum_bis: str,
) -> dict | None:
    """Fake get_messwerte for QUARTER_HOUR tests for a single meter 'test_meter'.

    Simulates different responses depending on the provided date range:
      - For the full range (2025-01-01 to 2025-01-05), returns a full aggregated response.
      - For chunk sub-ranges, returns responses with a subset of the measurements.

    Args:
        wertetyp (str): Expected to be "QUARTER_HOUR".
        zaehlpunkt (str | None): Expected to be "test_meter".
        datum_von (str): The start date in 'YYYY-MM-DD' format.
        datum_bis (str): The end date in 'YYYY-MM-DD' format.

    Returns:
        dict | None: A fake API response as a dictionary if parameters match; otherwise, None.

    """  # noqa: E501
    if wertetyp != "QUARTER_HOUR" or zaehlpunkt != "test_meter":
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
                            "messwert": 10,
                            "zeitVon": "2025-01-01T00:00:00.000Z",
                            "zeitBis": "2025-01-01T00:15:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 20,
                            "zeitVon": "2025-01-02T00:15:00.000Z",
                            "zeitBis": "2025-01-02T00:30:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 30,
                            "zeitVon": "2025-01-03T00:30:00.000Z",
                            "zeitBis": "2025-01-03T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 40,
                            "zeitVon": "2025-01-04T00:30:00.000Z",
                            "zeitBis": "2025-01-04T00:45:00.000Z",
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
                            "messwert": 10,
                            "zeitVon": "2025-01-01T00:00:00.000Z",
                            "zeitBis": "2025-01-01T00:15:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 20,
                            "zeitVon": "2025-01-02T00:15:00.000Z",
                            "zeitBis": "2025-01-02T00:30:00.000Z",
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
                            "messwert": 30,
                            "zeitVon": "2025-01-03T00:30:00.000Z",
                            "zeitBis": "2025-01-03T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 40,
                            "zeitVon": "2025-01-04T00:30:00.000Z",
                            "zeitBis": "2025-01-04T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-01" and datum_bis == "2025-01-05":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 10,
                            "zeitVon": "2025-01-01T00:00:00.000Z",
                            "zeitBis": "2025-01-01T00:15:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 20,
                            "zeitVon": "2025-01-02T00:15:00.000Z",
                            "zeitBis": "2025-01-02T00:30:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 30,
                            "zeitVon": "2025-01-03T00:30:00.000Z",
                            "zeitBis": "2025-01-03T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 40,
                            "zeitVon": "2025-01-04T00:30:00.000Z",
                            "zeitBis": "2025-01-04T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 50,
                            "zeitVon": "2025-01-05T00:30:00.000Z",
                            "zeitBis": "2025-01-05T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-01" and datum_bis == "2025-01-03":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 10,
                            "zeitVon": "2025-01-01T00:00:00.000Z",
                            "zeitBis": "2025-01-01T00:15:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 20,
                            "zeitVon": "2025-01-02T00:15:00.000Z",
                            "zeitBis": "2025-01-02T00:30:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 30,
                            "zeitVon": "2025-01-03T00:30:00.000Z",
                            "zeitBis": "2025-01-03T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-04" and datum_bis == "2025-01-05":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.9.0",
                    "messwerte": [
                        {
                            "messwert": 40,
                            "zeitVon": "2025-01-04T00:30:00.000Z",
                            "zeitBis": "2025-01-04T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 50,
                            "zeitVon": "2025-01-05T00:30:00.000Z",
                            "zeitBis": "2025-01-05T00:45:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    return None


def test_get_quarter_hour_values_non_paginated(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_quarter_hour_values without pagination returns the full-range response (a dict) for a single meter."""  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_qh)
    result = client.get_quarter_hour_values("test_meter", "2025-01-01", "2025-01-04")
    expected = fake_get_messwerte_qh(
        "QUARTER_HOUR",
        "test_meter",
        "2025-01-01",
        "2025-01-04",
    )
    assert isinstance(result, dict)
    assert result == expected


def test_get_quarter_hour_values_paginated(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_quarter_hour_values with pagination aggregates chunk responses correctly for a single meter.

    The date range is split into 4 chunks:
      - 2025-01-01 to 2025-01-02,
      - 2025-01-02 to 2025-01-03,
      - 2025-01-03 to 2025-01-04.
      - 2025-01-04 to 2025-01-05.
    The aggregated result should match the full-range response.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_qh)
    expected_full = fake_get_messwerte_qh(
        "QUARTER_HOUR",
        "test_meter",
        "2025-01-01",
        "2025-01-04",
    )
    result = client.get_quarter_hour_values(
        "test_meter",
        "2025-01-01",
        "2025-01-04",
        paginate=True,
        chunk_days=2,
    )
    # For a single meter, paginated should return a dict.
    assert isinstance(result, dict)
    assert result == expected_full

def test_get_quarter_hour_values_paginated_one_day_left(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_quarter_hour_values with pagination aggregates chunk responses correctly for a single meter.

    This tests if a chunk where 1 day would be left in the end, is extended by one day.
    The date range is split into 2 chunks:
      - 2025-01-01 to 2025-01-03,
      - 2025-01-04 to 2025-01-05,
    The aggregated result should match the full-range response.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_qh)
    expected_full = fake_get_messwerte_qh(
        "QUARTER_HOUR",
        "test_meter",
        "2025-01-01",
        "2025-01-05",
    )
    result = client.get_quarter_hour_values(
        "test_meter",
        "2025-01-01",
        "2025-01-05",
        paginate=True,
        chunk_days=2,
    )
    # For a single meter, paginated should return a dict.
    assert isinstance(result, dict)
    assert result == expected_full
