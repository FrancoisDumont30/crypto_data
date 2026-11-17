import pandas as pd
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

RAW_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]

FLOAT_COLUMNS = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ]

OUTPUT_COLUMNS = [
    "symbol",
    "interval",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]




 
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


def transform(raw :list[list], symbol:str, interval:str) :

    if not raw:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
      
    df = pd.DataFrame(raw, columns = RAW_COLUMNS).drop(columns=['ignore'])

    # types
    df['symbol'] = symbol
    df['interval'] = interval
    df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].astype(float)
    df['trades'] = df['trades'].astype('int64')

    for col in ("open_time", "close_time"):
            df[col] = pd.to_datetime(df[col], unit="ms", utc=True)

    df = (
        df[OUTPUT_COLUMNS]
        .drop_duplicates(subset=["symbol", "interval", "open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )

    return df

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
