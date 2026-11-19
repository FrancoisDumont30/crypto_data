from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from decimal import Decimal
import pytest
from pydantic import BaseModel

# Adaptez l'import ci-dessous selon votre module réel, par exemple :
from transform.models import process_coingecko_data
MODULE_PATH = "transform.models"

class DummySnapshot(BaseModel):
    id: str
    symbol: str
    name: str
    price: float
    collected_at: datetime

@pytest.fixture
def valid_item() -> dict:
    return {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": "65000.50",
        "market_cap": "1200000000000",
        "total_volume": "25000000000",
        "last_updated": "2026-11-19T10:00:00Z",
    }


@pytest.fixture
def invalid_item() -> dict:
    # 'current_price' non convertible en Decimal -> déclenche ValidationError
    return {
        "id": "solana",
        "symbol": "sol",
        "name": "Solana",
        "current_price": "not-a-decimal",
    }

def test_empty_raw_data_raises_runtime_error():
    with pytest.raises(RuntimeError, match="Received empty raw data from CoinGecko API."):
        process_coingecko_data([])


def test_all_valid_items_are_processed_and_share_timestamp(valid_item):
    fixed_now = datetime(2026, 11, 19, 10, 30, 45, 987654, tzinfo=timezone.utc)
    expected_collected_at = fixed_now.replace(microsecond=0)

    mock_datetime = MagicMock()
    mock_datetime.now.return_value = fixed_now

    raw_data = [
        {**valid_item, "id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "current_price": "65000.50"},
        {**valid_item, "id": "ethereum", "symbol": "eth", "name": "Ethereum", "current_price": "3200.25"},
    ]

    with patch(f"{MODULE_PATH}.datetime", mock_datetime):
        result = process_coingecko_data(raw_data)

    assert len(result) == 2
    assert result[0]["coin_id"] == "bitcoin"
    assert result[0]["coin_symbol"] == "btc"
    assert result[0]["coin_name"] == "Bitcoin"
    assert result[0]["current_price"] == Decimal("65000.50")
    assert result[0]["collected_at"] == expected_collected_at
    assert result[0]["collected_at"].microsecond == 0
    assert result[0]["collected_at"].tzinfo == timezone.utc

    assert result[1]["coin_id"] == "ethereum"
    assert result[1]["current_price"] == Decimal("3200.25")
    assert result[1]["collected_at"] == expected_collected_at

def test_partial_invalid_items_below_threshold_are_skipped_and_logged(
    caplog, valid_item, invalid_item
):
    # 1 rejet sur 4 lignes = 25 % (<= 50 %)
    raw_data = [
        {**valid_item, "id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {**valid_item, "id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        {**valid_item, "id": "cardano", "symbol": "ada", "name": "Cardano"},
        invalid_item,
    ]

    with caplog.at_level("WARNING", logger=MODULE_PATH):
        result = process_coingecko_data(raw_data)

    assert len(result) == 3
    assert [row["coin_id"] for row in result] == ["bitcoin", "ethereum", "cardano"]
    assert any("Invalid data for coin_id 'solana'" in record.message for record in caplog.records)


def test_exact_fifty_percent_rejection_rate_does_not_raise(valid_item, invalid_item):
    # 2 rejets sur 4 lignes = 50 % exact (la condition est > 0.5)
    raw_data = [
        {**valid_item, "id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {**valid_item, "id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        {**invalid_item, "id": "solana", "symbol": "sol"},
        {**invalid_item, "id": "polkadot", "symbol": "dot"},
    ]

    result = process_coingecko_data(raw_data)

    assert len(result) == 2
    assert [row["coin_id"] for row in result] == ["bitcoin", "ethereum"]


def test_rejection_rate_above_fifty_percent_raises_runtime_error(valid_item, invalid_item):
    # 2 rejets sur 3 lignes = ~66.7 % (> 50 %)
    raw_data = [
        valid_item,
        {**invalid_item, "id": "solana", "symbol": "sol"},
        {**invalid_item, "id": "avalanche", "symbol": "avax"},
    ]

    with pytest.raises(RuntimeError, match="Abnormal data rejection rate: 2/3 rows rejected."):
        process_coingecko_data(raw_data)


def test_missing_coin_id_logs_unknown(caplog, valid_item):
    # 1 ligne invalide sans 'id' ni 'coin_id' sur 3 lignes = 33.3 %
    item_without_id = {
        "symbol": "unk",
        "name": "Unknown",
        "current_price": "not-a-decimal",
    }
    raw_data = [
        valid_item,
        {**valid_item, "id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        item_without_id,
    ]

    with caplog.at_level("WARNING", logger=MODULE_PATH):
        result = process_coingecko_data(raw_data)

    assert len(result) == 2
    assert any("Invalid data for coin_id 'unknown'" in record.message for record in caplog.records)
    # 1 ligne invalide sans clé 'id' sur 3 lignes -> 33.3 % de rejet, log avec 'unknown'
    item_without_id = {"price": "invalid"}
    raw_data = [
        valid_item,
        {**valid_item, "id": "ethereum"},
        item_without_id,
    ]

    with (
        caplog.at_level("WARNING"),
        patch.dict(globals(), {"MarketSnapshot": DummySnapshot}),
    ):
        result = process_coingecko_data(raw_data)

    assert len(result) == 2
    assert any("Invalid data for coin_id 'unknown'" in record.message for record in caplog.records)