"""Utilitaires de stockage : écriture des bougies Binance en Parquet."""
import logging
from pathlib import Path
import os
import pandas as pd

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


# if __name__ == "__main__":
#     # Test sans réseau, dans un dossier temporaire (rien n'est écrit dans data/)
#     import tempfile

#     from transformations.binance_transform import transform

#     logging.basicConfig(level=logging.INFO)

#     raw = [
#         [1794471480000 + i * 60000, "1.0", "2.0", "0.5", "1.5", "10.0",
#          1794471539999 + i * 60000, "15.0", 5, "4.0", "6.0", "0"]
#         for i in range(3)
#     ]
#     df = transform(raw, "BTCUSDT", "1m")

#     with tempfile.TemporaryDirectory() as tmp:
#         files = write_klines_parquet(df, tmp)
#         print("Fichiers :", [str(f) for f in files])

#         # Deuxième écriture des mêmes données : pas de doublons attendus
#         write_klines_parquet(df, tmp)

#         relu = pd.read_parquet(files[0])
#         print(f"Lignes après 2 écritures : {len(relu)} (attendu : 3)")
#         print(relu.dtypes)