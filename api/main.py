from fastapi import FastAPI, HTTPException
from datetime import datetime

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Crypto ! Va sur /docs pour voir la documentation."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get('/price/{coin_id}')
def get_price(coin_id: str) :
    from queries import get_last_price

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
def get_klines(coin_id: str, start : datetime, end : datetime) :
    from queries import get_db_klines

    res = get_db_klines(coin_id, start, end)

    if not res:
        raise HTTPException(status_code=404, detail=f"No data found")

    return res