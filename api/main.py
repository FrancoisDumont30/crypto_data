from fastapi import FastAPI, HTTPException
from datetime import datetime
from queries import get_last_price, get_db_klines

app = FastAPI()


@app.get("/")
def read_root():
    """Root endpoint welcoming users and directing to documentation."""
    # Return a welcome message with a pointer to the Swagger UI
    return {"message": "Welcome to the Crypto API! Go to /docs to see the documentation."}


@app.get("/health")
def health():
    """Health check endpoint to verify the API is running."""
    return {"status": "ok"}


@app.get('/price/{coin_id}')
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


@app.get('/klines/{coin_id}')
def get_klines(coin_id: str, start: datetime, end: datetime):
    """Retrieve historical candlestick (klines) data for a coin within a date range."""
    # Fetch klines from the query layer
    res = get_db_klines(coin_id, start, end)

    if not res:
        raise HTTPException(status_code=404, detail="No data found")

    return res