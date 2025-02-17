"""Tests for the get_messwerte method of the WNAPIClient.

This module verifies that get_messwerte validates its 'wertetyp' parameter. In particular,
it checks that passing an invalid wertetyp causes the method to raise a ValueError with an
appropriate message.

Usage:
    python -m pytest tests/test_get_messwerte.py
"""  # noqa: E501

import pytest

from wiener_netze_smart_meter_api.client import WNAPIClient


def test_get_messwerte_invalid_wertetyp(client: WNAPIClient) -> None:
    """Test that get_messwerte raises ValueError for an invalid wertetyp.

    This test calls get_messwerte with a value not in ALLOWED_WERTE_TYP and asserts that
    a ValueError is raised with a message indicating the invalid wertetyp.
    """
    with pytest.raises(ValueError, match="Invalid wertetyp:"):
        client.get_messwerte("INVALID_TYPE", None, "2024-01-01", "2024-01-02")
