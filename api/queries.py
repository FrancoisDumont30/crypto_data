import psycopg2
from psycopg2.extras import execute_values
import os
from contextlib import closing
import logging
from datetime import date

logger = logging.getLogger(__name__)


def get_last_price(coin_id: str) -> tuple | None :

    """
    Récupère le dernier prix d'une monnaie
    """

    query = """
            SELECT coin_id, current_price, collected_at
            FROM market_snapshots 
            WHERE coin_id = %s
            ORDER BY collected_at DESC
            LIMIT 1;
            """

    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur :
            cur.execute(query, (coin_id,))
            res = cur.fetchone()

    # logger.info(f"{num} symboles trouvés")

    if res :
        return list(res)
    else :
        return None


def get_db_klines(coin_id: str, start : date, end : date) :
    """
    Récupère les klines d'une monnaie entre 2 datetime.
    """
    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    selected_col = ['open_time','open', 'high', 'low','close','volume']

    query1 = """
            SELECT binance_symbol
            FROM crypto_mapping
            WHERE coin_id = %s ;
            """
    
    param1 = (coin_id,)

    query2 = f"""
            SELECT 
                open::float8 AS open,
                high::float8 AS high,
                low::float8 AS low,
                close::float8 AS close,
                volume::float8 AS volume,
                open_time
            FROM klines
            WHERE symbol = %s
            AND interval = '1m'
            AND open_time >= %s
            AND close_time <= %s ;
            """

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur :
            cur.execute(query1, param1)
            symbol = cur.fetchone()[0]

            param2 = (symbol, start, end)
            cur.execute(query2, param2)
                 
            res = cur.fetchall()


        if res :

            candles = [dict(zip(selected_col, x)) for x in res]
            
            answer = {"coin_id": coin_id, 
                      "symbol": symbol, 
                      "count": len(res),
                      "candles" : candles}

        return answer
