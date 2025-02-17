"""Tests for the date range calculation functionality of the WNAPIClient.

These tests exercise the private _calculate_date_range logic indirectly through
the public get_messwerte method. They verify that:
  - When both valid dates are provided, they remain unchanged.
  - When the provided dates are equal, datum_bis is extended by one day.
  - When only one date is provided, the missing date is defaulted appropriately.
  - When datum_bis is earlier than datum_von, a ValueError is raised.
  - Invalid date formats raise a ValueError.
  - When no dates are provided, defaults (3 years ago to today) are used.

Usage:
    python -m pytest tests/test_calculate_date_range.py
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pytest
from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    from wiener_netze_smart_meter_api.client import WNAPIClient


def fake_make_authenticated_request_return_params(
    endpoint: str,  # noqa: ARG001
    method: str = "GET",  # noqa: ARG001
    params: dict | None = None,
) -> dict:
    """Fake make_authenticated_request that simply returns the parameters passed to it."""  # noqa: E501
    return params


def test_get_messwerte_both_dates(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test get_messwerte when both datum_von and datum_bis are provided correctly.

    In this scenario, the provided dates should be returned unchanged.
    """
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_return_params,
    )
    params = client.get_messwerte("DAY", "123", "2025-01-01", "2025-01-31")
    assert params["datumVon"] == "2025-01-01"
    assert params["datumBis"] == "2025-01-31"


def test_get_messwerte_equal_dates(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test get_messwerte with equal datum_von and datum_bis.

    When the provided dates are equal, the helper should extend datum_bis by one day.
    """
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_return_params,
    )
    params = client.get_messwerte("DAY", None, "2024-06-01", "2024-06-01")
    assert params["datumVon"] == "2024-06-01"
    # Expect datum_bis to be extended by one day.
    assert params["datumBis"] == "2024-06-02"


def test_get_messwerte_invalid_date_order(client: WNAPIClient) -> None:
    """Test that get_messwerte raises ValueError when datum_bis is earlier than datum_von."""  # noqa: E501
    with pytest.raises(ValueError, match="datum_bis is earlier than datum_von"):
        client.get_messwerte("DAY", None, "2024-12-31", "2024-01-01")


def test_get_messwerte_only_datum_von(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test get_messwerte when only datum_von is provided.

    The helper should default datum_bis to today's date.
    """
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_return_params,
    )
    params = client.get_messwerte("DAY", None, "2024-01-01", None)
    expected_today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    assert params["datumVon"] == "2024-01-01"
    assert params["datumBis"] == expected_today


def test_get_messwerte_only_datum_bis(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test get_messwerte when only datum_bis is provided.

    The helper should default datum_von to 3 years before datum_bis.
    """
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_return_params,
    )
    params = client.get_messwerte("DAY", None, None, "2024-12-31")
    dt_bis = datetime.datetime.strptime("2024-12-31", "%Y-%m-%d").replace(
        tzinfo=datetime.timezone.utc,
    )
    dt_von = dt_bis - relativedelta(years=3)
    expected_von = dt_von.strftime("%Y-%m-%d")
    assert params["datumVon"] == expected_von
    assert params["datumBis"] == "2024-12-31"


def test_get_messwerte_invalid_date_format_datum_von(client: WNAPIClient) -> None:
    """Test that get_messwerte raises ValueError for an invalid date format for datum_von."""  # noqa: E501
    with pytest.raises(ValueError, match="Invalid date format"):
        client.get_messwerte("DAY", None, "2024/01/01", "2024-12-31")


def test_get_messwerte_invalid_date_format_datum_bis(client: WNAPIClient) -> None:
    """Test that get_messwerte raises ValueError for an invalid date format for datum_bis."""  # noqa: E501
    with pytest.raises(ValueError, match="Invalid date format"):
        client.get_messwerte("DAY", None, "2024-01-01", "2024/12-31")


def test_get_messwerte_no_dates(
    monkeypatch: pytest.MonkeyPatch,
    client: WNAPIClient,
) -> None:
    """Test that get_messwerte defaults to a range of 3 years ago to today when no dates are provided.

    This verifies that both datum_von and datum_bis are computed as defaults.
    """  # noqa: E501
    monkeypatch.setattr(
        client,
        "make_authenticated_request",
        fake_make_authenticated_request_return_params,
    )
    params = client.get_messwerte("DAY", None, None, None)
    dt_bis = datetime.datetime.now(datetime.timezone.utc)
    dt_von = dt_bis - relativedelta(years=3)
    expected_bis = dt_bis.strftime("%Y-%m-%d")
    expected_von = dt_von.strftime("%Y-%m-%d")
    assert params["datumVon"] == expected_von
    assert params["datumBis"] == expected_bis
