"""Module for fetching raw data from the public Binance API."""

import logging
import time
from datetime import datetime, timezone

import requests

BASE_URL = "https://api.binance.com"
KLINES_URL = f"{BASE_URL}/api/v3/klines"

EXCHANGE_URL = f"{BASE_URL}/api/v3/exchangeInfo"

MAX_LIMIT = 1000          # Maximum allowed by Binance
PAUSE_BETWEEN_CALLS = 0.2  # Seconds between pages (rate limit compliance)
MAX_RETRIES = 5
TIMEOUT = 10               # Seconds

# Position of close_time in a raw candle array (see the 12-field layout)
CLOSE_TIME_INDEX = 6

logger = logging.getLogger(__name__)


def _to_ms(dt: datetime) -> int:
    """Convert a datetime object to a Unix timestamp in milliseconds UTC.

    Note:
        A naive datetime (without timezone) is treated as UTC by default.

    Args:
        dt: Datetime object to convert.

    Returns:
        The corresponding timestamp in milliseconds (integer).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _fetch_page(session: requests.Session, params: dict) -> list:
    """Call the Binance API to fetch a page of data with retry logic.

    Handled error cases:
    - 429 / 418 (Rate Limit): Wait based on the delay specified by the API.
    - 5xx and network errors: Retries with exponential backoff.
    - Other 4xx (e.g., invalid symbol): Immediate failure without retry.

    Args:
        session: Active HTTP session for connection pooling.
        params: Dictionary of API request parameters.

    Returns:
        The raw list returned by the API for this page.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(KLINES_URL, params=params, timeout=TIMEOUT)

            if resp.status_code in (429, 418):
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                logger.warning("Binance rate limit (%s), pausing for %ss", resp.status_code, wait)
                time.sleep(wait)
                continue

            if 400 <= resp.status_code < 500:
                resp.raise_for_status()  # Permanent error: do not retry

            resp.raise_for_status()      # Raise for 5xx -> handled below
            return resp.json()

        except (requests.ConnectionError, requests.Timeout) as exc:
            error = exc
        except requests.HTTPError as exc:
            if exc.response is not None and 400 <= exc.response.status_code < 500:
                raise
            error = exc

        wait = 2 ** attempt
        logger.warning("Binance call failed (attempt %s/%s): %s. Retrying in %ss",
                       attempt, MAX_RETRIES, error, wait)
        time.sleep(wait)

    raise RuntimeError(f"Binance unreachable after {MAX_RETRIES} attempts")


def get_klines(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    session: requests.Session | None = None,
) -> list[list]:
    """Retrieve the complete history of klines for a given symbol.

    Covers the period from `start` (inclusive) to `end` (exclusive).

    Args:
        symbol: Target trading pair, e.g., "BTCUSDT".
        interval: Candlestick time interval ("1m", "1h", "1d", etc.).
        start: Start date and time (UTC).
        end: End date and time (UTC, exclusive).
        session: Optional HTTP session.

    Returns:
        A raw list of lists (containing 12 elements each), untransformed.
    """
    start_ms = _to_ms(start)
    end_ms = _to_ms(end) - 1  # Binance endTime is inclusive, so subtract 1 ms
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

        if not page:  # No more data (or crypto launched after `start`)
            break

        all_klines.extend(page)
        logger.info("%s: %s klines fetched (total %s)", symbol, len(page), len(all_klines))

        # Next page: right after the last received candle's close time
        start_ms = page[-1][CLOSE_TIME_INDEX] + 1

        if len(page) < MAX_LIMIT:  # Last page
            break

        time.sleep(PAUSE_BETWEEN_CALLS)

    return all_klines


def fetch_binance_symbols() -> set:
    """Retrieve all active trading symbols from the public Binance API.

    Filters pairs to keep only those with 'TRADING' status and 'USDT' as quote asset.

    Returns:
        A set of string symbols (e.g., {"BTCUSDT", "ETHUSDT"}).

    Raises:
        requests.exceptions.HTTPError: If the API call fails.
    """
    resp = requests.get(EXCHANGE_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    result = []

    for dico in resp.json()['symbols']:
        if (dico['status'] == 'TRADING') and (dico['quoteAsset'] == 'USDT'):
            result.append(dico['symbol'])
            
    result = set(result)

    return result