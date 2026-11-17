"""Module de récupération des données brutes depuis l'API publique Binance."""

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
    """Convertit un objet datetime en timestamp Unix en millisecondes UTC.

    Note:
        Un datetime naïf (sans timezone) est considéré par défaut comme étant en UTC.

    Args:
        dt: Objet datetime à convertir.

    Returns:
        Le timestamp correspondant en millisecondes (entier).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _fetch_page(session: requests.Session, params: dict) -> list:
    """Appelle l'API Binance pour récupérer une page de données avec mécanisme de réessai (retry).

    Gestion des erreurs gérée :
        - 429 / 418 (Rate Limit) : Attente basée sur le délai indiqué par l'API.
        - 5xx et erreurs réseau : Nouvelles tentatives avec backoff exponentiel.
        - Autres 4xx (ex: symbole invalide) : Échec immédiat sans réessai.

    Args:
        session: Session HTTP active pour mutualiser les connexions.
        params: Dictionnaire des paramètres de la requête API.

    Returns:
        La liste brute retournée par l'API pour cette page.
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
    """Récupère l'historique complet des bougies (klines) pour un symbole donné.

    Couvre la période allant de `start` (inclus) à `end` (exclu).

    Args:
        symbol: Paire de trading ciblée, ex. « BTCUSDT ».
        interval: Intervalle temporel des bougies (« 1m », « 1h », « 1d », etc.).
        start: Date et heure de début (UTC).
        end: Date et heure de fin (UTC, exclue).
        session: Session HTTP optionnelle.

    Returns:
        Une liste brute de listes (contenant 12 éléments chacune), sans transformation.
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
    """Récupère l'ensemble des symboles de trading actifs sur l'API Binance.

    Filtre les paires pour ne conserver que celles dont le statut est « TRADING »
    et dont la devise de cotation est « USDT ».

    Returns:
        Un ensemble (set) de chaînes de caractères représentant les symboles (ex: {"BTCUSDT", "ETHUSDT"}).

    Raises:
        requests.exceptions.HTTPError: Si l'appel API échoue.
    """
    resp = requests.get(EXCHANGE_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    result = []
    for dico in resp.json()['symbols'] :
        if (dico['status']=='TRADING') and (dico['quoteAsset']=='USDT'):
            result.append(dico['symbol'])
    result = set(result)

    return result