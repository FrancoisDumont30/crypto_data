"""Module de récupération des données de marché depuis l'API CoinGecko."""

import requests

URL = "https://api.coingecko.com/api/v3/coins/markets"


def fetch_coingecko_data():
    """
    Interroge l'API CoinGecko pour récupérer les snapshots de marché.

    Cible spécifiquement les 50 crypto-monnaies les plus capitalisées.

    Returns:
        Une liste de dictionnaires contenant les données brutes des cryptos.
    """


    params = {"vs_currency": "usd", "per_page": 50, "page": 1}
    r = requests.get(URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()