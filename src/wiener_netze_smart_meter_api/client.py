from typing import Dict, Optional
import requests
import time
import logging
from datetime import datetime, timedelta
from requests.exceptions import RequestException
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
class WNAPIClient:
    TOKEN_URL = "https://log.wien/auth/realms/logwien/protocol/openid-connect/token"    
    BASE_URL = "https://api.wstw.at/gateway/WN_SMART_METER_API/1.0"
    ALLOWED_METHODS = {"GET", "POST"}

    def __init__(self, client_id: str, client_secret: str, api_key: str, token_url:str = TOKEN_URL, base_url:str = BASE_URL, max_retries: int = 3, retry_delay: int = 5):
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.token_url = token_url
        self.base_url = base_url
        self.token = None
        self.token_expiry = 0  # UNIX timestamp when the token expires
        self.max_retries = max_retries  # Max retry attempts
        self.retry_delay = retry_delay  # Delay between retries in seconds
        self.session = requests.Session()  # New persistent session

    def get_bearer_token(self) -> Optional[str]:
        """
        Retrieves a Bearer Token, refreshing it if expired.
    
        Returns:
            A valid bearer token as a string if successful, or None if token retrieval fails.
        """
        if self.token and time.time() < self.token_expiry:
            return self.token  # Return cached token if still valid

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(self.token_url, data=data, headers=headers, timeout=10)
                response.raise_for_status()
                try:
                    token_data = response.json()
                except ValueError as json_err:
                    logging.exception("JSON decoding failed for token response")
                    raise json_err
                self.token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 300)  # Default to 300 sec
                self.token_expiry = time.time() + expires_in - 10  # Buffer of 10 sec

                logging.info(f"Successfully obtained Bearer Token (Expires in {expires_in} sec)")
                return self.token

            except RequestException:
                logging.exception(f"Token request failed (Attempt {attempt}/{self.max_retries})")
                if attempt < self.max_retries:
                    logging.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logging.critical("Max retries reached. Unable to obtain token.")
                    return None

    def make_authenticated_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Makes an API request with a valid Bearer Token.
        
        Note: Currently, the Wiener Netze API endpoints only use GET, but POST support is included for future endpoints if needed.

        Returns:
            The JSON response as a dictionary if successful, or None on failure.
        """
        method = method.upper()
        if method not in self.ALLOWED_METHODS:
            raise NotImplementedError(f"HTTP method {method} is not supported.")
        
        for attempt in range(1, self.max_retries + 1):
            token = self.get_bearer_token()
            if not token:
                logging.error("No valid token available, request aborted.")
                return None

            headers = {
                "Authorization": f"Bearer {token}",
                "x-Gateway-APIKey": self.api_key
            }

            try:
                if method == "GET":
                    response = self.session.get(endpoint, headers=headers, timeout=10, params=params)
                elif method == "POST":
                    response = self.session.post(endpoint, headers=headers, json=data, timeout=10, params=params)

                response.raise_for_status()
                logging.info(f"Successful {method} request to {endpoint}")
                return response.json()

            except requests.HTTPError as http_err:
                logging.exception(f"HTTP error on {method} request to {endpoint}")
                if http_err.response is not None and http_err.response.status_code == 401:
                    logging.warning("Token may be expired. Fetching new token...")
                    self.token = None  # Invalidate token to force refresh

            except requests.Timeout:
                logging.warning(f"Timeout on {method} request to {endpoint} (Attempt {attempt}/{self.max_retries})")

            except RequestException:
                logging.exception("Request error occurred")

            delay = self.retry_delay * (2 ** (attempt - 1))
            if attempt < self.max_retries:
                logging.info(f"Retrying request in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.critical(f"Max retries reached. Unable to complete request: {endpoint}")
                return None

    def get_anlagendaten(self, zaehlpunkt: str = None, result_type: str = "ALL") -> Optional[Dict]:
        """
        Fetches information about a specific or all smart meter(s) associated with the user.
        If a zaehlpunkt is provided, fetches details for that specific meter.
        """
        if zaehlpunkt:
            endpoint = urljoin(self.base_url,f"/zaehlpunkte/{zaehlpunkt}")
        else:
            endpoint = urljoin(self.base_url, "/zaehlpunkte")
            params = {
                "resultType": result_type
            }
            
        return self.make_authenticated_request(endpoint, method="GET", params=params)

    def get_messwerte(self, wertetyp: str, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None) -> Optional[Dict]:
        """
        Fetches measured values (QUARTER_HOUR, DAY, METER_READ) for smart meters.
        If a zaehlpunkt is provided, fetches measured values for that specific meter.
        Defaults to fetching data from 3 years ago to today.
        """
        if not datumVon:
            datumVon = (datetime.today() - timedelta(days=3*365)).strftime('%Y-%m-%d')
        if not datumBis:
            datumBis = datetime.today().strftime('%Y-%m-%d')

        params = {
            "wertetyp": wertetyp,
            "datumVon": datumVon,
            "datumBis": datumBis
        }
        
        if zaehlpunkt:
            endpoint = urljoin(self.base_url, f"/zaehlpunkte/{zaehlpunkt}/messwerte")
        else:
            endpoint = urljoin(self.base_url, "/zaehlpunkte/messwerte")
            
        return self.make_authenticated_request(endpoint, method="GET", params=params)

    def get_quarter_hour_values(self, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None) -> Optional[Dict]:
        """ 
        Fetches quarter-hourly measured values.
        If a zaehlpunkt is provided, fetches measured values for that specific meter.        
        """
        return self.get_messwerte("QUARTER_HOUR", zaehlpunkt, datumVon, datumBis)

    def get_daily_values(self, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None) -> Optional[Dict]:
        """ 
        Fetches daily measured values. 
        If a zaehlpunkt is provided, fetches measured values for that specific meter.
        """
        return self.get_messwerte("DAY", zaehlpunkt, datumVon, datumBis)

    def get_meter_readings(self, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None) -> Optional[Dict]:
        """ Fetches meter readings. 
        If a zaehlpunkt is provided, fetches meter readings for that specific meter."""
        return self.get_messwerte("METER_READ", zaehlpunkt, datumVon, datumBis)