"""Collecteur Binance : récupération de l'historique de bougies (klines).

Endpoint public (pas de clé API) : GET /api/v3/klines
- 1000 bougies maximum par appel
- startTime / endTime en millisecondes UTC
"""

import logging
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://api.binance.com"
KLINES_URL = f"{BASE_URL}/api/v3/klines"

EXCHANGE_URL = f"{BASE_URL}/api/v3/exchangeInfo"

MAX_LIMIT = 1000          # maximum autorisé par Binance
PAUSE_BETWEEN_CALLS = 0.2  # secondes entre deux pages (respect du rate limit)
MAX_RETRIES = 5
TIMEOUT = 10               # secondes

# Position de close_time dans une bougie brute (voir le tableau des 12 champs)
CLOSE_TIME_INDEX = 6

logger = logging.getLogger(__name__)


def _to_ms(dt: datetime) -> int:
    """Convertit un datetime en millisecondes UTC (naïf = considéré UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _fetch_page(session: requests.Session, params: dict) -> list:
    """Appelle l'API pour une page, avec retries.

    - 429 / 418 (rate limit) : on attend le délai indiqué par Binance
    - 5xx et erreurs réseau : nouvel essai avec attente croissante
    - autre 4xx (ex. symbole invalide) : erreur immédiate, inutile de réessayer
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(KLINES_URL, params=params, timeout=TIMEOUT)

            if resp.status_code in (429, 418):
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                logger.warning("Rate limit Binance (%s), pause de %ss", resp.status_code, wait)
                time.sleep(wait)
                continue

            if 400 <= resp.status_code < 500:
                resp.raise_for_status()  # erreur définitive : on ne réessaie pas

            resp.raise_for_status()      # lève pour les 5xx -> traité plus bas
            return resp.json()

        except (requests.ConnectionError, requests.Timeout) as exc:
            error = exc
        except requests.HTTPError as exc:
            if exc.response is not None and 400 <= exc.response.status_code < 500:
                raise
            error = exc

        wait = 2 ** attempt
        logger.warning("Échec appel Binance (essai %s/%s) : %s. Nouvel essai dans %ss",
                       attempt, MAX_RETRIES, error, wait)
        time.sleep(wait)

    raise RuntimeError(f"Binance injoignable après {MAX_RETRIES} essais")


def get_klines(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    session: requests.Session | None = None,
) -> list[list]:
    """Récupère toutes les bougies de `symbol` entre `start` (inclus) et `end` (exclu).

    Paramètres
    ----------
    symbol   : paire Binance, ex. "BTCUSDT"
    interval : "1m", "1h", "1d"...
    start    : datetime de début (UTC)
    end      : datetime de fin (UTC), exclue

    Retourne la liste BRUTE des bougies (liste de listes de 12 éléments),
    sans aucune transformation.
    """
    start_ms = _to_ms(start)
    end_ms = _to_ms(end) - 1  # endTime est inclusif chez Binance : on retire 1 ms
    session = session or requests.Session()

    all_klines: list[list] = []

    while start_ms <= end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": MAX_LIMIT,
        }
        page = _fetch_page(session, params)

        if not page:  # plus de données (ou crypto lancée après `start`)
            break

        all_klines.extend(page)
        logger.info("%s : %s bougies récupérées (total %s)", symbol, len(page), len(all_klines))

        # Page suivante : juste après la dernière bougie reçue
        start_ms = page[-1][CLOSE_TIME_INDEX] + 1

        if len(page) < MAX_LIMIT:  # dernière page
            break

        time.sleep(PAUSE_BETWEEN_CALLS)

    return all_klines

def fetch_binance_symbols() -> set :
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