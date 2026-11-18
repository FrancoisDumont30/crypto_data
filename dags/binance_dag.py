from datetime import datetime, timedelta
from airflow.sdk import dag, task
from monitoring.alerts import notify_failure

@dag(
    dag_id="binance_klines_daily",
    schedule="0 2 * * *",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=3,
    default_args={
        "retries": 3, 
        "retry_delay": timedelta(minutes=2),
        "on_failure_callback": notify_failure
    }
)
def binance_pipe():
    """DAG to orchestrate daily Binance klines ingestion and symbol mapping updates."""
    
    @task
    def list_pairs() -> list:
        """Fetch unique cryptos, build and update the symbol mapping, and return active symbols."""
        from load.postgres_db import get_unique_crypto, upsert_mapping, get_all_symbols
        from extract.binance import fetch_binance_symbols
        from transform.mappers import build_crypto_mapping

        # Fetch unique cryptos and Binance symbols to build the mapping
        gencko_crypto = get_unique_crypto()  # -> list
        binance_symbols = fetch_binance_symbols()  # -> set
        mapper = build_crypto_mapping(gencko_crypto, binance_symbols)  # -> dict

        # Upsert the mapping into the database
        upsert_mapping(mapper)

        # Read the symbols from the database
        symbols = get_all_symbols()

        if len(symbols) == 0:
            raise ValueError("Symbol list is empty")

        return symbols
        
    @task(max_active_tis_per_dag=1)
    def ingest(symbol: str):
        """Ingest historical and recent klines data for a specific symbol."""
        from pipelines.ingestion import ingest_binance_pair, ingest_recent_klines
        
        pair = ingest_binance_pair(symbol, interval="1m", backfill_days=7) 
        recent_klines = ingest_recent_klines(symbol, interval="1m", days=7) 

        pair.update(recent_klines)

        return pair

    mapper = list_pairs()
    ingest.expand(symbol=mapper)

binance_pipe()