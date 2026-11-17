import logging
from pathlib import Path
import os
from contextlib import closing
import pandas as pd
from datetime import datetime, timezone, timedelta, date
import psycopg2
from psycopg2.extras import execute_values

# Dossier de base DANS le conteneur Airflow (volume ./data monté sur /opt/airflow/data)
DEFAULT_BASE_DIR = Path(os.getenv("DATA_DIR", "/opt/airflow/data")) / "parquet"

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


logger = logging.getLogger(__name__)


def find_limit_date(days : int = 7) -> date :
    """
    Calcul la date limite (borne inférieure) """
    today_utc = datetime.now(timezone.utc).date()

    return today_utc - timedelta(days=days)


def find_parquet_file(symbol :str, limit_date : date, interval : str ="1m") -> list :
    """
    Recherche tous les fichiers parquets entre maintenant et 'maintenant - days'
    Renvoie une liste de file_path.
    """
    
    parquet_files = []

    base_dir = Path(DEFAULT_BASE_DIR)
    folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"

    # # today = datetime.today().replace(tzinfo=timezone.utc)
    first_month = limit_date.replace(day=1)


    for file_path in folder.glob("*.parquet"):
            date_str = file_path.stem  # Format "YYYY-MM"

            try:
                file_date = datetime.strptime(date_str, "%Y-%m").replace(tzinfo=timezone.utc).replace(day=1)
                   
                # Conserve le fichier si son mois >= first_month
                if file_date.date()  >= first_month:
                    parquet_files.append(file_path)

            except ValueError:
                continue

    logger.info(f'{len(parquet_files)} parquet files found')
    return parquet_files


def get_data(parquet_files) -> pd.DataFrame :
    """
    Pour chaque file_path de la liste, ouvre le dataframe et trie les lignes pour que toutes les dates soient >= limit_date
    """
    df_list = []

    for file_path in parquet_files:
        df_temp = pd.read_parquet(file_path, columns=OUTPUT_COLUMNS)
        df_list.append(df_temp)

    if df_list:
        df = pd.concat(df_list, ignore_index=True)

    else:
        df = pd.DataFrame(columns=OUTPUT_COLUMNS)

    logger.info(f'{len(df)} rows read')

    return df



def insert_klines_data(df) -> int:
    """
    Insère les klines dans la table klines.
    Renvoie le nombre de lignes réellement insérées.
    """
    if df.empty:
        return 0

    # tuples = [tuple(x) for x in df.to_numpy()]
    tuples = list(df[OUTPUT_COLUMNS].itertuples(index=False, name=None))

    columns_str = ", ".join(OUTPUT_COLUMNS)

    query = f"""
            INSERT INTO klines ({columns_str}) 
            VALUES %s
            ON CONFLICT (symbol, interval, open_time) DO NOTHING
            RETURNING 1;
            """
    
    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            inserted = execute_values(cur, query, tuples, page_size=1000, fetch=True)
            num = len(inserted)

    logger.info(f"{num} lignes insérées")
    return num


def purge_old_klines(symbol: str, limit_date, interval: str = "1m") -> int:
    """
    Supprime les lignes de ce symbole dont open_time est antérieur à limit_date.
    Renvoie le nombre de lignes supprimées.
    """
    query = """
        DELETE FROM klines
        WHERE symbol = %s
          AND interval = %s
          AND open_time < %s;
    """
    params = (symbol, interval, limit_date)

    crypto_db_url = os.environ["CRYPTO_DB_URL"]

    with closing(psycopg2.connect(crypto_db_url)) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
            row_count = cur.rowcount

    logger.info(f'{row_count} lignes supprimées de la table "klines"')
    return row_count


def load_recent_klines_pipe(symbol :str, days : int = 7, interval : str ="1m", ) -> dict :
    """
    Lit dans le Parquet les bougies des derniers jours pour ce symbole
    """

    limit_date = find_limit_date(days=days)

    # 1. Lecture des fichiers Parquet
    parquet_files = find_parquet_file(symbol, limit_date, interval)

    # Insérer les données des fichiers parquet dans un df
    if parquet_files :
        df = get_data(parquet_files)
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
