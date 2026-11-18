import logging
import os
import requests

logger = logging.getLogger(__name__)

def notify_failure(context: dict) -> None:
    """Airflow callback executed upon final failure of a task."""
    # Retrieve Airflow context details
    dag_run = context.get("dag_run")
    dag_id = dag_run.dag_id if dag_run else "unknown"
    
    ti = context.get("ti") or context.get("task_instance")
    task_id = ti.task_id if ti else "unknown"
    map_index = getattr(ti, "map_index", -1) if ti else -1
    
    exception = context.get("exception", "Unknown error")
    
    # 1. Compose the message (with support for mapped tasks)
    task_desc = f"{task_id} (index: {map_index})" if map_index >= 0 else task_id
    message = f"[Airflow] DAG '{dag_id}' task '{task_desc}' failed. Error: {exception}"
    
    # 2. Log the error
    logger.error(message)
    
    # 3. Send webhook if the environment variable is configured
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        try:
            # Adapt payload format based on the platform (Discord vs Slack)
            if "discord.com" in webhook_url:
                payload = {"content": message}
            else:
                payload = {"text": message}
            
            response = requests.post(webhook_url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to send alert webhook: %s", e)