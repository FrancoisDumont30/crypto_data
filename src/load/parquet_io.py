"""Module de gestion des Entrées/Sorties (I/O) pour les fichiers Parquet locaux."""

import logging
from pathlib import Path
import os
import pandas as pd
from datetime import datetime, timezone, timedelta, date

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


# Dossier de base DANS le conteneur Airflow (volume ./data monté sur /opt/airflow/data)
DEFAULT_BASE_DIR = Path(os.getenv("DATA_DIR", "/opt/airflow/data")) / "parquet"

# Clé unique d'une bougie
KEY_COLUMNS = ["symbol", "interval", "open_time"]

def write_klines_to_parquet(df: pd.DataFrame, base_dir: Path | str = DEFAULT_BASE_DIR) -> list[Path]:
    """Écrit un DataFrame de bougies sous forme de fichiers Parquet partitionnés.

        Arborescence cible :
        « <base_dir>/klines/interval=1m/symbol=BTCUSDT/2026-11.parquet »

        Le processus est idempotent : si le fichier du mois existe déjà, les nouvelles
        lignes sont fusionnées avec l'existant, les doublons (basés sur le symbole,
        l'intervalle et l'`open_time`) sont supprimés et la dernière version est conservée.

        Args:
            df: DataFrame pandas contenant les klines à persister.
            base_dir: Répertoire racine de stockage.

        Returns:
            La liste des chemins de fichiers (`Path`) écrits ou mis à jour.
        """
    
    if df.empty:
        logger.info("DataFrame vide : rien à écrire")
        return []

    base_dir = Path(base_dir)
    df = df.assign(month=df["open_time"].dt.strftime("%Y-%m"))

    written: list[Path] = []
    for (symbol, interval, month), part in df.groupby(["symbol", "interval", "month"]):
        part = part.drop(columns="month")

        folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{month}.parquet"

        if path.exists():
            part = pd.concat([pd.read_parquet(path), part], ignore_index=True)
            part = part.drop_duplicates(subset=KEY_COLUMNS, keep="last")

        part = part.sort_values("open_time").reset_index(drop=True)

        # Écriture dans un fichier temporaire puis remplacement :
        # un plantage en cours d'écriture ne corrompt pas le fichier existant
        tmp_path = path.with_suffix(".parquet.tmp")
        part.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)

        logger.info("%s : %s lignes écrites", path, len(part))
        written.append(path)

    return written


def get_last_open_time(symbol, interval, base_dir: Path | str = DEFAULT_BASE_DIR) :
    """Récupère le dernier horodatage d'ouverture (`open_time`) enregistré pour un symbole.

    Args:
        symbol: Paire de trading (ex: "BTCUSDT").
        interval: Intervalle des bougies.
        base_dir: Répertoire racine de stockage Parquet.

    Returns:
        Le timestamp en millisecondes de la dernière bougie, ou None si aucun fichier n'existe.
    """

    base_dir = Path(base_dir)
    folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"

    files = sorted(folder.glob("*.parquet"))  
    if not files:                            
        return None

    col = pd.read_parquet(files[-1], columns=["open_time"])
    return col["open_time"].max()


def calculate_limit_date(days : int = 7) -> date :
    """Calcule la date limite (borne inférieure) pour le filtrage temporel.

    Args:
        days: Nombre de jours en arrière à partir d'aujourd'hui.

    Returns:
        Un objet `date` représentant la borne inférieure calculée.
    """
    today_utc = datetime.now(timezone.utc).date()

    return today_utc - timedelta(days=days)


def list_parquet_files(symbol :str, limit_date : date, interval : str ="1m") -> list :
    """Recherche et liste les fichiers Parquet valides couvrant la période récente.

    Args:
        symbol: Symbole de la paire ciblée.
        limit_date: Date limite inférieure de recherche.
        interval: Intervalle des klines.

    Returns:
        Une liste de chemins (`Path`) pointant vers les fichiers correspondants.
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


def read_klines_from_parquet(parquet_files) -> pd.DataFrame :
    """Lit une liste de fichiers Parquet et filtre les lignes selon la date limite.

        Args:
            parquet_files: Liste des chemins de fichiers Parquet à charger.

        Returns:
            Un DataFrame pandas consolidé et trié.
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