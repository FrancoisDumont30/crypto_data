"""Cross-platform symbol matching and reconciliation module."""

import logging
logger = logging.getLogger(__name__)
from collections import Counter


def build_crypto_mapping(gecko_symbols: list[tuple[str, str]], binance_symbols: set[str]) -> dict[str, str]:
    """Sort the unique CoinGecko symbols and find semantic matches between CoinGecko and Binance identifiers.

    Args:
        gecko_symbols: List of assets retrieved from CoinGecko (tuples of coin_id, coin_symbol).
        binance_symbols: Set of valid symbols referenced on Binance.

    Returns:
        A mapping dictionary linking coin IDs to Binance exchange symbols.
    """

    if len(gecko_symbols)== 0 :
        logger.warning('CoinGecko symbols list is empty.')
        return {}

    if len(binance_symbols) == 0 :
        logger.warning('Binance symbols list is empty.')
        return {}

    # 1. Candidate Binance symbol for each coin (case-insensitive)
    candidates = [
        (coin_id, coin_symbol.upper() + "USDT")
        for coin_id, coin_symbol in gecko_symbols
    ]

    # 2. Detect ambiguous targets in a single pass
    counts = Counter(target for _, target in candidates)
    duplicated = {target for target, n in counts.items() if n > 1}

    if duplicated:
        logger.warning(
            "Coins sharing the same Binance symbol (all excluded): %s",
            [pair for pair in candidates if pair[1] in duplicated],
        )

    # 3. Build the mapping
    mapper = {}
    for coin_id, target in candidates:
        if target in duplicated:
            continue
        if target in binance_symbols:
            mapper[coin_id] = target
        else:
            logger.warning(
                "Gecko coin_id '%s' with Binance symbol '%s' was not found on Binance.",
                coin_id, target,
            )

    return mapper 
    