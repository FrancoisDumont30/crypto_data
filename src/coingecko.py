import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import requests

import psycopg2
from psycopg2.extras import execute_values

from dotenv import load_dotenv
load_dotenv() 

CRYPTO_DB_URL = os.getenv('CRYPTO_DB_URL')

URL = "https://api.coingecko.com/api/v3/coins/markets"


def safe_string(val, max_length=None):
    if val is None:
        return None
    text = str(val).strip()
    if max_length and len(text) > max_length:
        return text[:max_length]
    return text

def safe_datetime(val):
    """Convertit une string ISO en datetime UTC, ou retourne None si vide."""
    if not val:
        return None
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    return val

def safe_numeric(val):
    """Convertit proprement en Decimal pour le type NUMERIC de PostgreSQL."""
    if val is None:
        return None
    try:
        # Passer par str() évite les imprécisions des floats natifs Python
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return None

# Dictionnaire de configuration des types par colonne
COLUMN_MAPPINGS = {
    "coin_id": safe_string,
    "coin_symbol": safe_string,
    "coin_name": safe_string,
    "current_price" : safe_numeric,
    "market_cap" : safe_numeric,
    "total_volume" : safe_numeric,
    "last_updated" : safe_datetime,
    "collected_at" : safe_datetime,
        }

def fetch_coingecko_data():
    params = {"vs_currency": "usd", "per_page": 50, "page": 1}
    r = requests.get(URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def process_coingecko_data(raw_data):
    FIELDS = ["id", "symbol", "name", "current_price", "market_cap", "total_volume", "last_updated"]
    collected_at = datetime.now(timezone.utc).replace(microsecond=0)

    processed_list = []
    for d in raw_data:
        filtered_dict = {}
        for k in FIELDS:
            if k in d:
                val = d[k]
                if k in COLUMN_MAPPINGS:
                    filtered_dict[k] = COLUMN_MAPPINGS[k](val)
                else:
                    filtered_dict[k] = val
        
        # Ajout du timestamp de collecte POUR CHAQUE DICTIONNAIRE dans la boucle
        filtered_dict["collected_at"] = collected_at
        processed_list.append(filtered_dict)

    return processed_list  # <-- Doit être en dehors de la boucle for

def insert_coingecko_data(data_list):
    with psycopg2.connect(CRYPTO_DB_URL) as conn:
        with conn.cursor() as cur:
            execute_values(
                cur, 
                """
                INSERT INTO market_snapshots
                    (coin_id, coin_symbol, coin_name, current_price, market_cap, total_volume,
                    last_updated, collected_at)
                VALUES %s
                ON CONFLICT (coin_id, collected_at) DO NOTHING
                """, 
                data_list,
                # On mappe chaque clé du dictionnaire vers la colonne correspondante
                template="(%(id)s, %(symbol)s, %(name)s, %(current_price)s, %(market_cap)s, %(total_volume)s, %(last_updated)s, %(collected_at)s)"
            )


# ## test ###
# raw_data = fetch_coingecko_data() 
# t_data = process_coingecko_data(raw_data)

# # for k, v in t_data[0].items() :
# #   print(k, v, type(v))


# insert_coingecko_data(t_data)