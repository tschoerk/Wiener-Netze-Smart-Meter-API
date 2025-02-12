"""Client for the Wiener Netze Smart Meter API.

This module provides the WNAPIClient class for interacting with the Wiener Netze Smart Meter API.
It handles authentication via a bearer token, makes authenticated HTTP requests with automatic
retry and token refresh, and offers methods to fetch various smart meter readings and measured values.

Usage:
    from wiener_netze_smart_meter_api import WNAPIClient

    client = WNAPIClient(
        client_id="your_client_id",
        client_secret="your_client_secret",
        api_key="your_api_key"
    )
    # Example: Fetch information for all smart meters.
    anlagendaten = client.get_anlagendaten()
"""  # noqa: E501

from __future__ import annotations

import datetime
import logging
import time
from typing import ClassVar
from urllib.parse import urljoin

import requests
from dateutil.relativedelta import relativedelta
from exceptions import WNAPIAuthenticationError, WNAPIRequestError
from requests.exceptions import RequestException

_LOGGER = logging.getLogger(__name__)


class WNAPIClient:
    """Client for the Wiener Netze Smart Meter API.

    This client handles authentication, token management, and making requests
    to the Wiener Netze Smart Meter API endpoints.
    """

    TOKEN_URL = "https://log.wien/auth/realms/logwien/protocol/openid-connect/token"  # noqa: S105
    BASE_URL = "https://api.wstw.at/gateway/WN_SMART_METER_API/1.0/"
    ALLOWED_METHODS: ClassVar[set[str]] = {"GET", "POST"}
    HTTP_CODE_UNAUTHORIZED = 401

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_key: str,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> None:
        """Initialize the WNAPIClient.

        Args:
            client_id (str): Client ID for authentication.
            client_secret (str): Client secret for authentication.
            api_key (str): API key for gateway access.
            max_retries (int, optional): Maximum number of retry attempts for requests. Defaults to 3.
            retry_delay (int, optional): Delay between retries in seconds. Defaults to 5.

        """  # noqa: E501
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.token = None
        self.token_expiry = 0  # UNIX timestamp when the token expires
        self.max_retries = max_retries  # Max retry attempts
        self.retry_delay = retry_delay  # Delay between retries in seconds
        self.session = requests.Session()  # New persistent session

    def get_bearer_token(self) -> str | None:
        """Retrieve a Bearer Token, refreshing it if expired.

        Returns:
            Optional[str]: A valid bearer token as a string if successful,
                           or None if token retrieval fails.

        """
        if self.token and time.time() < self.token_expiry:
            return self.token  # Return cached token if still valid

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(
                    self.TOKEN_URL,
                    data=data,
                    headers=headers,
                    timeout=10,
                )
                response.raise_for_status()
                try:
                    token_data = response.json()
                except ValueError:
                    _LOGGER.exception("JSON decoding failed for token response")
                    raise
            except RequestException:  # noqa: PERF203
                msg = f"Token request failed (Attempt {attempt}/{self.max_retries})"
                _LOGGER.exception(msg)
                if attempt < self.max_retries:
                    msg = f"Retrying in {self.retry_delay} seconds..."
                    _LOGGER.info(msg)
                    time.sleep(self.retry_delay)
                else:
                    msg = "Max retries reached. Unable to obtain token."
                    _LOGGER.critical(msg)
                    raise WNAPIAuthenticationError(msg) from None
            else:
                self.token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 300)  # Default to 300 sec
                self.token_expiry = time.time() + expires_in - 10  # Buffer of 10 sec

                msg = (
                    f"Successfully obtained Bearer Token (Expires in {expires_in} sec)"
                )
                _LOGGER.info(msg)
                return self.token
        return None

    def make_authenticated_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict | None:
        """Make an API request with a valid Bearer Token.

        Note:
            Currently, the Wiener Netze API endpoints only use GET, but POST support
            is included for future endpoints if needed.

        Args:
            endpoint (str): The API endpoint URL.
            method (str, optional): HTTP method to use ("GET" or "POST"). Defaults to "GET".
            data (Optional[Dict], optional): JSON payload for POST requests. Defaults to None.
            params (Optional[Dict], optional): Query parameters for the request. Defaults to None.

        Returns:
            Optional[Dict]: The JSON response as a dictionary if successful,
                            or None on failure.

        Raises:
            NotImplementedError: If an unsupported HTTP method is used.

        """  # noqa: E501
        method = method.upper()
        if method not in self.ALLOWED_METHODS:
            msg = f"HTTP method {method} is not supported."
            raise NotImplementedError(msg)

        for attempt in range(1, self.max_retries + 1):
            token = self.get_bearer_token()
            if not token:
                _LOGGER.error("No valid token available, request aborted.")
                return None

            headers = {
                "Authorization": f"Bearer {token}",
                "x-Gateway-APIKey": self.api_key,
            }

            try:
                if method == "GET":
                    response = self.session.get(
                        endpoint,
                        headers=headers,
                        timeout=10,
                        params=params,
                    )
                elif method == "POST":
                    response = self.session.post(
                        endpoint,
                        headers=headers,
                        json=data,
                        timeout=10,
                        params=params,
                    )

                response.raise_for_status()
                msg = f"Successful {method} request to {endpoint}"
                _LOGGER.info(msg)
                return response.json()

            except requests.HTTPError as http_err:
                msg = f"HTTP error on {method} request to {endpoint}"
                _LOGGER.exception(msg)
                if (
                    http_err.response is not None
                    and http_err.response.status_code == self.HTTP_CODE_UNAUTHORIZED
                ):
                    _LOGGER.warning("Token may be expired. Fetching new token...")
                    self.token = None  # Invalidate token to force refresh

            except requests.Timeout:
                msg = f"Timeout on {method} request to {endpoint} (Attempt {attempt}/{self.max_retries})"  # noqa: E501
                _LOGGER.warning(msg)

            except RequestException:
                _LOGGER.exception("Request error occurred")

            delay = self.retry_delay * (2 ** (attempt - 1))
            if attempt < self.max_retries:
                msg = f"Retrying request in {delay} seconds..."
                _LOGGER.info(msg)
                time.sleep(delay)
            else:
                msg = f"Max retries reached. Unable to complete request: {endpoint}"
                _LOGGER.critical(msg)
                raise WNAPIRequestError(msg)
        return None

    def _calculate_date_range(
        self,
        datum_von: str | None,
        datum_bis: str | None,
    ) -> tuple[str, str]:
        """Calculate the date range based on the provided datum_von and datum_bis.

        - If both dates are provided, returns them unchanged.
        - If only datum_von is provided, datum_bis defaults to today.
        - If only datum_bis is provided, datum_von defaults to 3 years before datum_bis.
        - If neither is provided, defaults to 3 years ago to today.

        Assumes dates are in the format '%Y-%m-%d'.

        Args:
            datum_von (Optional[str]): The starting date as a string.
            datum_bis (Optional[str]): The ending date as a string.

        Returns:
            Tuple[str, str]: A tuple containing the calculated start and end dates.

        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if datum_von and datum_bis:
            return datum_von, datum_bis
        if not datum_von and not datum_bis:
            return (now - relativedelta(years=3)).strftime("%Y-%m-%d"), now.strftime(
                "%Y-%m-%d",
            )
        if datum_von and not datum_bis:
            return datum_von, now.strftime("%Y-%m-%d")
        if datum_bis and not datum_von:
            datum_bis_dt = datetime.strptime(datum_bis, "%Y-%m-%d")
            datum_von_dt = datum_bis_dt - relativedelta(years=3)
            return datum_von_dt.strftime("%Y-%m-%d"), datum_bis
        return None

    def get_anlagendaten(
        self,
        zaehlpunkt: str | None = None,
        result_type: str = "ALL",
    ) -> dict | None:
        """Fetch information about a specific or all smart meter(s) associated with the user.

        If a zaehlpunkt is provided, fetches details for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            result_type (str, optional): The result type filter (e.g., "ALL"). Defaults to "ALL".

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        params = None
        if zaehlpunkt:
            endpoint = urljoin(self.BASE_URL, f"zaehlpunkte/{zaehlpunkt}")
        else:
            endpoint = urljoin(self.BASE_URL, "zaehlpunkte")
            params = {"resultType": result_type}

        return self.make_authenticated_request(endpoint, method="GET", params=params)

    def get_messwerte(
        self,
        wertetyp: str,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
    ) -> dict | None:
        """Fetch measured values (QUARTER_HOUR, DAY, METER_READ) for smart meters.

        If a zaehlpunkt is provided, fetches measured values for that specific meter.
        Defaults to fetching data from 3 years ago to today if no dates are provided.

        Args:
            wertetyp (str): The type of measured values (e.g., "QUARTER_HOUR", "DAY", "METER_READ").
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        datum_von, datum_bis = self._calculate_date_range(datum_von, datum_bis)

        params = {"wertetyp": wertetyp, "datumVon": datum_von, "datumBis": datum_bis}

        if zaehlpunkt:
            endpoint = urljoin(self.BASE_URL, f"zaehlpunkte/{zaehlpunkt}/messwerte")
        else:
            endpoint = urljoin(self.BASE_URL, "zaehlpunkte/messwerte")

        return self.make_authenticated_request(endpoint, method="GET", params=params)

    def get_quarter_hour_values(
        self,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
    ) -> dict | None:
        """Fetch quarter-hourly measured values.

        If a zaehlpunkt is provided, fetches measured values for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        return self.get_messwerte("QUARTER_HOUR", zaehlpunkt, datum_von, datum_bis)

    def get_daily_values(
        self,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
    ) -> dict | None:
        """Fetch daily measured values.

        If a zaehlpunkt is provided, fetches measured values for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        return self.get_messwerte("DAY", zaehlpunkt, datum_von, datum_bis)

    def get_meter_readings(
        self,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
    ) -> dict | None:
        """Fetch meter readings.

        If a zaehlpunkt is provided, fetches meter readings for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        return self.get_messwerte("METER_READ", zaehlpunkt, datum_von, datum_bis)
