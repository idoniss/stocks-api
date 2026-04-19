import hashlib
import hmac
import os

import requests
from fastapi import FastAPI, HTTPException, Request, Response

app = FastAPI()

ALPHA_VANTAGE_API_KEY = os.environ["ALPHA_VANTAGE_API_KEY"]
WHATSAPP_VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]
WHATSAPP_ACCESS_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
WHATSAPP_APP_SECRET = os.environ["WHATSAPP_APP_SECRET"]


def fetch_stock_quote(symbol: str) -> dict:
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


def send_whatsapp_message(to: str, body: str) -> None:
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": body},
    }
    requests.post(url, headers=headers, json=payload)


def format_quote_reply(quote: dict) -> str:
    return (
        f"{quote['symbol']}: ${quote['price']} "
        f"({quote['change']}, {quote['change_percent']})"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stock/{symbol}")
def get_stock_price(symbol: str):
    return fetch_stock_quote(symbol)


@app.get("/webhook/whatsapp")
def whatsapp_verify(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp")
async def whatsapp_receive(request: Request):
    raw_body = await request.body()

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature_header, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()

    try:
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    except (KeyError, IndexError):
        return {"status": "ok"}

    if message.get("type") != "text":
        return {"status": "ok"}

    sender = message["from"]
    symbol = message["text"]["body"].strip().upper()

    try:
        quote = fetch_stock_quote(symbol)
        reply = format_quote_reply(quote)
    except HTTPException as e:
        if e.status_code == 404:
            reply = f"Symbol '{symbol}' not found"
        else:
            reply = "Sorry, couldn't fetch that right now."
    except Exception:
        reply = "Sorry, couldn't fetch that right now."

    send_whatsapp_message(sender, reply)
    return {"status": "ok"}
