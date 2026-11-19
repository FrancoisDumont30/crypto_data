"""Module for PostgreSQL database interaction (insertions and queries)."""

import psycopg2
from psycopg2.extras import execute_values
from contextlib import closing
from airflow.sdk import BaseHook

import logging
logger = logging.getLogger(__name__)

def get_db_url():
    from airflow.sdk import BaseHook
    return BaseHook.get_connection("crypto_db").get_uri()

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



def insert_coingecko_data(data_list: list[dict]) -> None:
    """Save CoinGecko market snapshots into the PostgreSQL `market_snapshots` table.

    Duplicates on (coin_id, collected_at) are silently ignored, so a retry
    does not fail.

    Args:
        data_list: List of validated dictionaries (keys = column names).
    """
    with closing(psycopg2.connect(get_db_url())) as conn:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO market_snapshots
                    (coin_id, coin_symbol, coin_name, current_price, market_cap,
                     total_volume, last_updated, collected_at)
                VALUES %s
                ON CONFLICT (coin_id, collected_at) DO NOTHING
                """,
                data_list,
                template=(
                    "(%(coin_id)s, %(coin_symbol)s, %(coin_name)s, %(current_price)s, "
                    "%(market_cap)s, %(total_volume)s, %(last_updated)s, %(collected_at)s)"
                ),
            )

def get_unique_crypto(since_hours: int | None = 24) -> list:
    """Retrieve distinct `(coin_id, coin_symbol)` pairs collected recently.

    Args:
        since_hours: Time window in hours. If None, queries the entire table.

    Returns:
        A list of tuples representing unique cryptocurrencies.
    """
    query = "SELECT DISTINCT coin_id, coin_symbol FROM market_snapshots"
    params = ()
    if since_hours is not None:
        query += " WHERE collected_at > now() - make_interval(hours => %s)"
        params = (since_hours,)
    query += " ORDER BY coin_id"

    with closing(psycopg2.connect(get_db_url())) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            res = cur.fetchall()

    if not res:
        logger.warning("Couldn't find any unique crypto")

    return res


def insert_klines_data(df) -> int:
    """Insert a batch of klines into the target PostgreSQL `klines` table.

    Args:
        df: DataFrame containing klines ready to be loaded.

    Returns:
        The total number of rows actually inserted.
    """
    if df.empty:
        return 0

    tuples = list(df[OUTPUT_COLUMNS].itertuples(index=False, name=None))
    columns_str = ", ".join(OUTPUT_COLUMNS)

    query = f"""
            INSERT INTO klines ({columns_str}) 
            VALUES %s
            ON CONFLICT (symbol, interval, open_time) DO NOTHING
            RETURNING 1;
            """
    
    with closing(psycopg2.connect(get_db_url())) as conn:
        with conn, conn.cursor() as cur:
            inserted = execute_values(cur, query, tuples, page_size=1000, fetch=True)
            num = len(inserted)

    logger.info("%s rows inserted", num)
    return num


def purge_old_klines(symbol: str, limit_date, interval: str = "1m") -> int:
    """Delete obsolete klines for a given symbol from the database.

    Targets rows where `open_time` is strictly older than `limit_date`.

    Args:
        symbol: Trading pair symbol.
        limit_date: Threshold date for purging.
        interval: Candlestick interval.

    Returns:
        The number of rows deleted from the table.
    """
    query = """
        DELETE FROM klines
        WHERE symbol = %s
          AND interval = %s
          AND open_time < %s;
    """
    params = (symbol, interval, limit_date)

    with closing(psycopg2.connect(get_db_url())) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            row_count = cur.rowcount

    logger.info('%s rows deleted from table "klines"', row_count)
    return row_count


def upsert_mapping(mapper: dict) -> int:
    """Insert or update (Upsert) the crypto mapping table in the database.

    Args:
        mapper: Dictionary mapping coin IDs to exchange symbols.

    Returns:
        The number of rows affected by the operation.
    """
    if not mapper:
        return 0

    query = f"""
            INSERT INTO crypto_mapping 
            (coin_id, binance_symbol) VALUES %s
            ON CONFLICT (coin_id) 
            DO UPDATE SET binance_symbol = EXCLUDED.binance_symbol, updated_at = now();
            """
    
    params = list(mapper.items())

    with closing(psycopg2.connect(get_db_url())) as conn:
        with conn, conn.cursor() as cur:
            execute_values(cur, query, params)
            num = cur.rowcount

    logger.info("%s rows upserted", num)
    return num


def get_all_symbols() -> list:
    """Retrieve the exhaustive list of Binance symbols registered in `crypto_mapping`.

    Returns:
        A list of string symbols.
    """
    query = """
            SELECT binance_symbol
            FROM crypto_mapping 
            ORDER BY binance_symbol;
            """

    with closing(psycopg2.connect(get_db_url())) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query)
            res = cur.fetchall()

    logger.info("%s symbols found", len(res))
    return [x[0] for x in res]