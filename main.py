import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

from agent.news_agent import app as news_agent_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

FINNHUB_API_KEY = os.environ["FINNHUB_API_KEY"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stock/{symbol}")
def get_stock_price(symbol: str):
    url = "https://finnhub.io/api/v1/quote"
    params = {
        "symbol": symbol,
        "token": FINNHUB_API_KEY,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("pc"):
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    return {
        "symbol": symbol.upper(),
        "price": f"{data['c']:.2f}",
        "change": f"{data['d']:.2f}",
        "change_percent": f"{data['dp']:.2f}%",
    }


@app.get("/news/{symbol}")
def get_news(symbol: str):
    result = news_agent_app.invoke({"symbol": symbol})
    return {"symbol": symbol.upper(), "summary": result["summary"]}
