"""Module fakeresponse.py.

This module defines the FakeResponse class, a stand-in for the requests.Response object,
to simulate HTTP responses during testing. It supports returning predefined JSON data,
simulating HTTP errors via status codes, and optionally raising a ValueError when JSON
decoding is intended to fail.
"""

from __future__ import annotations

from typing import ClassVar

import requests


class FakeResponse:
    """A fake response object to simulate requests.Response for testing purposes.

    Attributes:
        HTTP_ERROR_THRESHOLD (ClassVar[int]): The threshold status code above which an HTTPError is raised.

    """  # noqa: E501

    HTTP_ERROR_THRESHOLD: ClassVar[int] = 400

    def __init__(
        self,
        status_code: int = 200,
        json_data: dict | None = None,
        headers: dict | None = None,
        *,
        raise_on_json: bool = False,
    ) -> None:
        """Initialize a FakeResponse.

        Args:
            status_code (int, optional): HTTP status code. Defaults to 200.
            json_data (dict | None, optional): The JSON data to return. Defaults to {}.
            headers (dict | None, optional): HTTP headers. Defaults to {"Content-Type": "application/json"}.
            raise_on_json (bool, optional): If True, calling json() will raise a ValueError.

        """  # noqa: E501
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {"Content-Type": "application/json"}
        self.raise_on_json = raise_on_json

    def raise_for_status(self) -> None:
        """Raise an HTTPError if the status code is 400 or above."""
        if self.status_code >= self.HTTP_ERROR_THRESHOLD:
            raise requests.HTTPError(response=self)

    def json(self) -> dict:
        """Return the JSON data or raise a ValueError if configured.

        Returns:
            dict: The stored JSON data.

        Raises:
            ValueError: If raise_on_json is True.

        """
        if self.raise_on_json:
            msg = "JSON decoding failed for token response"
            raise ValueError(msg)
        return self._json_data
