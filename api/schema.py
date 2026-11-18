from pydantic import BaseModel, AwareDatetime
from decimal import Decimal
from datetime import datetime
from typing_extensions import TypedDict

class PriceResponse(BaseModel):
    coin_id : str
    current_price : Decimal | None = None
    collected_at : datetime

class Candles(TypedDict):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class KlineResponse(BaseModel):
    coin_id : str
    symbol: str
    count: int
    candles: list[Candles]