from datetime import datetime, timedelta
from airflow.sdk import dag, task
from monitoring.alerts import notify_failure

@dag(
    dag_id="binance_klines_daily",
    schedule="0 2 * * *",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=3,
    default_args={"retries": 3, 
                  "retry_delay": timedelta(minutes=2),
                  "on_failure_callback": notify_failure})

def binance_pipe():
    @task
    def list_pairs() -> list:

        from load.postgres_db import get_unique_crypto, upsert_mapping, get_all_symbols
        from extract.binance import fetch_binance_symbols
        from transform.mappers import build_crypto_mapping

        # Récupérer les symbols et créer un mapper
        gencko_crypto = get_unique_crypto() # -> list
        binance_symbols = fetch_binance_symbols() # -> set
        mapper = build_crypto_mapping(gencko_crypto, binance_symbols) # -> dict

        # Insérer le mapper dans la bdd
        upsert_mapping(mapper)

        # Lire les symbols de la bdd
        symbols = get_all_symbols()

        if len(symbols) == 0 :
            raise ValueError('Liste de symboles vide')


        return symbols
        


    @task(max_active_tis_per_dag = 1)
    def ingest(symbol:str) :

        from pipelines.ingestion import ingest_binance_pair, ingest_recent_klines
        

        pair = ingest_binance_pair(symbol, interval="1m", backfill_days=7) 
        recent_klines = ingest_recent_klines(symbol, interval="1m", days=7) 

        pair.update(recent_klines)

        return pair


    mapper = list_pairs()
    ingest.expand(symbol=mapper)

binance_pipe()