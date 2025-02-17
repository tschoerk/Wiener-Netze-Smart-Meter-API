"""Example Script for Using the WNAPIClient.

This script demonstrates how to use the WNAPIClient to interact with the Wiener Netze Smart Meter API.
It shows how to:
  - Obtain a bearer token,
  - Fetch information for all smart meters,
  - Retrieve details for a specific smart meter,
  - Get quarter-hourly measured values (defaulting to the last 3 years),
  - Get daily measured values for a specific meter (defaulting to the last 3 years),
  - Fetch meter readings for a specific meter for a defined date range.

Usage:
    python example.py
"""  # noqa: E501

import logging

from client import WNAPIClient  # Adjust the import based on your project structure

if __name__ == "__main__":
    # Configure logging for the example script.
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Initialize the API client with your credentials.
    client = WNAPIClient(
        client_id="client_id",
        client_secret="",
        api_key="api_key",
    )

    # Retrieve the bearer token.
    token = client.get_bearer_token()

    # Fetch all smart meters.
    smart_meters = client.get_anlagendaten()
    msg = f"All smart meters: {smart_meters}"
    logging.debug(msg)

    # Fetch specific smart meter details.
    smart_meter_number = "AT0010000000000000001000000000000"
    specific_meter = client.get_anlagendaten(smart_meter_number)
    msg = f"Details for smart meter {smart_meter_number}: {specific_meter}"
    logging.debug(msg)

    # Fetch quarter-hourly measured values for all meters (defaults to last 3 years).
    quarter_hour_values = client.get_quarter_hour_values()
    msg = f"Quarter-hour values: {quarter_hour_values}"
    logging.debug(msg)

    # Fetch daily measured values for a specific meter (defaults to last 3 years).
    daily_values = client.get_daily_values(smart_meter_number)
    msg = f"Daily values for meter {smart_meter_number}: {daily_values}"
    logging.debug(msg)

    # Fetch daily measured values for a specific meter (defaults to last 3 years) with pagination (defaults to 30 days chunks).  # noqa: E501
    daily_values_paginated = client.get_daily_values(smart_meter_number, paginate=True)
    msg = f"Daily values for meter {smart_meter_number} with pagination: {daily_values_paginated}"  # noqa: E501
    logging.debug(msg)

    # Define a specific date range for meter readings.
    date_from = "2025-01-01"
    date_to = "2025-01-02"

    # Fetch meter readings for the specific meter over the given date range.
    meter_readings = client.get_meter_readings(smart_meter_number, date_from, date_to)
    msg = f"Meter readings for meter {smart_meter_number} from {date_from} to {date_to}: {meter_readings}"  # noqa: E501
    logging.debug(msg)

    # Fetch meter readings for a specific meter for a specific time period with pagination in 7 days chunks  # noqa: E501
    meter_readings_paginated = client.get_meter_readings(
        smart_meter_number,
        date_from,
        date_to,
        paginate=True,
        chunk_days=7,
    )
    msg = f"Meter readings for meter {smart_meter_number} from {date_from} to {date_to} with pagination in 7 days chunks: {meter_readings_paginated}"  # noqa: E501
    logging.debug(msg)
