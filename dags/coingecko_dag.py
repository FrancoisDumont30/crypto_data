from datetime import datetime, timedelta
from airflow.sdk import dag, task
from monitoring.alerts import notify_failure


@dag(
    dag_id="crypto_collect_minute",
    schedule="* * * * *",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2, 
        "retry_delay": timedelta(seconds=15),
        "on_failure_callback": notify_failure
    },
)
def coingecko_pipe():
    """DAG to collect, transform, and ingest minute-level CoinGecko market data."""

    @task
    def collect() -> list:
        """Fetch raw market data from the CoinGecko API."""
        from extract.coingecko import fetch_coingecko_data
        
        # Retrieve raw data payload
        raws = fetch_coingecko_data()
        return raws

    @task
    def transform(raws: list) -> list:
        """Process and clean raw CoinGecko data into structured format."""
        from transform.models import process_coingecko_data
        
        # Transform raw records
        return process_coingecko_data(raws)

    @task
    def ingest(datalist: list):
        """Load the processed market data into the PostgreSQL database."""
        from load.postgres_db import insert_coingecko_data
        
        # Insert records into DB
        return insert_coingecko_data(datalist)

    # Pipeline task dependencies
    raw_data = collect()
    datalist = transform(raw_data)
    ingest(datalist)

coingecko_pipe()