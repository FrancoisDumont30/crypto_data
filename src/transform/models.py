"""Module for cleaning, typing, and transforming raw payloads."""

import pandas as pd
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

RAW_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]

FLOAT_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]

OUTPUT_COLUMNS = [
    "symbol",
    "interval",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def safe_string(val, max_length=None) -> str | None:
    """Clean and secure a raw character string.

    Args:
        val: Raw input value.
        max_length: Optional maximum length to truncate the string.

    Returns:
        The cleaned string, or None if the value is empty.
    """
    if val is None:
        return None
    text = str(val).strip()
    if max_length and len(text) > max_length:
        return text[:max_length]
    return text


def safe_datetime(val) -> datetime | None:
    """Convert an ISO string to a UTC datetime, or return None if empty.

    Args:
        val: Character string in ISO format.

    Returns:
        A timezone-aware datetime object (UTC) or None.
    """
    if not val:
        return None
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    return val


def safe_numeric(val) -> Decimal | None:
    """Properly convert a value to Decimal for PostgreSQL NUMERIC types.

    Args:
        val: Raw numeric value (int, float, str).

    Returns:
        A secure Decimal object or None.
    """
    if val is None:
        return None
    try:
        # Using str() avoids inaccuracies from native Python floats
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return None


def transform(raw: list[list], symbol: str, interval: str) -> pd.DataFrame:
    """Transform raw Binance klines lists into structured DataFrames.

    Args:
        raw: Raw list of candles returned by the API.
        symbol: Symbol of the pair concerned.
        interval: Time interval of the candles.

    Returns:
        A pandas DataFrame ready for insertion or storage.
    """
    if not raw:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
      
    df = pd.DataFrame(raw, columns=RAW_COLUMNS).drop(columns=['ignore'])

    # Apply types
    df['symbol'] = symbol
    df['interval'] = interval
    df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].astype(float)
    df['trades'] = df['trades'].astype('int64')

    for col in ("open_time", "close_time"):
        df[col] = pd.to_datetime(df[col], unit="ms", utc=True)

    df = (
        df[OUTPUT_COLUMNS]
        .drop_duplicates(subset=["symbol", "interval", "open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )

    return df


# Type configuration dictionary per column
COLUMN_MAPPINGS = {
    "coin_id": safe_string,
    "coin_symbol": safe_string,
    "coin_name": safe_string,
    "current_price": safe_numeric,
    "market_cap": safe_numeric,
    "total_volume": safe_numeric,
    "last_updated": safe_datetime,
    "collected_at": safe_datetime,
}


def process_coingecko_data(raw_data: list[dict]) -> list[dict]:
    """Process and normalize raw data from CoinGecko.

    Filters relevant fields and adds a normalized timestamp (`collected_at`).

    Args:
        raw_data: Raw list of CoinGecko snapshots.

    Returns:
        A list of cleaned and standardized dictionaries.
    """
    FIELDS = ["id", "symbol", "name", "current_price", "market_cap", "total_volume", "last_updated"]
    collected_at = datetime.now(timezone.utc).replace(microsecond=0)

    processed_list = []
    for d in raw_data:
        filtered_dict = {}
        for k in FIELDS:
            if k in d:
                val = d[k]
                if k in COLUMN_MAPPINGS:
                    filtered_dict[k] = COLUMN_MAPPINGS[k](val)
                else:
                    filtered_dict[k] = val
        
        # Add collection timestamp for each dictionary in the loop
        filtered_dict["collected_at"] = collected_at
        processed_list.append(filtered_dict)

    return processed_list