import psycopg2
import os
from contextlib import closing
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_last_price(coin_id: str) -> list | None:
    """Retrieve the latest price record for a specific coin."""
    query = """
            SELECT coin_id, current_price, collected_at
            FROM market_snapshots 
            WHERE coin_id = %s
            ORDER BY collected_at DESC
            LIMIT 1;
            """

    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    # Connect and fetch the most recent market snapshot
    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, (coin_id,))
            res = cur.fetchone()

    return list(res) if res else None


# def get_db_klines(coin_id: str, start: datetime, end: datetime) -> dict | None:
#     """Retrieve historical candlestick (klines) data for a coin within a date range."""
#     crypto_db_url = os.environ["CRYPTO_DB_URL"]
#     selected_col = ['open_time', 'open', 'high', 'low', 'close', 'volume']

#     query1 = """
#             SELECT binance_symbol
#             FROM crypto_mapping
#             WHERE coin_id = %s;
#             """
    
#     query2 = """
#             SELECT 
#                 open::float8 AS open,
#                 high::float8 AS high,
#                 low::float8 AS low,
#                 close::float8 AS close,
#                 volume::float8 AS volume,
#                 open_time
#             FROM klines
#             WHERE symbol = %s
#             AND interval = '1m'
#             AND open_time >= %s
#             AND close_time <= %s
#             ORDER BY open_time ASC;
#             """

#     with closing(psycopg2.connect(crypto_db_url)) as conn:
#         with conn, conn.cursor() as cur:
#             # Map coin_id to exchange symbol
#             cur.execute(query1, (coin_id,))
#             symbol_row = cur.fetchone()
#             if not symbol_row:
#                 return None
#             symbol = symbol_row[0]

#             # Fetch klines data
#             cur.execute(query2, (symbol, start, end))
#             res = cur.fetchall()

#     if not res:
#         return None

#     # Format results into a dictionary response
#     candles = [dict(zip(selected_col, x)) for x in res]

#     return {
#         "coin_id": coin_id, 
#         "symbol": symbol, 
#         "count": len(res),
#         "candles": candles
#     }


MAX_ROWS = 10_080  # 7 days of 1m candles


def get_db_klines(coin_id: str, start: datetime, end: datetime,
                  limit: int = MAX_ROWS) -> dict | None:
    """Retrieve 1m candles for a coin between start and end (oldest first)."""
    crypto_db_url = os.environ["CRYPTO_DB_URL"]
    selected_col = ["open_time", "open", "high", "low", "close", "volume"]

    query1 = "SELECT binance_symbol FROM crypto_mapping WHERE coin_id = %s;"
    query2 = """
        SELECT
            open_time,
            open::float8,
            high::float8,
            low::float8,
            close::float8,
            volume::float8
        FROM klines
        WHERE symbol = %s
          AND interval = '1m'
          AND open_time >= %s
          AND close_time <= %s
        ORDER BY open_time
        LIMIT %s;
    """

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query1, (coin_id,))
            symbol_row = cur.fetchone()
            if not symbol_row:
                return None
            symbol = symbol_row[0]

            cur.execute(query2, (symbol, start, end, limit))
            res = cur.fetchall()

    if not res:
        return None

    return {
        "coin_id": coin_id,
        "symbol": symbol,
        "count": len(res),
        "candles": [dict(zip(selected_col, row)) for row in res],
    }