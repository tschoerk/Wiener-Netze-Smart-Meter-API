# Wiener Netze Smart Meter API

[![PyPI - Version](https://img.shields.io/pypi/v/wiener-netze-smart-meter-api.svg)](https://pypi.org/project/wiener-netze-smart-meter-api)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wiener-netze-smart-meter-api.svg)](https://pypi.org/project/wiener-netze-smart-meter-api)

-----

## Table of Contents

- [Introduction](#introduction)
- [First Steps](#firststeps)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Introduction
This project provides a Python wrapper for the **official** Wiener Netze Smart Meter API (WN_SMART_METER_API), which is published by Wiener Stadtwerke through their [developer portal](https://api-portal.wienerstadtwerke.at/). Unlike other approaches (notably [fleinze’s vienna-smartmeter API Python wrapper](https://github.com/fleinze/vienna-smartmeter) and [DarwinsBuddy’s HomeAssistant Integration](https://github.com/DarwinsBuddy/WienerNetzeSmartmeter)) that rely on web-login recreation and can fail due to captchas, rate limiting, or other website changes, this wrapper uses the official endpoint.

By following the instructions below, you can acquire the necessary API credentials (client ID, client secret, and API key) from Wiener Stadtwerke’s developer portal and start fetching your power usage data .

## First Steps

1. Create an account at the [Developer Portal of the Wiener Stadtwerke](https://api-portal.wienerstadtwerke.at/)
2. Create an application [here](https://api-portal.wienerstadtwerke.at/portal/applications/create) for the WN_SMART_METER_API
3. When the application is approved you will get an e-mail from API Developer Portal. The **API-key** is then found in the details of the newly created [application](https://api-portal.wienerstadtwerke.at/portal/applications).
4. Write an e-mail to the [Smart Meter Portal Support](mailto:support.sm-portal@wienit.at?subject=Anfrage%20zur%20%C3%9Cberpr%C3%BCfung%20und%20Fertigstellung%20der%20Anmeldung%20zur%20Smart%20Meter-Public%20API&body=Ich%20bitte%20um%20%C3%9Cberpr%C3%BCfung%20und%20Fertigstellung%20der%20Anmeldung%20zur%20Smart%20Meter-Public%20API%0A%0AApplikationsname%20%28aus%20dem%20WSTW%20Developer-Portal%29%3A%20%5BName%20of%20application%20created%20at%20the%20Developer%20Portal%20of%20the%20Wiener%20Stadtwerke%5D%0A%0ASmart%20Meter-Portal%20E-Mail-Adresse%3A%20%5BE-mail%20address%20of%20Smart%20Meter%20Portal%20user%5D) to connect the application with the Smart Meter Portal user. It usually takes 1-2 weeks to get a response.
5. Afterwards the **client-ID** and **client-secret** can be found in the [settings](https://smartmeter-business.wienernetze.at/einstellungen) of the Smart Meter-Businessportal. 


## Installation

```console
pip install wiener-netze-smart-meter-api
```

## Updating

```console
pip install -U wiener-netze-smart-meter-api
```

## Usage
```console
from wiener_netze_smart_meter_api import WNAPIClient
from datetime import datetime

client = WNAPIClient(client_id="client-id", client_secret="client-secret", api_key="API-key")

# Fetch all smart meters
smart_meters = client.get_anlagendaten()
print("All Smart Meters:", smart_meters)

# Fetch specific smart meter details
smart_meter_number = "AT0010000000000000001000000000000"
specific_meter = client.get_anlagendaten(smart_meter_number)
print("Specific Smart Meter:", specific_meter)

# Fetch quarter-hourly measured values for all meters for the last 3 years (default time period)
quarter_hour_values = client.get_quarter_hour_values()
print("Quarter-Hourly Values:", quarter_hour_values)

# Fetch daily measured values for a specific meter for the last 3 years (default time period)
daily_values = client.get_daily_values(smart_meter_number)
print("Daily Values for Specific Meter:", daily_values)

# Fetch daily measured values for a specific meter for the last 3 years (default time period) with pagination in 30 days chunks (default chunk size)
daily_values_paginated = client.get_daily_values(smart_meter_number, paginate=True)
print("Daily Values for Specific Meter with Pagination:", daily_values_paginated)

# Fetch meter readings for a specific meter for a specific time period
meter_readings = client.get_meter_readings(smart_meter_number, "2025-01-01", "2025-01-02")
print("Meter Readings:", meter_readings)

# Fetch meter readings for a specific meter for a specific time period with pagination in 7 days chunks
meter_readings_paginated = client.get_meter_readings(smart_meter_number, "2025-01-01", "2025-01-31", paginate=True, chunk_days=7)
print("Meter Readings Paginated:", meter_readings_paginated)

# Optional settings for the client regarding request retries, delay and timeout.
client = WNAPIClient(
    client_id="client_id",
    client_secret="",
    api_key="api_key",
    max_retries=3,
    retry_delay=5,
    timeout=10,
)

```

## License

`wiener-netze-smart-meter-api` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
