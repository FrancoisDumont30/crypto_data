import logging
logger = logging.getLogger(__name__)

def get_mapper(gecko_symbols, binance_symbols):
    mapper = {}  # gecko_id : binance_symbol

    for coin_id, coin_symbol in gecko_symbols :
        crypto = coin_symbol.upper()+'USDT'
        if crypto in binance_symbols :
            mapper[coin_id] = crypto
        else :
            logging.warning(f"gecko coin_id '{coin_id}' with {crypto} symbol wasn't find in binance.")

    return mapper



# test in terminal :
# docker compose exec airflow-worker python -c "
# from load.coingecko_load import get_unique_crypto
# from collector.binance_symbol import get_binance_symbols
# from collector.map_to_binance import get_mapper
# gecko_symbols = get_unique_crypto()
# binance_symbols = get_binance_symbols()
# r = get_mapper(gecko_symbols, binance_symbols)
# print(len(gecko_symbols), len(r))
# print(r)
# print(len(r) == len(set(r.values())))
# "


# output :
# WARNING:root:gecko coin_id 'canton-network' with CCUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'crypto-com-chain' with CROUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'dai' with DAIUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'falcon-finance' with USDFUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'figure-heloc' with FIGR_HELOCUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'global-dollar' with USDGUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'hashnote-usyc' with USYCUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'leo-token' with LEOUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'memecore' with MUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'monero' with XMRUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'okb' with OKBUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'ondo-us-dollar-yield' with USDYUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'paypal-usd' with PYUSDUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'rain' with RAINUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'spiko-amundi-overnight-swap-fund-eur' with EURSAFOUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'tether' with USDTUSDT symbol wasn't find in binance.
# WARNING:root:gecko coin_id 'whitebit' with WBTUSDT symbol wasn't find in binance.
# 51 34
# {'aave': 'AAVEUSDT', 'avalanche-2': 'AVAXUSDT', 'binancecoin': 'BNBUSDT', 'bitcoin': 'BTCUSDT', 'bitcoin-cash': 'BCHUSDT', 'bittensor': 'TAOUSDT', 'cardano': 'ADAUSDT', 'chainlink': 'LINKUSDT', 'dogecoin': 'DOGEUSDT', 'ethena': 'ENAUSDT', 'ethena-usde': 'USDEUSDT', 'ethereum': 'ETHUSDT', 'hedera-hashgraph': 'HBARUSDT', 'hyperliquid': 'HYPEUSDT', 'litecoin': 'LTCUSDT', 'near': 'NEARUSDT', 'ondo-finance': 'ONDOUSDT', 'pax-gold': 'PAXGUSDT', 'pepe': 'PEPEUSDT', 'quant-network': 'QNTUSDT', 'ripple': 'XRPUSDT', 'ripple-usd': 'RLUSDUSDT', 'shiba-inu': 'SHIBUSDT', 'solana': 'SOLUSDT', 'stellar': 'XLMUSDT', 'sui': 'SUIUSDT', 'tether-gold': 'XAUTUSDT', 'the-open-network': 'GRAMUSDT', 'tron': 'TRXUSDT', 'uniswap': 'UNIUSDT', 'usd1-wlfi': 'USD1USDT', 'usd-coin': 'USDCUSDT', 'usds': 'USDSUSDT', 'zcash': 'ZECUSDT'}
# True
