from transform.mappers import build_crypto_mapping
import logging
# name
# test_<fonction>_<situation>_<résultat>


def test_maps_every_symbol_present_on_binance():
    gecko = [("bitcoin", "btc"), ("aave", "aave")]
    binance = {"BTCUSDT", "AAVEUSDT", "ETHUSDT"}

    result = build_crypto_mapping(gecko, binance)

    assert result == {"bitcoin": "BTCUSDT", "aave": "AAVEUSDT"}


def test_ignores_coins_without_binance_pair():
    gecko = [("bitcoin", "btc"), ("unknown-coin", "xyz")]
    binance = {"BTCUSDT"}

    result = build_crypto_mapping(gecko, binance)

    assert result == {"bitcoin": "BTCUSDT"}
    assert "unknown-coin" not in result


def test_returns_empty_dict_when_nothing_matches():
    gecko = [("bitcoin", "btc")]
    binance = {"123456", "TARATATA"}

    assert build_crypto_mapping(gecko, binance) == {}


def test_returns_empty_dict_on_empty_inputs():
    assert build_crypto_mapping([], set()) == {}
    assert build_crypto_mapping([("bitcoin", "btc")], set()) == {}


def test_lower_binance_symbols():
    gecko = [("bitcoin", "btc"), ("aave", "aave")]
    binance = {  "btcusdt", "aaveusdt", "ethusdt"}

    result = build_crypto_mapping(gecko, binance)

    assert result == {}


def test_mapping_excludes_coins_sharing_the_same_symbol() :
    gecko = [("bitcoin", "btc"), ("bythechance", "btc")]
    binance = {"BTCUSDT", "AAVEUSDT", "ETHUSDT"}

    result = build_crypto_mapping(gecko, binance)

    assert result == {}


def test_mapping_logs_warning_for_unmatched_coin(caplog):
    with caplog.at_level(logging.WARNING):
        build_crypto_mapping([("x", "xyz")], {"BTCUSDT"})

    assert "not found on Binance" in caplog.text
