"""Cross-platform symbol matching and reconciliation module."""

import logging
logger = logging.getLogger(__name__)

def build_crypto_mapping(gecko_symbols: list[tuple[str, str]], binance_symbols: set[str]) -> dict[str, str]:
    """Find semantic matches between CoinGecko and Binance identifiers.

    Args:
        gecko_symbols: List of assets retrieved from CoinGecko (tuples of coin_id, coin_symbol).
        binance_symbols: Set of valid symbols referenced on Binance.

    Returns:
        A mapping dictionary linking coin IDs to Binance exchange symbols.
    """
    mapper = {}  # gecko_id: binance_symbol

    for coin_id, coin_symbol in gecko_symbols:
        crypto = coin_symbol.upper() + "USDT"
        if crypto in binance_symbols:
            mapper[coin_id] = crypto
        else:
            logger.warning("Gecko coin_id '%s' with symbol '%s' was not found on Binance.", coin_id, crypto)

    return mapper