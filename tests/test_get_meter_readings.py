"""Tests for get_meter_readings functionality of the WNAPIClient.

These tests verify that:
  - When no pagination is requested, get_meter_readings returns the full-range response
    as a dictionary for a single meter.
  - When pagination is enabled, the response is aggregated correctly from multiple chunks.
  - The aggregated result merges entries by meter and obisCode as expected.
  - A ValueError is raised when an invalid chunk_days value is provided.
  - If a chunk returns data without a 'zaehlpunkt' key, the final result is None.

Usage:
    python -m pytest tests/test_get_meter_readings.py
"""  # noqa: E501

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from wiener_netze_smart_meter_api.client import WNAPIClient


def fake_get_messwerte_mr(
    wertetyp: str,
    zaehlpunkt: str | None,
    datum_von: str,
    datum_bis: str,
) -> dict | None:
    """Fake get_messwerte for METER_READ tests for a single meter "test_meter".

    Returns different fake responses depending on the provided date range.
    """
    if wertetyp != "METER_READ" or zaehlpunkt != "test_meter":
        return None
    # Define fake responses based on date range.
    if datum_von == "2025-01-01" and datum_bis == "2025-01-02":
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.8.0",
                    "messwerte": [
                        {
                            "messwert": 100,
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
                    "obisCode": "1-1:1.8.0",
                    "messwerte": [
                        {
                            "messwert": 200,
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
                    "obisCode": "1-1:1.8.0",
                    "messwerte": [
                        {
                            "messwert": 300,
                            "zeitVon": "2025-01-03T23:00:00.000Z",
                            "zeitBis": "2025-01-04T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-01" and datum_bis == "2025-01-04":
        # Full response
        return {
            "zaehlpunkt": "test_meter",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "1-1:1.8.0",
                    "messwerte": [
                        {
                            "messwert": 100,
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 200,
                            "zeitVon": "2025-01-02T23:00:00.000Z",
                            "zeitBis": "2025-01-03T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 300,
                            "zeitVon": "2025-01-03T23:00:00.000Z",
                            "zeitBis": "2025-01-04T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    return None


def test_get_meter_readings_non_paginated(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_meter_readings without pagination returns the full response as a dict for a single meter."""  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_mr)
    result = client.get_meter_readings("test_meter", "2025-01-01", "2025-01-04")
    expected = fake_get_messwerte_mr(
        "METER_READ",
        "test_meter",
        "2025-01-01",
        "2025-01-04",
    )
    assert isinstance(result, dict)
    assert result == expected


def test_get_meter_readings_paginated(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_meter_readings with pagination aggregates chunk responses correctly for a single meter.

    The date range is split into 3 chunks:
      - 2025-01-01 to 2025-01-02
      - 2025-01-02 to 2025-01-03
      - 2025-01-03 to 2025-01-04
    The aggregated result should match the full-range response.
    """  # noqa: E501
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_mr)
    result = client.get_meter_readings(
        "test_meter",
        "2025-01-01",
        "2025-01-04",
        paginate=True,
        chunk_days=1,
    )
    expected = fake_get_messwerte_mr(
        "METER_READ",
        "test_meter",
        "2025-01-01",
        "2025-01-04",
    )
    # For a single meter, the paginated method should return a dict.
    assert isinstance(result, dict)
    assert result == expected


def test_get_meter_readings_invalid_chunk_days(client: WNAPIClient) -> None:
    """Test that get_meter_readings raises a ValueError when chunk_days is less than 1.

    If chunk_days is set to a value less than 1, a ValueError with the message
    "chunk_days must be at least 1" should be raised.
    """
    with pytest.raises(ValueError, match="chunk_days must be at least 1"):
        client.get_meter_readings(
            "test_meter",
            "2025-01-01",
            "2025-01-04",
            paginate=True,
            chunk_days=0,
        )


def test_get_meter_readings_paginated_missing_zp(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_meter_readings with pagination returns None when chunk data lacks 'zaehlpunkt'.

    This test simulates an API response for a chunk without a 'zaehlpunkt' key. The aggregation logic
    should skip such data, resulting in an overall None return.
    """  # noqa: E501

    def fake_get_messwerte_missing_zp(
        wertetyp: str,  # noqa: ARG001
        zaehlpunkt: str | None,  # noqa: ARG001
        datum_von: str,  # noqa: ARG001
        datum_bis: str,  # noqa: ARG001
    ) -> dict:
        # Return a dict without the 'zaehlpunkt' key.
        return {"zaehlwerke": [{"obisCode": "1-1:1.8.0", "messwerte": []}]}

    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_missing_zp)
    result = client.get_meter_readings(
        "dummy",
        "2025-01-01",
        "2025-01-03",
        paginate=True,
        chunk_days=1,
    )
    assert result is None


def fake_get_messwerte_multi_chunk(
    wertetyp: str,
    zaehlpunkt: str | None,
    datum_von: str,
    datum_bis: str,
) -> dict | None:
    """Fake get_messwerte to simulate chunk responses for a single meter "TEST_METER" for METER_READ.

    Returns different data depending on the provided date range (chunk).
    """  # noqa: E501
    if wertetyp != "METER_READ" or zaehlpunkt != "TEST_METER":
        return None

    if datum_von == "2025-01-01" and datum_bis == "2025-01-02":
        # Chunk 1: obisCode OBIS1, one measurement.
        return {
            "zaehlpunkt": "TEST_METER",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "OBIS1",
                    "messwerte": [
                        {
                            "messwert": 100,
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-02" and datum_bis == "2025-01-03":
        # Chunk 2: obisCode OBIS2, one measurement.
        return {
            "zaehlpunkt": "TEST_METER",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "OBIS2",
                    "messwerte": [
                        {
                            "messwert": 200,
                            "zeitVon": "2025-01-02T23:00:00.000Z",
                            "zeitBis": "2025-01-03T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-03" and datum_bis == "2025-01-04":
        # Chunk 3: obisCode OBIS1 again, a different measurement.
        return {
            "zaehlpunkt": "TEST_METER",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "OBIS1",
                    "messwerte": [
                        {
                            "messwert": 150,
                            "zeitVon": "2025-01-03T23:00:00.000Z",
                            "zeitBis": "2025-01-04T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    if datum_von == "2025-01-01" and datum_bis == "2025-01-04":
        # Full response: OBIS1 with both measurements merged and OBIS2 as provided.
        return {
            "zaehlpunkt": "TEST_METER",
            "zaehlwerke": [
                {
                    "einheit": "WH",
                    "obisCode": "OBIS1",
                    "messwerte": [
                        {
                            "messwert": 100,
                            "zeitVon": "2025-01-01T23:00:00.000Z",
                            "zeitBis": "2025-01-02T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                        {
                            "messwert": 150,
                            "zeitVon": "2025-01-03T23:00:00.000Z",
                            "zeitBis": "2025-01-04T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
                {
                    "einheit": "WH",
                    "obisCode": "OBIS2",
                    "messwerte": [
                        {
                            "messwert": 200,
                            "zeitVon": "2025-01-02T23:00:00.000Z",
                            "zeitBis": "2025-01-03T23:00:00.000Z",
                            "qualitaet": "VAL",
                        },
                    ],
                },
            ],
        }
    return None


def test_get_meter_readings_paginated_found_none(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_meter_readings with pagination correctly aggregates responses when multiple obisCodes are encountered.

    This test simulates three chunks:
      - Chunk 1: returns obisCode "OBIS1" (one measurement).
      - Chunk 2: returns obisCode "OBIS2" (one measurement).
      - Chunk 3: returns obisCode "OBIS1" again (a different measurement).

    The aggregated result for a single meter should include:
      - One merged entry for OBIS1 with two measurements.
      - One separate entry for OBIS2.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.

    """  # noqa: E501
    expected_obis1_measurements_amount = 2
    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_multi_chunk)
    result = client.get_meter_readings(
        "TEST_METER",
        "2025-01-01",
        "2025-01-04",
        paginate=True,
        chunk_days=1,
    )
    # For a single meter, the paginated method should return a dict.
    assert isinstance(result, dict)
    zaehlwerke = result.get("zaehlwerke", [])
    # Expect two distinct obisCodes: "OBIS1" and "OBIS2"
    obis_codes = {zw.get("obisCode") for zw in zaehlwerke}
    assert obis_codes == {"OBIS1", "OBIS2"}
    # Verify that for OBIS1, the merged "messwerte" list contains 2 measurements.
    for zw in zaehlwerke:
        if zw.get("obisCode") == "OBIS1":
            assert len(zw.get("messwerte", [])) == expected_obis1_measurements_amount


def test_get_meter_readings_paginated_no_data(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that when no data is returned for any chunk in a paginated request, a warning is logged and the final aggregated result is None.

    Args:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.
        client (WNAPIClient): A WNAPIClient instance.
        caplog (pytest.LogCaptureFixture): Fixture to capture log output.

    """  # noqa: E501

    def fake_get_messwerte_no_data(
        wertetyp: str,  # noqa: ARG001
        zaehlpunkt: str | None,  # noqa: ARG001
        datum_von: str,  # noqa: ARG001
        datum_bis: str,  # noqa: ARG001
    ) -> None:
        """Fake get_messwerte function that simulates no data returned for any chunk."""
        return

    monkeypatch.setattr(client, "get_messwerte", fake_get_messwerte_no_data)
    result = client.get_meter_readings(
        "test_meter",
        "2025-01-01",
        "2025-01-04",
        paginate=True,
        chunk_days=1,
    )
    assert result is None
    assert "No data returned for chunk" in caplog.text
