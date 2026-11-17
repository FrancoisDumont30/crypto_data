import psycopg2
from psycopg2.extras import execute_values
import os
from contextlib import closing
import logging


logger = logging.getLogger(__name__)


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


# docker compose exec airflow-worker python -c "
# import logging
# logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
# from load.mapping_load import get_all_symbols
# symbols = get_all_symbols()
# print(type(symbols))
# print(symbols)
# "