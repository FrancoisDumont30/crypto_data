import logging
logger = logging.getLogger(__name__)

def get_mapper(gecko_symbols, binance_symbols):
    """
    Recherche des correspondances entre les appelation des monnaies gecko et biances 
    """
    mapper = {}  # gecko_id : binance_symbol

    for coin_id, coin_symbol in gecko_symbols :
        crypto = coin_symbol.upper()+'USDT'
        if crypto in binance_symbols :
            mapper[coin_id] = crypto
        else :
            logging.warning(f"gecko coin_id '{coin_id}' with {crypto} symbol wasn't find in binance.")

    return mapper
