from monitoring.alerts import notify_failure
from datetime import datetime
from airflow.sdk import dag, task

@dag(
    dag_id="Raise_alert",
    schedule=None,
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0, 
                  "on_failure_callback": notify_failure},
    )

def raise_alert() :
    @task
    def alert():
        raise ValueError("test alerte réel")

    alert()

    
raise_alert()