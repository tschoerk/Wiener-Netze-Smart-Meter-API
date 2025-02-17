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
from zoneinfo import ZoneInfo

import requests
from dateutil.relativedelta import relativedelta
from requests.exceptions import RequestException

from .exceptions import WNAPIAuthenticationError, WNAPIRequestError

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
    VIENNA_TZ = ZoneInfo("Europe/Vienna")

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        api_key: str,
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout: int = 10,
    ) -> None:
        """Initialize the WNAPIClient.

        Args:
            client_id (str): Client ID for authentication.
            client_secret (str): Client secret for authentication.
            api_key (str): API key for gateway access.
            max_retries (int, optional): Maximum number of retry attempts for requests. Defaults to 3.
            retry_delay (int, optional): Delay between retries in seconds. Defaults to 5.
            timeout (int, optional): Time in seconds until timeout error for requests.

        """  # noqa: E501
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.token = None
        self.token_expiry = 0  # UNIX timestamp when the token expires
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
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
                    timeout=self.timeout,
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
            dict | None: The JSON response as a dictionary if successful,
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
                        timeout=self.timeout,
                        params=params,
                    )
                elif method == "POST":
                    response = self.session.post(
                        endpoint,
                        headers=headers,
                        json=data,
                        timeout=self.timeout,
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

        - If both dates are provided:
            - If datum_bis is earlier than datum_von, a warning is logged and the default range (3 years ago to today) is used.
            - If they are equal, datum_bis is extended by one day.
            - Otherwise, returns the provided dates.
        - If only datum_von is provided, datum_bis defaults to today.
        - If only datum_bis is provided, datum_von defaults to 3 years before datum_bis.
        - If neither is provided, defaults to 3 years ago to today.

        Assumes dates are in the format '%Y-%m-%d'.

        Args:
            datum_von (str | None): The starting date as a string.
            datum_bis (str | None): The ending date as a string.

        Returns:
            tuple[str, str]: A tuple containing the calculated start and end dates.

        """  # noqa: E501
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        if datum_von:
            try:
                dt_von = datetime.datetime.strptime(datum_von, "%Y-%m-%d").replace(
                    tzinfo=datetime.timezone.utc,
                )
            except ValueError as e:
                msg = "Invalid date format. Expected '%Y-%m-%d'."
                raise ValueError(msg) from e
        if datum_bis:
            try:
                dt_bis = datetime.datetime.strptime(datum_bis, "%Y-%m-%d").replace(
                    tzinfo=datetime.timezone.utc,
                )
            except ValueError as e:
                msg = "Invalid date format. Expected '%Y-%m-%d'."
                raise ValueError(msg) from e
        if datum_von and datum_bis:
            if dt_von > dt_bis:
                msg = "datum_bis is earlier than datum_von."
                raise ValueError(msg)
            if dt_von == dt_bis:
                # If the dates are equal, extend datum_bis by one day, since the API throws a 400 otherwise. # noqa: E501
                # It is assumed that the user wants the specific day anyway so that corrects it. # noqa: E501
                msg = "datum_von and datum_bis are equal. Extending datum_bis by 1 day."
                _LOGGER.warning(msg)
                datum_bis = (dt_bis + datetime.timedelta(days=1)).strftime(
                    "%Y-%m-%d",
                )
            return datum_von, datum_bis
        if datum_von and not datum_bis:
            return datum_von, now.strftime("%Y-%m-%d")
        if datum_bis and not datum_von:
            datum_von_dt = dt_bis - relativedelta(years=3)
            return datum_von_dt.strftime("%Y-%m-%d"), datum_bis
        if not datum_von and not datum_bis:
            return (now - relativedelta(years=3)).strftime("%Y-%m-%d"), now.strftime(
                "%Y-%m-%d",
            )
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
            dict | None: The API response as a dictionary, or None if the request fails.

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
            dict | None: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        datum_von, datum_bis = self._calculate_date_range(datum_von, datum_bis)

        params = {"wertetyp": wertetyp, "datumVon": datum_von, "datumBis": datum_bis}

        if zaehlpunkt:
            endpoint = urljoin(self.BASE_URL, f"zaehlpunkte/{zaehlpunkt}/messwerte")
        else:
            endpoint = urljoin(self.BASE_URL, "zaehlpunkte/messwerte")

        return self.make_authenticated_request(endpoint, method="GET", params=params)

    def _get_paginated_messwerte(
        self,
        wertetyp: str,
        zaehlpunkt: str | None,
        datum_von: str | None,
        datum_bis: str | None,
        chunk_days: int = 7,
    ) -> list[dict] | None:
        """Fetch measured values with client-side pagination and aggregate results.

        Splits the overall date range into chunks (default 7 days per chunk) and aggregates
        the responses by grouping results by 'zaehlpunkt'. For each meter, the 'zaehlwerke'
        entries are merged by matching on 'obisCode'. For duplicate entries, their 'messwerte'
        lists are combined without adding duplicate measurements (determined by 'zeitVon' and 'zeitBis').

        Args:
            wertetyp (str): The type of measured values (e.g., "QUARTER_HOUR", "DAY", "METER_READ").
            zaehlpunkt (str | None): The meter identifier. If provided, only data for this meter is fetched.
            datum_von (str | None): The starting date in '%Y-%m-%d' format.
            datum_bis (str | None): The ending date in '%Y-%m-%d' format.
            chunk_days (int, optional): The number of days per chunk. Must be at least 1. Defaults to 7.

        Returns:
            list[dict] | None: A list of aggregated meter responses, or None if no data was retrieved.

        """  # noqa: E501
        # Enforce a minimum chunk_days value of 1.
        chunk_days = max(chunk_days, 1)

        # Determine effective date range.
        datum_von, datum_bis = self._calculate_date_range(datum_von, datum_bis)
        start_date = (
            datetime.datetime.strptime(datum_von, "%Y-%m-%d")
            .replace(
                tzinfo=datetime.timezone.utc,
            )
            .date()
        )
        end_date = (
            datetime.datetime.strptime(datum_bis, "%Y-%m-%d")
            .replace(
                tzinfo=datetime.timezone.utc,
            )
            .date()
        )
        aggregated: dict[str, dict] = {}

        current_start = start_date
        # Use a strict < condition so we don't start a chunk when current_start equals end_date, otherwise we get a 400.  # noqa: E501
        while current_start < end_date:
            current_end = min(
                current_start + datetime.timedelta(days=chunk_days),
                end_date,
            )

            chunk_von = current_start.strftime("%Y-%m-%d")
            chunk_bis = current_end.strftime("%Y-%m-%d")

            msg = f"Fetching {wertetyp} chunk data from {chunk_von} to {chunk_bis}"
            _LOGGER.info(msg)

            # Retrieve data for this chunk.
            chunk_data = self.get_messwerte(wertetyp, zaehlpunkt, chunk_von, chunk_bis)
            # Normalize chunk_data to a list if it is a dict (i.e., single meter case).
            if chunk_data and isinstance(chunk_data, dict):
                chunk_data = [chunk_data]
            if chunk_data:
                for meter in chunk_data:
                    zp = meter.get("zaehlpunkt")
                    if not zp:
                        continue
                    if zp not in aggregated:
                        # Create a deep copy: copy all keys and duplicate the zaehlwerke list.  # noqa: E501
                        aggregated[zp] = {
                            **meter,
                            "zaehlwerke": [
                                {**zw, "messwerte": zw.get("messwerte", []).copy()}
                                for zw in meter.get("zaehlwerke", [])
                            ],
                        }
                    else:
                        # Merge each zaehlwerke entry.
                        for zw in meter.get("zaehlwerke", []):
                            obis = zw.get("obisCode")
                            found = None
                            for agg_zw in aggregated[zp].get("zaehlwerke", []):
                                if agg_zw.get("obisCode") == obis:
                                    found = agg_zw
                                    break
                            if found is None:
                                # No matching obisCode; add a new entry.
                                new_zw = {
                                    **zw,
                                    "messwerte": zw.get("messwerte", []).copy(),
                                }
                                aggregated[zp].setdefault("zaehlwerke", []).append(
                                    new_zw,
                                )
                            else:
                                # Merge messwerte, checking duplicates based on zeitVon and zeitBis.  # noqa: E501
                                for mv in zw.get("messwerte", []):
                                    if not any(
                                        existing.get("zeitVon") == mv.get("zeitVon")
                                        and existing.get("zeitBis") == mv.get("zeitBis")
                                        for existing in found.get("messwerte", [])
                                    ):
                                        found.setdefault("messwerte", []).append(mv)
            else:
                msg = f"No data returned for chunk {chunk_von} to {chunk_bis}"
                _LOGGER.warning(msg)

            # Advance current_start to current_end to allow one-day overlap.
            current_start = current_end
            msg = f"Next chunk starts at {current_start}"
            _LOGGER.info(msg)

        msg = f"Chunk start is equal to end at {current_start}. Finished pagination."
        _LOGGER.info(msg)

        if not aggregated:
            return None

        result = list(aggregated.values())
        # If a single meter was requested, return its dict (to mimic non-paginated call).  # noqa: E501
        if zaehlpunkt is not None and len(result) == 1:
            return result[0]
        return result

    def get_quarter_hour_values(
        self,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
        *,
        paginate: bool = False,
        chunk_days: int = 7,
    ) -> dict | None:
        """Fetch quarter-hourly measured values.

        If a zaehlpunkt is provided, fetches measured values for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.
            paginate (bool, optional): Whether to paginate the request. Defaults to False.
            chunk_days (int, optional): Days per chunk if paginating. Defaults to 7.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        if paginate:
            return self._get_paginated_messwerte(
                "QUARTER_HOUR",
                zaehlpunkt,
                datum_von,
                datum_bis,
                chunk_days,
            )
        return self.get_messwerte("QUARTER_HOUR", zaehlpunkt, datum_von, datum_bis)

    def get_daily_values(
        self,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
        *,
        paginate: bool = False,
        chunk_days: int = 7,
    ) -> dict | None:
        """Fetch daily measured values.

        If a zaehlpunkt is provided, fetches measured values for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.
            paginate (bool, optional): Whether to paginate the request. Defaults to False.
            chunk_days (int, optional): Days per chunk if paginating. Defaults to 7.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        if paginate:
            return self._get_paginated_messwerte(
                "DAY",
                zaehlpunkt,
                datum_von,
                datum_bis,
                chunk_days,
            )
        return self.get_messwerte("DAY", zaehlpunkt, datum_von, datum_bis)

    def get_meter_readings(
        self,
        zaehlpunkt: str | None = None,
        datum_von: str | None = None,
        datum_bis: str | None = None,
        *,
        paginate: bool = False,
        chunk_days: int = 7,
    ) -> dict | None:
        """Fetch meter readings.

        If a zaehlpunkt is provided, fetches meter readings for that specific meter.

        Args:
            zaehlpunkt (str, optional): The meter identifier. Defaults to None.
            datum_von (str, optional): The starting date in '%Y-%m-%d' format. Defaults to None.
            datum_bis (str, optional): The ending date in '%Y-%m-%d' format. Defaults to None.
            paginate (bool, optional): Whether to paginate the request. Defaults to False.
            chunk_days (int, optional): Days per chunk if paginating. Defaults to 7.

        Returns:
            Optional[Dict]: The API response as a dictionary, or None if the request fails.

        """  # noqa: E501
        if paginate:
            return self._get_paginated_messwerte(
                "METER_READ",
                zaehlpunkt,
                datum_von,
                datum_bis,
                chunk_days,
            )
        return self.get_messwerte("METER_READ", zaehlpunkt, datum_von, datum_bis)
