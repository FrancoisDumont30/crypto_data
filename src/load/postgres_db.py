import psycopg2
from psycopg2.extras import execute_values
import os
from contextlib import closing

import logging
logger = logging.getLogger(__name__)


from dotenv import load_dotenv

load_dotenv() 

CRYPTO_DB_URL = os.getenv('CRYPTO_DB_URL')


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


def insert_coingecko_data(data_list : list):
    """
    Enregistre les données dans la base PostgreSQL market_snapshots
    """
    
    with psycopg2.connect(CRYPTO_DB_URL) as conn:
        with conn.cursor() as cur:
            execute_values(
                cur, 
                """
                INSERT INTO market_snapshots
                    (coin_id, coin_symbol, coin_name, current_price, market_cap, total_volume,
                    last_updated, collected_at)
                VALUES %s
                ON CONFLICT (coin_id, collected_at) DO NOTHING
                """, 
                data_list,
                # On mappe chaque clé du dictionnaire vers la colonne correspondante
                template="(%(id)s, %(symbol)s, %(name)s, %(current_price)s, %(market_cap)s, %(total_volume)s, %(last_updated)s, %(collected_at)s)"
            )


def get_unique_crypto(since_hours: int | None = 24) :
    """
    Renvoie les (coin_id, coin_symbol) distincts collectés sur les `since_hours` dernières heures.
    since_hours=None : pas de filtre de temps (toute la table).
    """
    query = "SELECT DISTINCT coin_id, coin_symbol FROM market_snapshots"
    params = ()
    if since_hours is not None:
        query += " WHERE collected_at > now() - make_interval(hours => %s)"
        params = (since_hours,)
    query += " ORDER BY coin_id"

    with closing(psycopg2.connect(CRYPTO_DB_URL)) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            res = cur.fetchall()

            return res

    if len(res) == 0 :
        logger.warning("Couldn't find any unique crypto")

def insert_klines_data(df) -> int:
    """
    Insère les klines dans la table klines.
    Renvoie le nombre de lignes réellement insérées.
    """
    if df.empty:
        return 0

    # tuples = [tuple(x) for x in df.to_numpy()]
    tuples = list(df[OUTPUT_COLUMNS].itertuples(index=False, name=None))

    columns_str = ", ".join(OUTPUT_COLUMNS)

    query = f"""
            INSERT INTO klines ({columns_str}) 
            VALUES %s
            ON CONFLICT (symbol, interval, open_time) DO NOTHING
            RETURNING 1;
            """
    
    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            inserted = execute_values(cur, query, tuples, page_size=1000, fetch=True)
            num = len(inserted)

    logger.info(f"{num} lignes insérées")
    return num


def purge_old_klines(symbol: str, limit_date, interval: str = "1m") -> int:
    """
    Supprime les lignes de ce symbole dont open_time est antérieur à limit_date.
    Renvoie le nombre de lignes supprimées.
    """
    query = """
        DELETE FROM klines
        WHERE symbol = %s
          AND interval = %s
          AND open_time < %s;
    """
    params = (symbol, interval, limit_date)

    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            row_count = cur.rowcount

    logger.info(f'{row_count} lignes supprimées de la table "klines"')
    return row_count


def upsert_mapping(mapper: dict) -> int :
    if not mapper :
        return 0

    query = f"""
            INSERT INTO crypto_mapping 
            (coin_id, binance_symbol) VALUES %s
            ON CONFLICT (coin_id) 
            DO UPDATE SET binance_symbol = EXCLUDED.binance_symbol, updated_at = now();
            """
    
    params = list(mapper.items())

    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            inserted = execute_values(cur, query, params)
            num = cur.rowcount

    logger.info(f"{num} lignes insérées")

    return num

def get_all_symbols() -> list :
    """
    Récupère la liste des symbols binance dans la table crypto_mapping
    """

    query = """
            SELECT  binance_symbol
            FROM crypto_mapping 
            ORDER BY binance_symbol;
            """


    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur :

            cur.execute(query)
            # inserted = execute_values(cur, query,)
            # num = cur.rowcount
            res = cur.fetchall()
            num = cur.rowcount

    logger.info(f"{num} symboles trouvés")

    ma_liste = [x[0] for x in res]


    return ma_liste