"""Module de correspondance et réconciliation des symboles inter-plateformes."""


import logging
logger = logging.getLogger(__name__)

def build_crypto_mapping(gecko_symbols, binance_symbols):
    """Recherche des correspondances sémantiques entre les identifiants CoinGecko et Binance.

    Args:
        gecko_symbols: Liste des actifs récupérés depuis CoinGecko.
        binance_symbols: Ensemble des symboles valides référencés sur Binance.

    Returns:
        Un dictionnaire de correspondance mapant les identifiants entre les deux sources.
    """
    mapper = {}  # gecko_id : binance_symbol

    for coin_id, coin_symbol in gecko_symbols :
        crypto = coin_symbol.upper()+'USDT'
        if crypto in binance_symbols :
            mapper[coin_id] = crypto
        else :
            logging.warning(f"gecko coin_id '{coin_id}' with {crypto} symbol wasn't find in binance.")

    return mapper
