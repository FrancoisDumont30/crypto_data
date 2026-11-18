"""ETL pipeline orchestration module (Extraction, Transformation, Loading)."""

import logging

import pandas as pd
from datetime import datetime, timezone, timedelta

from load.parquet_io import get_last_open_time, write_klines_to_parquet, calculate_limit_date, read_klines_from_parquet, list_parquet_files
from load.postgres_db import insert_klines_data, purge_old_klines
from extract.binance import get_klines
from transform.models import transform

logger = logging.getLogger(__name__)

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


def ingest_binance_pair(symbol: str, interval: str = "1m", backfill_days: int = 30) -> dict:
    """Execute the historical ingestion pipeline for a given trading pair.

    Fetches, transforms, and saves the latest days of data.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT").
        interval: Candlestick time interval.
        backfill_days: Number of historical days to backfill.

    Returns:
        A dictionary summarizing the execution metrics.
    """
    last_open_time = get_last_open_time(symbol, interval)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    if last_open_time:
        start = last_open_time + timedelta(minutes=1)
    else:
        start = now - timedelta(days=backfill_days)

    info = {
        "symbol": f"{symbol}",
        "interval": f"{interval}",
        "start": f"{start}",
        "end": f"{now}",
        "rows": 0,
    }

    if start >= now:
        logger.info("%s: nothing to fetch", symbol)
        return info

    # Fetch, transform, and write data
    resp = get_klines(symbol, interval, start, now)
    df = transform(resp, symbol, interval)
    write_klines_to_parquet(df)

    info["rows"] = len(df)
    logger.info(info)
    return info


def ingest_recent_klines(symbol: str, days: int = 7, interval: str = "1m") -> dict:
    """Orchestrate incremental updates of recent candles from Parquet files.

    Reads recent Parquet files, synchronizes the database, and purges obsolete data.

    Args:
        symbol: Target trading pair symbol.
        days: Number of recent days to process.
        interval: Candlestick interval.

    Returns:
        A dictionary of pipeline summary metrics.
    """
    limit_date = calculate_limit_date(days=days)

    # 1. Read Parquet files
    parquet_files = list_parquet_files(symbol, limit_date, interval)

    # Load parquet file contents into a DataFrame
    if parquet_files:
        df = read_klines_from_parquet(parquet_files)
    else:
        df = pd.DataFrame(columns=OUTPUT_COLUMNS)

    # Filter by open_time (UTC)
    limit_timestamp = pd.Timestamp(limit_date, tz="UTC")
    df = df.loc[df["open_time"] >= limit_timestamp]
    row_left = len(df)
    logger.info("%s rows retained after filtering.", row_left)

    # 2. Batch insertion with duplicate handling
    inserted_rows = insert_klines_data(df)
    
    # 3. Purge data older than the limit
    purged_rows = purge_old_klines(symbol, limit_timestamp)
    logger.info("%s row(s) purged.", purged_rows)

    # 4. Return summary dictionary
    return {
        "symbol": symbol,
        "limit_date": limit_date.isoformat(),
        "filtered_rows": row_left,
        "db_inserted_rows": inserted_rows,
        "db_purged_rows": purged_rows,
    }