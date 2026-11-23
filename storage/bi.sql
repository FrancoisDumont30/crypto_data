-- Schéma dédié à la BI
CREATE SCHEMA IF NOT EXISTS bi;

-- Vue des bougies 1m (seule chose que Streamlit pourra lire)
CREATE OR REPLACE VIEW bi.v_klines_1m AS
SELECT
    symbol,
    open_time,
    open,
    high,
    low,
    close,
    volume
FROM public.klines
WHERE "interval" = '1m';

-- Rôle en lecture seule (mot de passe fourni en variable psql, jamais en dur)
CREATE ROLE bi_ro LOGIN PASSWORD :'bi_pwd';

GRANT CONNECT ON DATABASE crypto TO bi_ro;
GRANT USAGE ON SCHEMA bi TO bi_ro;
GRANT SELECT ON bi.v_klines_1m TO bi_ro;



-- Dernier prix connu de chaque crypto (pour le top 5)
CREATE OR REPLACE VIEW bi.v_latest_prices AS
SELECT DISTINCT ON (coin_id)
    coin_id,
    coin_symbol,
    coin_name,
    current_price,
    market_cap,
    total_volume,
    collected_at
FROM public.market_snapshots
ORDER BY coin_id, collected_at DESC;

GRANT SELECT ON bi.v_latest_prices TO bi_ro;