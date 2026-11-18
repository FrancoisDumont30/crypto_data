"""Module for fetching market data from the CoinGecko API."""

import requests

URL = "https://api.coingecko.com/api/v3/coins/markets"


def fetch_coingecko_data() -> list[dict]:
    """Query the CoinGecko API to retrieve market snapshots.

    Specifically targets the top 50 cryptocurrencies by market capitalization.

    Returns:
        A list of dictionaries containing raw cryptocurrency data.
    """
    params = {"vs_currency": "usd", "per_page": 50, "page": 1}
    r = requests.get(URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()