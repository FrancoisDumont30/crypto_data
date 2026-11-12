import requests

URL = "https://api.coingecko.com/api/v3/coins/markets"


def fetch_coingecko_data():
    params = {"vs_currency": "usd", "per_page": 50, "page": 1}
    r = requests.get(URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()