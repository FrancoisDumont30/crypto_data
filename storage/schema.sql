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