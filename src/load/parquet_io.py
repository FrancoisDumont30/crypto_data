"""I/O management module for local Parquet files."""

import logging
from pathlib import Path
import os
import pandas as pd
from datetime import datetime, timezone, timedelta, date

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


# Base directory INSIDE the Airflow container (volume ./data mounted to /opt/airflow/data)
DEFAULT_BASE_DIR = Path(os.getenv("DATA_DIR", "/opt/airflow/data")) / "parquet"

# Unique candle key
KEY_COLUMNS = ["symbol", "interval", "open_time"]


def write_klines_to_parquet(df: pd.DataFrame, base_dir: Path | str = DEFAULT_BASE_DIR) -> list[Path]:
    """Write a DataFrame of candles as partitioned Parquet files.

    Target structure:
    '<base_dir>/klines/interval=1m/symbol=BTCUSDT/2026-11.parquet'

    The process is idempotent: if the monthly file already exists, new rows
    are merged with existing ones, duplicates (based on symbol, interval,
    and `open_time`) are removed, and the latest version is kept.

    Args:
        df: Pandas DataFrame containing klines to persist.
        base_dir: Root storage directory.

    Returns:
        The list of written or updated file paths (`Path`).
    """
    if df.empty:
        logger.info("Empty DataFrame: nothing to write")
        return []

    base_dir = Path(base_dir)
    df = df.assign(month=df["open_time"].dt.strftime("%Y-%m"))

    written: list[Path] = []
    for (symbol, interval, month), part in df.groupby(["symbol", "interval", "month"]):
        part = part.drop(columns="month")

        folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{month}.parquet"

        if path.exists():
            part = pd.concat([pd.read_parquet(path), part], ignore_index=True)
            part = part.drop_duplicates(subset=KEY_COLUMNS, keep="last")

        part = part.sort_values("open_time").reset_index(drop=True)

        # Write to a temporary file then replace:
        # a crash during writing will not corrupt the existing file
        tmp_path = path.with_suffix(".parquet.tmp")
        part.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)

        logger.info("%s: %s rows written", path, len(part))
        written.append(path)

    return written


def get_last_open_time(symbol: str, interval: str, base_dir: Path | str = DEFAULT_BASE_DIR):
    """Retrieve the last recorded opening timestamp (`open_time`) for a symbol.

    Args:
        symbol: Trading pair (e.g., "BTCUSDT").
        interval: Candlestick interval.
        base_dir: Root Parquet storage directory.

    Returns:
        The timestamp in milliseconds of the last candle, or None if no file exists.
    """
    base_dir = Path(base_dir)
    folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"

    files = sorted(folder.glob("*.parquet"))  
    if not files:                            
        return None

    col = pd.read_parquet(files[-1], columns=["open_time"])
    return col["open_time"].max()


def calculate_limit_date(days: int = 7) -> date:
    """Calculate the limit date (lower bound) for time filtering.

    Args:
        days: Number of days back from today.

    Returns:
        A `date` object representing the calculated lower bound.
    """
    today_utc = datetime.now(timezone.utc).date()
    return today_utc - timedelta(days=days)


def list_parquet_files(symbol: str, limit_date: date, interval: str = "1m") -> list:
    """Search and list valid Parquet files covering the recent period.

    Args:
        symbol: Target trading pair symbol.
        limit_date: Lower search limit date.
        interval: Klines interval.

    Returns:
        A list of paths (`Path`) pointing to the matching files.
    """
    parquet_files = []
    base_dir = Path(DEFAULT_BASE_DIR)
    folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"

    first_month = limit_date.replace(day=1)

    for file_path in folder.glob("*.parquet"):
        date_str = file_path.stem  # Format "YYYY-MM"

        try:
            file_date = datetime.strptime(date_str, "%Y-%m").replace(tzinfo=timezone.utc).replace(day=1)
               
            # Keep file if its month >= first_month
            if file_date.date() >= first_month:
                parquet_files.append(file_path)

        except ValueError:
            continue

    logger.info("%s parquet files found", len(parquet_files))
    return parquet_files


def read_klines_from_parquet(parquet_files: list) -> pd.DataFrame:
    """Read a list of Parquet files and filter rows according to the limit date.

    Args:
        parquet_files: List of Parquet file paths to load.

    Returns:
        A consolidated and sorted pandas DataFrame.
    """
    df_list = []

    for file_path in parquet_files:
        df_temp = pd.read_parquet(file_path, columns=OUTPUT_COLUMNS)
        df_list.append(df_temp)

    if df_list:
        df = pd.concat(df_list, ignore_index=True)
    else:
        df = pd.DataFrame(columns=OUTPUT_COLUMNS)

    logger.info("%s rows read", len(df))
    return df