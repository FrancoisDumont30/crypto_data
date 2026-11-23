from datetime import datetime, time, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import query_df

st.set_page_config(page_title="Crypto BI", layout="wide")

CANDLES = {
    "1 minute": "1 minute",
    "5 minutes": "5 minutes",
    "15 minutes": "15 minutes",
    "1 heure": "1 hour",
    "4 heures": "4 hours",
    "1 jour": "1 day",
}
# Unités de temps du graphique d'évolution des prix (pas de 4 heures)
PRICE_UNITS = {
    "Minute": "1 minute",
    "Heure": "1 hour",
    "Jour": "1 day",
}


@st.cache_data(ttl=300)
def get_bounds() -> tuple:
    df = query_df(
        "SELECT min(open_time) AS first_open, max(open_time) AS last_open "
        "FROM bi.v_klines_1m"
    )
    return df.loc[0, "first_open"], df.loc[0, "last_open"]


@st.cache_data(ttl=300)
def get_coins() -> pd.DataFrame:
    """Cryptos ayant une paire Binance : symbole USDT, nom, dernier prix.
    Les symboles partagés par plusieurs coins sont écartés (correspondance ambiguë)."""
    df = query_df(
        """
        WITH latest AS (
            SELECT upper(coin_symbol) || 'USDT' AS symbol,
                   coin_name,
                   current_price,
                   count(*) OVER (PARTITION BY upper(coin_symbol)) AS n
            FROM bi.v_latest_prices
        )
        SELECT symbol, coin_name, current_price
        FROM latest
        WHERE n = 1
          AND symbol IN (SELECT DISTINCT symbol FROM bi.v_klines_1m)
        ORDER BY current_price DESC
        """
    )
    df["current_price"] = df["current_price"].astype(float)
    return df


@st.cache_data(ttl=300)
def get_variations(start, end) -> pd.DataFrame:
    df = query_df(
        """
        WITH w AS (
            SELECT symbol, open_time, open, close
            FROM bi.v_klines_1m
            WHERE open_time >= %s AND open_time < %s
        ),
        debut AS (
            SELECT DISTINCT ON (symbol) symbol, open AS first_open
            FROM w ORDER BY symbol, open_time ASC
        ),
        fin AS (
            SELECT DISTINCT ON (symbol) symbol, close AS last_close
            FROM w ORDER BY symbol, open_time DESC
        )
        SELECT d.symbol,
               (f.last_close - d.first_open) / NULLIF(d.first_open, 0) * 100.0
                   AS variation_pct
        FROM debut d JOIN fin f USING (symbol)
        """,
        (start, end),
    )
    df["variation_pct"] = df["variation_pct"].astype(float)
    return df


@st.cache_data(ttl=300)
def get_candles(symbol: str, stride: str, start, end) -> pd.DataFrame:
    df = query_df(
        """
        SELECT date_bin(%s::interval, open_time, '2000-01-01') AS bucket,
               (array_agg(open ORDER BY open_time ASC))[1] AS open,
               max(high) AS high,
               min(low) AS low,
               (array_agg(close ORDER BY open_time DESC))[1] AS close
        FROM bi.v_klines_1m
        WHERE symbol = %s AND open_time >= %s AND open_time < %s
        GROUP BY bucket
        ORDER BY bucket
        """,
        (stride, symbol, start, end),
    )
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    return df


@st.cache_data(ttl=300)
def get_prices(stride: str, start, end) -> pd.DataFrame:
    """Dernier prix (close) de chaque crypto, par minute / heure / jour."""
    df = query_df(
        """
        SELECT symbol,
               date_bin(%s::interval, open_time, '2000-01-01') AS bucket,
               (array_agg(close ORDER BY open_time DESC))[1] AS price
        FROM bi.v_klines_1m
        WHERE open_time >= %s AND open_time < %s
        GROUP BY symbol, bucket
        ORDER BY symbol, bucket
        """,
        (stride, start, end),
    )
    df["price"] = df["price"].astype(float)
    return df

