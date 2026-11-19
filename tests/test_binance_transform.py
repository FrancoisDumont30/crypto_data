import datetime
import pandas as pd
import transform.models as klines_module
import pytest


RAW_COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]

FLOAT_COLS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_asset_volume",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
]

OUTPUT_COLS = [
    "symbol",
    "interval",
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
]


@pytest.fixture
def patched_constants(monkeypatch):
    monkeypatch.setattr(klines_module, "RAW_COLUMNS", RAW_COLS)
    monkeypatch.setattr(klines_module, "FLOAT_COLUMNS", FLOAT_COLS)
    monkeypatch.setattr(klines_module, "OUTPUT_COLUMNS", OUTPUT_COLS)


def make_kline(
    open_time: int = 1_700_000_000_000,
    close_time: int = 1_700_000_059_999,
    open_p: str | float = "100.5",
    high_p: str | float = "105.0",
    low_p: str | float = "99.0",
    close_p: str | float = "102.25",
    volume: str | float = "12.5",
    quote_vol: str | float = "1275.0",
    trades: int | str = 42,
    taker_base: str | float = "6.0",
    taker_quote: str | float = "612.0",
    ignore: str | float = "0",
) -> list:
    return [
        open_time,
        open_p,
        high_p,
        low_p,
        close_p,
        volume,
        close_time,
        quote_vol,
        trades,
        taker_base,
        taker_quote,
        ignore,
    ]


# --- 1. Cas nominaux et structure de sortie ---
def test_nominal_transformation_columns_and_metadata(patched_constants):
    raw = [make_kline()]

    result = klines_module.transform(raw, "BTCUSDT", "1m")

    assert list(result.columns) == OUTPUT_COLS
    assert "ignore" not in result.columns
    assert len(result) == 1
    assert (result["symbol"] == "BTCUSDT").all()
    assert (result["interval"] == "1m").all()


def test_time_conversion_utc_and_exact_values(patched_constants):
    t_open = 1_700_000_000_000
    t_close = 1_700_000_059_999
    raw = [make_kline(open_time=t_open, close_time=t_close)]

    result = klines_module.transform(raw, "BTCUSDT", "1m")

    assert result["open_time"].dt.tz == datetime.timezone.utc
    assert result["close_time"].dt.tz == datetime.timezone.utc
    assert result.loc[0, "open_time"] == pd.Timestamp(t_open, unit="ms", tz="UTC")
    assert result.loc[0, "close_time"] == pd.Timestamp(t_close, unit="ms", tz="UTC")


def test_numeric_types(patched_constants):
    raw = [make_kline()]

    result = klines_module.transform(raw, "BTCUSDT", "1m")

    for col in FLOAT_COLS:
        assert pd.api.types.is_float_dtype(result[col])
    assert result["trades"].dtype == "int64"


# --- 2. Cas limites et données vides ---
def test_empty_raw_returns_empty_dataframe_with_output_columns(patched_constants):
    result = klines_module.transform([], "BTCUSDT", "1m")

    assert result.empty
    assert list(result.columns) == OUTPUT_COLS


def test_string_numeric_values_are_cast(patched_constants):
    raw = [
        make_kline(
            open_p="25000.125",
            high_p="25100.5",
            low_p="24900.0",
            close_p="25050.75",
            volume="100.25",
            quote_vol="2510000.0",
            trades="150",
            taker_base="50.0",
            taker_quote="1250000.0",
        )
    ]

    result = klines_module.transform(raw, "BTCUSDT", "5m")

    assert result.loc[0, "open"] == pytest.approx(25000.125)
    assert result.loc[0, "trades"] == 150
    assert result["trades"].dtype == "int64"


# --- 3. Nettoyage, déduplication et tri ---
def test_deduplicates_same_symbol_interval_open_time(patched_constants):
    kline_first = make_kline(open_time=1_700_000_000_000, close_p="100.0", trades=10)
    kline_duplicate = make_kline(open_time=1_700_000_000_000, close_p="105.0", trades=20)

    result = klines_module.transform([kline_first, kline_duplicate], "BTCUSDT", "1m")

    assert len(result) == 1
    assert result.loc[0, "close"] == pytest.approx(100.0)
    assert result.loc[0, "trades"] == 10


def test_does_not_drop_same_open_time_for_different_symbol_or_interval(patched_constants):
    shared_open_time = 1_700_000_000_000
    kline = make_kline(open_time=shared_open_time)

    res_btc = klines_module.transform([kline], "BTCUSDT", "1m")
    res_eth = klines_module.transform([kline], "ETHUSDT", "1m")
    res_5m = klines_module.transform([kline], "BTCUSDT", "5m")

    combined = pd.concat([res_btc, res_eth, res_5m], ignore_index=True)
    deduped = combined.drop_duplicates(subset=["symbol", "interval", "open_time"])

    assert len(deduped) == 3


def test_sorts_by_open_time_and_resets_index(patched_constants):
    t1 = 1_700_000_120_000
    t2 = 1_700_000_000_000
    t3 = 1_700_000_060_000

    raw = [
        make_kline(open_time=t1, close_p="300.0"),
        make_kline(open_time=t2, close_p="100.0"),
        make_kline(open_time=t3, close_p="200.0"),
    ]

    result = klines_module.transform(raw, "BTCUSDT", "1m")

    assert list(result.index) == [0, 1, 2]
    assert list(result["close"]) == [100.0, 200.0, 300.0]
    assert result["open_time"].is_monotonic_increasing


# --- 4. Cas d’erreur et robustesse ---


def test_mismatched_column_count_raises(patched_constants):
    short_kline = [1_700_000_000_000, "100.0"]  # Trop peu de colonnes

    with pytest.raises(ValueError):
        klines_module.transform([short_kline], "BTCUSDT", "1m")


def test_invalid_float_value_raises(patched_constants):
    bad_kline = make_kline(close_p="not_a_number")

    with pytest.raises(ValueError):
        klines_module.transform([bad_kline], "BTCUSDT", "1m")


def test_invalid_trades_value_raises(patched_constants):
    bad_kline = make_kline(trades="abc")

    with pytest.raises(ValueError):
        klines_module.transform([bad_kline], "BTCUSDT", "1m")


def test_missing_output_column_raises_key_error(monkeypatch):
    monkeypatch.setattr(klines_module, "RAW_COLUMNS", RAW_COLS)
    monkeypatch.setattr(klines_module, "FLOAT_COLUMNS", FLOAT_COLS)
    monkeypatch.setattr(klines_module, "OUTPUT_COLUMNS", OUTPUT_COLS + ["non_existent_col"])

    with pytest.raises(KeyError):
        klines_module.transform([make_kline()], "BTCUSDT", "1m")


# --- 5. Isolation des constantes globales ---


def test_constants_are_not_mutated_by_transform(monkeypatch):
    raw_cols_copy = list(RAW_COLS)
    float_cols_copy = list(FLOAT_COLS)
    output_cols_copy = list(OUTPUT_COLS)

    monkeypatch.setattr(klines_module, "RAW_COLUMNS", raw_cols_copy)
    monkeypatch.setattr(klines_module, "FLOAT_COLUMNS", float_cols_copy)
    monkeypatch.setattr(klines_module, "OUTPUT_COLUMNS", output_cols_copy)

    klines_module.transform([make_kline()], "BTCUSDT", "1m")

    assert raw_cols_copy == RAW_COLS
    assert float_cols_copy == FLOAT_COLS
    assert output_cols_copy == OUTPUT_COLS