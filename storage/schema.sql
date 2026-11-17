CREATE TABLE IF NOT EXISTS market_snapshots (
    coin_id TEXT NOT NULL,
    coin_symbol TEXT, 
    coin_name TEXT,
    current_price NUMERIC,
    market_cap NUMERIC,
    total_volume NUMERIC, 
    last_updated TIMESTAMPTZ,
    collected_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (coin_id, collected_at)
    );

CREATE TABLE IF NOT EXISTS klines (
    symbol TEXT NOT NULL,
    "interval" TEXT, 
    open_time TIMESTAMPTZ,
    "open" NUMERIC,
    high NUMERIC,
    low NUMERIC, 
    "close" NUMERIC,
    volume NUMERIC,
    close_time TIMESTAMPTZ,
    quote_volume NUMERIC,
    trades INTEGER,
    taker_buy_base_volume NUMERIC,
    taker_buy_quote_volume NUMERIC,
    PRIMARY KEY (symbol, interval, open_time)
    );


CREATE TABLE IF NOT EXISTS crypto_mapping (
    coin_id TEXT PRIMARY KEY,
    binance_symbol TEXT NOT NULL, 
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    
    );