def show_variation(column, label: str, row: pd.Series, color: str) -> None:
    """Libellé, puis une ligne : nom · symbole Binance · variation colorée."""
    with column.container(border=True):
        st.subheader(label)
        st.subheader(
            f"{row['coin_name']} ({row['symbol']}) : "
            f":{color}[{row['variation_pct']:+.2f} %]"
        )

# --- 1. Titre ---
st.title("Crypto BI")

# --- 2. Dernières bougies ---
first_open, last_open = get_bounds()
if pd.isna(last_open):
    st.warning("Aucune bougie en base.")
    st.stop()

st.write(
    f"Dernières données : {last_open:%d/%m/%Y %H:%M}")

# --- 3. Période (défaut : 30 derniers jours, ancrés sur la dernière bougie) ---
st.subheader("Choix de la période")
default_end = last_open.date()
default_start = default_end - timedelta(days=29)

d1, d2, _ = st.columns([1, 1, 4])
start_date = d1.date_input("Début", value=default_start, format="DD/MM/YYYY")
end_date = d2.date_input("Fin", value=default_end, format="DD/MM/YYYY")

if start_date > end_date:
    st.error("La date de début doit être antérieure à la date de fin.")
    st.stop()

start = datetime.combine(start_date, time.min)
end = datetime.combine(end_date + timedelta(days=1), time.min)  # fin incluse

if start_date < first_open.date():
    info_col, _ = st.columns([2, 4])  # même largeur que les deux sélecteurs de dates
    info_col.info(f"Historique disponible seulement à partir du {first_open:%d/%m/%Y}.")
st.divider()

# --- 4. Les plus grandes variations de prix ---
coins = get_coins()
if coins.empty:
    st.warning("Aucune crypto avec une paire Binance.")
    st.stop()

variations = get_variations(start, end).merge(
    coins[["symbol", "coin_name"]], on="symbol"
)
if variations.empty:
    st.warning("Pas de bougies sur cette période.")
    st.stop()

best = variations.loc[variations["variation_pct"].idxmax()]
worst = variations.loc[variations["variation_pct"].idxmin()]

st.subheader("Les plus grandes variations de prix :")
col_sapce, col_up, one_space,col_down, space2 = st.columns([.5,1,.5,1,3])

show_variation(col_up, "Plus forte hausse", best, "green")
show_variation(col_down, "Plus forte baisse", worst, "red")
st.divider()

# --- 5. Top 5 des cryptos les plus chères (moitié de la largeur) ---
st.subheader("Top 5 des cryptos les plus chères")
top5 = coins.head(5)[["coin_name", "symbol", "current_price"]].rename(
    columns={"coin_name": "Nom", "symbol": "Symbole", "current_price": "Prix (USD)"}
)
left, _ = st.columns(2)
left.dataframe(
    top5,
    hide_index=True,
    width="stretch",
    column_config={"Prix (USD)": st.column_config.NumberColumn(format="$%.2f")},
)
st.divider()

# --- 7. Chandeliers d'une crypto ---
st.subheader("Chandeliers")
symbol_by_name = dict(zip(coins["coin_name"], coins["symbol"]))
names = sorted(symbol_by_name)
default_name = names.index("Bitcoin") if "Bitcoin" in names else 0

s1, s2, _ = st.columns([1, 1, 4])
name = s1.selectbox("Crypto", names, index=default_name)
candle_label = s2.selectbox(
    "Taille des bougies", list(CANDLES), index=list(CANDLES).index("1 jour")
)

candles = get_candles(symbol_by_name[name], CANDLES[candle_label], start, end)

if candles.empty:
    st.info("Pas de bougies pour cette crypto sur cette période.")
else:
    fig = go.Figure(
        go.Candlestick(
            x=candles["bucket"],
            open=candles["open"],
            high=candles["high"],
            low=candles["low"],
            close=candles["close"],
        )
    )
    fig.update_layout(xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, width="stretch")