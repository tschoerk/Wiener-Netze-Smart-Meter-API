"""Tests for parameter validation in the __init__ method of WNAPIClient.

This module verifies that invalid initialization parameters raise a ValueError with
appropriate messages. In particular, it tests:
  - max_retries must be at least 1.
  - retry_delay must be at least 0.
  - timeout must be at least 1.

Usage:
    python -m pytest tests/test_wnapi_client.py
"""

from __future__ import annotations

import pytest

from wiener_netze_smart_meter_api.client import WNAPIClient


def test_invalid_max_retries() -> None:
    """Test that __init__ raises ValueError when max_retries is less than 1."""
    with pytest.raises(ValueError, match="max_retries must be at least 1"):
        WNAPIClient("id", "secret", "api_key", max_retries=0, retry_delay=5, timeout=5)


def test_invalid_retry_delay() -> None:
    """Test that __init__ raises ValueError when retry_delay is less than 0."""
    with pytest.raises(ValueError, match="retry_delay must be at least 0"):
        WNAPIClient("id", "secret", "api_key", max_retries=3, retry_delay=-1, timeout=5)


def test_invalid_timeout() -> None:
    """Test that __init__ raises ValueError when timeout is less than 1."""
    with pytest.raises(ValueError, match="timeout must be at least 1"):
        WNAPIClient("id", "secret", "api_key", max_retries=3, retry_delay=5, timeout=0)
