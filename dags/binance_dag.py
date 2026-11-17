from datetime import datetime, timedelta
from airflow.sdk import dag, task


@dag(
    dag_id="binance_klines_daily",
    schedule="0 2 * * *",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=3,
    default_args={"retries": 3, "retry_delay": timedelta(minutes=2)}
    )

def binance_pipe():
    @task
    def list_pairs() -> list:
        from load.coingecko_load import get_unique_crypto
        from collector.binance_symbol import get_binance_symbols
        from collector.map_to_binance import get_mapper
        from load.mapping_load import upsert_mapping, get_all_symbols

        # Récupérer les symbols et créer un mapper
        gencko_crypto = get_unique_crypto() # -> list
        binance_symbols = get_binance_symbols() # -> set
        mapper = get_mapper(gencko_crypto, binance_symbols) # -> dict

        # Insérer le mapper dans la bdd
        upsert_mapping(mapper)

        # Lire les symbols de la bdd
        symbols = get_all_symbols()

        if len(symbols) == 0 :
            raise ValueError('Liste de symboles vide')


        return symbols
        


    @task(max_active_tis_per_dag = 1)
    def ingest(symbol:str) :

        from load.binance_load import ingest_pair
        from load.klines_pg import load_recent_klines_pipe

        pair = ingest_pair(symbol, interval="1m", backfill_days=7) 
        recent_klines = load_recent_klines_pipe(symbol, interval="1m", days=7) 

        pair.update(recent_klines)

        return pair


    mapper = list_pairs()
    ingest.expand(symbol=mapper)

binance_pipe()