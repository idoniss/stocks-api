import os
from fastapi import FastAPI, HTTPException
import requests

app = FastAPI()

ALPHA_VANTAGE_API_KEY = os.environ["ALPHA_VANTAGE_API_KEY"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stock/{symbol}")
def get_stock_price(symbol: str):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "Global Quote" not in data or not data["Global Quote"]:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    quote = data["Global Quote"]
    return {
        "symbol": quote["01. symbol"],
        "price": quote["05. price"],
        "change": quote["09. change"],
        "change_percent": quote["10. change percent"],
    }
