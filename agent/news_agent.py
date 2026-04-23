"""
News agent — fetches recent news for a stock and summarizes it.

Run:  python news_agent.py
"""

import os
from datetime import date, timedelta
from typing import TypedDict

import requests
from openai import OpenAI
from langgraph.graph import StateGraph, END


class State(TypedDict):
    symbol: str
    articles: list
    summary: str


def fetch_news(state: State):
    symbol = state["symbol"]
    api_key = os.environ["FINNHUB_API_KEY"]

    today = date.today()
    week_ago = today - timedelta(days=7)

    url = "https://finnhub.io/api/v1/company-news"
    params = {
        "symbol": symbol,
        "from": week_ago.isoformat(),
        "to": today.isoformat(),
        "token": api_key,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    articles = response.json()

    return {"articles": articles}


def summarize(state: State):
    symbol = state["symbol"]
    articles = state["articles"]

    headlines_block = "\n".join(
        f"- {a.get('headline')}: {a.get('summary')}" for a in articles
    )

    prompt = (
        f"Please summarize the recent news about the company with ticker {symbol}. "
        f"Focus on what's relevant to the company itself (not the broader market). "
        f"Keep it to 3-5 short bullet points.\n\n"
        f"Articles:\n{headlines_block}"
    )

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    summary_text = response.choices[0].message.content

    return {"summary": summary_text}


graph = StateGraph(State)
graph.add_node("fetch_news", fetch_news)
graph.add_node("summarize", summarize)
graph.set_entry_point("fetch_news")
graph.add_edge("fetch_news", "summarize")
graph.add_edge("summarize", END)

app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({"symbol": "NVDA"})
    print(result["summary"])
