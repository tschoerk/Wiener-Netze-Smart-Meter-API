import requests
import time
import logging
from datetime import datetime, timedelta
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class WNAPIClient:
    BASE_URL = "https://api.wstw.at/gateway/WN_SMART_METER_API/1.0"

    def __init__(self, client_id: str, client_secret: str, api_key: str, max_retries: int = 3, retry_delay: int = 5):
        self.client_id = client_id
        self.client_secret = client_secret
        self.api_key = api_key
        self.token = None
        self.token_expiry = 0  # UNIX timestamp when the token expires
        self.max_retries = max_retries  # Max retry attempts
        self.retry_delay = retry_delay  # Delay between retries in seconds
        self.session = requests.Session()  # New persistent session

    def get_bearer_token(self) -> str:
        """
        Retrieves a Bearer Token, refreshing it if expired.
        Implements automatic retries.
        """
        if self.token and time.time() < self.token_expiry:
            return self.token  # Return cached token if still valid

        url = "https://log.wien/auth/realms/logwien/protocol/openid-connect/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(url, data=data, headers=headers, timeout=10)
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

    def make_authenticated_request(self, endpoint: str, method: str = "GET", data=None):
        """
        Makes an API request with a valid Bearer Token.
        Implements automatic retries.
        """
        token = self.get_bearer_token()
        if not token:
            logging.exception("No valid token available, request aborted.")
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "x-Gateway-APIKey": self.api_key
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = self.session.get(endpoint, headers=headers, timeout=10)
                elif method.upper() == "POST":
                    response = self.session.post(endpoint, headers=headers, json=data, timeout=10)
                else:
                    logging.error(f"Unsupported HTTP method: {method}")
                    return None

                response.raise_for_status()
                logging.info(f"Successful {method} request to {endpoint}")
                return response.json()

            except requests.HTTPError:
                logging.exception(f"HTTP error on {method} request to {endpoint}")

                if response.status_code == 401:
                    logging.warning("Token may be expired. Fetching new token...")
                    self.token = None  # Force token refresh
                    return self.make_authenticated_request(endpoint, method, data)

            except requests.Timeout:
                logging.warning(f"Timeout on {method} request to {endpoint} (Attempt {attempt}/{self.max_retries})")

            except RequestException:
                logging.exception(f"Request error")

            if attempt < self.max_retries:
                logging.info(f"Retrying request in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
            else:
                logging.critical(f"Max retries reached. Unable to complete request: {endpoint}")
                return None

    def get_anlagendaten(self, zaehlpunkt: str = None, result_type: str = "ALL"):
        """
        Fetches information about a specific or all smart meter(s) associated with the user.
        If a zaehlpunkt is provided, fetches details for that specific meter.
        """
        if zaehlpunkt:
            endpoint = f"{self.BASE_URL}/zaehlpunkte/{zaehlpunkt}"
        else:
            endpoint = f"{self.BASE_URL}/zaehlpunkte?resultType={result_type}"
        return self.make_authenticated_request(endpoint)

    def get_messwerte(self, wertetyp: str, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None):
        """
        Fetches measured values (QUARTER_HOUR, DAY, METER_READ) for smart meters.
        If a zaehlpunkt is provided, fetches measured values for that specific meter.
        Defaults to fetching data from 3 years ago to today.
        """
        if not datumVon:
            datumVon = (datetime.today() - timedelta(days=3*365)).strftime('%Y-%m-%d')
        if not datumBis:
            datumBis = datetime.today().strftime('%Y-%m-%d')

        if zaehlpunkt:
            endpoint = f"{self.BASE_URL}/zaehlpunkte/{zaehlpunkt}/messwerte?wertetyp={wertetyp}&datumVon={datumVon}&datumBis={datumBis}"
        else:
            endpoint = f"{self.BASE_URL}/zaehlpunkte/messwerte?wertetyp={wertetyp}&datumVon={datumVon}&datumBis={datumBis}"
        return self.make_authenticated_request(endpoint)

    def get_quarter_hour_values(self, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None):
        """ 
        Fetches quarter-hourly measured values.
        If a zaehlpunkt is provided, fetches measured values for that specific meter.        
        """
        return self.get_messwerte("QUARTER_HOUR", zaehlpunkt, datumVon, datumBis)

    def get_daily_values(self, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None):
        """ 
        Fetches daily measured values. 
        If a zaehlpunkt is provided, fetches measured values for that specific meter.
        """
        return self.get_messwerte("DAY", zaehlpunkt, datumVon, datumBis)

    def get_meter_readings(self, zaehlpunkt: str = None, datumVon: str = None, datumBis: str = None):
        """ Fetches meter readings. 
        If a zaehlpunkt is provided, fetches meter readings for that specific meter."""
        return self.get_messwerte("METER_READ", zaehlpunkt, datumVon, datumBis)