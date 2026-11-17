from datetime import datetime, timedelta
from airflow.sdk import dag, task
from monitoring.alerts import notify_failure


@dag(
    dag_id="crypto_collect_minute",
    schedule="* * * * *",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, 
                  "retry_delay": timedelta(seconds=15),
                  "on_failure_callback": notify_failure},
)

def coingecko_pipe():
    @task
    def collect():
        from collector.coingecko import fetch_coingecko_data
        raws = fetch_coingecko_data()
        return raws

    @task
    def transform(raws):
        from transformations.coingecko_transform import process_coingecko_data
        return process_coingecko_data(raws)

    @task
    def ingest(datalist) :
        from load.coingecko_load import insert_coingecko_data
        return insert_coingecko_data(datalist)

    raw_data = collect()
    datalist = transform(raw_data)
    ingest(datalist)

coingecko_pipe()