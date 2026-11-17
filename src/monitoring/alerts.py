import logging
import os
import requests

logger = logging.getLogger(__name__)

def notify_failure(context):
    """Callback Airflow exécuté lors de l'échec définitif d'une tâche."""
    # Récupération des informations du contexte Airflow
    dag_run = context.get("dag_run")
    dag_id = dag_run.dag_id if dag_run else "inconnu"
    
    ti = context.get("ti") or context.get("task_instance")
    task_id = ti.task_id if ti else "inconnu"
    map_index = getattr(ti, "map_index", -1) if ti else -1
    
    exception = context.get("exception", "Erreur inconnue")
    
    # 1. Composition du message (avec gestion des tâches mappées)
    task_desc = f"{task_id} (index : {map_index})" if map_index >= 0 else task_id
    message = f"[Airflow] Échec du DAG '{dag_id}' sur la tâche '{task_desc}'. Erreur : {exception}"
    
    # 2. Écriture dans les logs
    logger.error(message)
    
    # 3. Envoi du webhook si la variable d'environnement est définie
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if webhook_url:
        try:
            # Adaptation du format selon la plateforme (Discord vs Slack)
            if "discord.com" in webhook_url:
                payload = {"content": message}
            else:
                payload = {"text": message}
            
            response = requests.post(webhook_url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Échec de l'envoi du webhook d'alerte : {e}")