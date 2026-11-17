import logging

import pandas as pd
from datetime import datetime, timezone, timedelta

from load.parquet_io import get_last_open_time, write_klines_to_parquet, calculate_limit_date, read_klines_from_parquet, list_parquet_files
from load.postgres_db import insert_klines_data, purge_old_klines
from extract.binance import get_klines
from transform.models import transform

logger = logging.getLogger(__name__)

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


def ingest_binance_pair(symbol, interval="1m", backfill_days=30) :
    """ 
    Enregistre les 30 derniers jours de donnée sur une bougie donnée
    """
    last_open_time = get_last_open_time(symbol, interval)

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    if last_open_time :
        start = last_open_time + timedelta(minutes=1)
    else :
        start = now - timedelta(days=backfill_days)


    info = {"symbol":f'{symbol}',
            "interval":f'{interval}',
            "start":f'{start}',
            "end":f'{now}',
            "rows": 0}

    if start >= now:
        logging.info("%s : rien à récupérer", symbol)
        return info

    else :
        resp = get_klines(symbol, interval, start, now)
        # transform
        df = transform(resp, symbol, interval)
        # load
        write_klines_to_parquet(df)

        info["rows"] = len(df)
        logger.info(info)
        return info


def ingest_recent_klines(symbol :str, days : int = 7, interval : str ="1m", ) -> dict :
    """
    Lit dans le Parquet les bougies des derniers jours pour ce symbole
    """

    limit_date = calculate_limit_date(days=days)

    # 1. Lecture des fichiers Parquet
    parquet_files = list_parquet_files(symbol, limit_date, interval)

    # Insérer les données des fichiers parquet dans un df
    if parquet_files :
        df = read_klines_from_parquet(parquet_files)
    else:
        df = pd.DataFrame(columns=OUTPUT_COLUMNS)

    # filtrage sur open_time (UTC)
    # Conversion de limit_date en Timestamp UTC
    limit_timestamp = pd.Timestamp(limit_date, tz="UTC")
    df = df.loc[df["open_time"] >= limit_timestamp]
    row_left = len(df)
    logger.info(f"{row_left} lignes conservées après filtre.")

    # 2. Insertion en lot avec gestion des doublons
    inserted_rows = insert_klines_data(df)
    
    # 3. Purge des données plus anciennes que la limite
    purged_rows = purge_old_klines(symbol, limit_timestamp)
    logger.info(f"{purged_rows} ligne(s) purgée(s).")

    # 4. Renvoi du résumé sous forme de dictionnaire
    return {
        "symbol": symbol,
        "date_limite" :limit_date.isoformat(),
        "lignes_après_filtre" : row_left,
        "db_lignes_inserées": inserted_rows,
        "db_lignes_purgées": purged_rows
    }