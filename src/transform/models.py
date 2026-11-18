"""Module for cleaning, typing, and transforming raw payloads."""

import logging
import pandas as pd
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import BaseModel, AwareDatetime, ValidationError, Field, ConfigDict

logger = logging.getLogger(__name__)

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



class MarketSnapshot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    coin_id: str = Field(alias="id")
    coin_symbol: str = Field(alias="symbol")
    coin_name: str = Field(alias="name")
    current_price: Decimal | None = None
    market_cap: Decimal | None = None
    total_volume: Decimal | None = None
    last_updated: AwareDatetime | None = None
    collected_at: AwareDatetime


def process_coingecko_data(raw_data: list[dict]) -> list[dict]:
    """Process and validate raw data from CoinGecko using Pydantic.

    Individual invalid lines are logged as warnings and skipped.

    Args:
        raw_data: Raw list of CoinGecko snapshots.

    Returns:
        A list of validated and standardized dictionaries.
    
    Raises:
        RuntimeError: If raw_data is empty or if the data rejection rate exceeds 50%.
    """

    if not raw_data:
        raise RuntimeError("Received empty raw data from CoinGecko API.")
    
    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    processed_list = []
    rejected_count = 0
    total_count = len(raw_data)

    for d in raw_data:
        row_data = {**d, "collected_at": collected_at}
        try:
            snapshot = MarketSnapshot.model_validate(row_data)
            processed_list.append(snapshot.model_dump())
        except ValidationError as e:
            rejected_count += 1
            coin_id = d.get("id", "unknown")
            logger.warning("Invalid data for coin_id '%s': %s", coin_id, e.errors())

    # Alert
    if rejected_count / total_count > 0.5:
        raise RuntimeError(
            f"Abnormal data rejection rate: {rejected_count}/{total_count} rows rejected. "
            "API format might have changed."
        )

    return processed_list
