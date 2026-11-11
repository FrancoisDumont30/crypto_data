from datetime import datetime
from airflow.sdk import dag, task

@dag(
    dag_id="test_simple_dag",
    schedule=None,  # Déclenchement uniquement manuel depuis l'UI
    start_date=datetime(2026, 1, 1),
    catchup=False,
)
def test_pipeline():
    @task
    def say_hello():
        print("Hello depuis Airflow 3 !")
        return "OK"

    say_hello()

test_pipeline()