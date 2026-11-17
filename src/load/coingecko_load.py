import psycopg2
from psycopg2.extras import execute_values
import os
from contextlib import closing

import logging
logger = logging.getLogger(__name__)


from dotenv import load_dotenv

load_dotenv() 

CRYPTO_DB_URL = os.getenv('CRYPTO_DB_URL')

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