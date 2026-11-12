import pandas as pd



RAW_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]

FLOAT_COLUMNS = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ]

OUTPUT_COLUMNS = [
    "symbol",
    "interval",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def transform(raw :list[list], symbol:str, interval:str) :

    if not raw:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
      
    df = pd.DataFrame(raw, columns = RAW_COLUMNS).drop(columns=['ignore'])

    # types
    df['symbol'] = symbol
    df['interval'] = interval
    df[FLOAT_COLUMNS] = df[FLOAT_COLUMNS].astype(float)
    df['trades'] = df['trades'].astype('int64')

    for col in ("open_time", "close_time"):
            df[col] = pd.to_datetime(df[col], unit="ms", utc=True)

    df = (
        df[OUTPUT_COLUMNS]
        .drop_duplicates(subset=["symbol", "interval", "open_time"])
        .sort_values("open_time")
        .reset_index(drop=True)
    )

    return df


