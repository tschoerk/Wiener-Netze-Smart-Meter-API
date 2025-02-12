"""Custom exceptions for the WNAPIClient.

This module defines exception classes that can be raised by the WNAPIClient
to signal different kinds of errors.
"""


class WNAPIError(Exception):
    """Base exception for errors raised by the WNAPIClient."""


class WNAPIAuthenticationError(WNAPIError):
    """Exception raised when authentication fails, such as when obtaining a token."""


class WNAPIRequestError(WNAPIError):
    """Exception raised when an API request fails after maximum retries."""
