from fastapi import FastAPI, HTTPException, Path, Query, Request
import time
from datetime import datetime, timedelta
from queries import get_last_price, get_db_klines
from schema import KlineResponse, PriceResponse
from typing import Annotated

app = FastAPI(title="Crypto API")

MAX_RANGE = timedelta(days=7)

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    """Add the server-side processing time (ms) in the X-Process-Time header."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.1f}"
    return response


@app.get("/")
def read_root():
    """Root endpoint welcoming users and directing to documentation."""
    # Return a welcome message with a pointer to the Swagger UI
    return {"message": "Welcome to the Crypto API! Go to /docs to see the documentation."}


@app.get("/health")
def health():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok"}


@app.get('/price/{coin_id}', 
         response_model = PriceResponse,
         responses={404: {"description": "Coin not found"}},
         )

def get_price(coin_id: str):
    """Retrieve the latest collected price for a specific coin."""
    # Fetch the last price from the database/query layer
    res = get_last_price(coin_id)

    if not res:
        raise HTTPException(status_code=404, detail=f"{coin_id} not found")

    db_coin_id, current_price, collected_at = res

    return {
        'coin_id': db_coin_id,
        'current_price': current_price, 
        'collected_at': collected_at
    } 


@app.get('/klines/{coin_id}', 
         response_model = KlineResponse,
         responses={
        404: {"description": "No data found"},
        422: {"description": "Invalid date range"},
        },)

def get_klines(
    coin_id: Annotated[str, Path(min_length=1, max_length=64, pattern=r"^[a-z0-9\-]+$")],
    start: Annotated[datetime, Query(description="ISO 8601 with timezone, e.g. 2026-11-17T00:00:00Z")],
    end: Annotated[datetime, Query(description="ISO 8601 with timezone, e.g. 2026-11-18T00:00:00Z")],
):
    if start >= end:
        raise HTTPException(status_code=422, detail="start must be before end")
    if end - start > MAX_RANGE:
        raise HTTPException(status_code=422, detail="range cannot exceed 7 days")

    res = get_db_klines(coin_id, start, end)
    if not res:
        raise HTTPException(status_code=404, detail="No data found")
    return res