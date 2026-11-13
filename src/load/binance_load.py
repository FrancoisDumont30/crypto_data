"""Utilitaires de stockage : écriture des bougies Binance en Parquet."""
import logging
from pathlib import Path
import os
import pandas as pd
from datetime import datetime, timezone, timedelta

from collector.binance import get_klines
from transformations.binance_transform import transform

# Dossier de base DANS le conteneur Airflow (volume ./data monté sur /opt/airflow/data)
DEFAULT_BASE_DIR = Path(os.getenv("DATA_DIR", "/opt/airflow/data")) / "parquet"

# Clé unique d'une bougie
KEY_COLUMNS = ["symbol", "interval", "open_time"]

logger = logging.getLogger(__name__)


def parquet_storage(df: pd.DataFrame, base_dir: Path | str = DEFAULT_BASE_DIR) -> list[Path]:
    """Écrit un DataFrame de bougies en fichiers Parquet, un par (symbole, intervalle, mois).

    Arborescence :
        <base_dir>/klines/interval=1m/symbol=BTCUSDT/2026-11.parquet

    Relançable sans risque : si le fichier du mois existe déjà, les nouvelles
    lignes sont fusionnées avec l'existant, les doublons (même symbol, interval,
    open_time) sont supprimés et la dernière version de la ligne est conservée.

    Retourne la liste des fichiers écrits.
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
    """
    Renvoie le dernier 'open time' d'une bougie.
    """

    base_dir = Path(base_dir)
    folder = base_dir / "klines" / f"interval={interval}" / f"symbol={symbol}"

    files = sorted(folder.glob("*.parquet"))  
    if not files:                            
        return None

    col = pd.read_parquet(files[-1], columns=["open_time"])
    return col["open_time"].max()


def ingest_pair(symbol, interval="1m", backfill_days=30) :
    """ Enregistre les 30 derniers jours de donnée sur une bougie donnée
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
        parquet_storage(df)

        info["rows"] = len(df)
        logging.info(info)
        return info
