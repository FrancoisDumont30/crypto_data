
import logging

import requests

BASE_URL = "https://api.binance.com"
EXCHANGE_URL = f"{BASE_URL}/api/v3/exchangeInfo"

TIMEOUT = 10               # secondes

logger = logging.getLogger(__name__)

def get_binance_symbols() -> set :
    """
    Récupère tous les symbols de l'API de binance avec
    un filtre status = TRADING et monnaie = USDT 
    """
    resp = requests.get(EXCHANGE_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    result = []
    for dico in resp.json()['symbols'] :
        if (dico['status']=='TRADING') and (dico['quoteAsset']=='USDT'):
            result.append(dico['symbol'])
    result = set(result)

    return result


