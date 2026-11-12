
import logging
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://api.binance.com"
EXCHANGE_URL = f"{BASE_URL}/api/v3/exchangeInfo"

# MAX_LIMIT = 1000          # maximum autorisé par Binance
# PAUSE_BETWEEN_CALLS = 0.2  # secondes entre deux pages (respect du rate limit)
# MAX_RETRIES = 5
TIMEOUT = 10               # secondes
# # Position de close_time dans une bougie brute (voir le tableau des 12 champs)
# CLOSE_TIME_INDEX = 6

logger = logging.getLogger(__name__)

def get_binance_symbols():
    resp = requests.get(EXCHANGE_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    result = []
    for dico in resp.json()['symbols'] :
        if (dico['status']=='TRADING') and (dico['quoteAsset']=='USDT'):
            result.append(dico['symbol'])
    result = set(result)

    return result
