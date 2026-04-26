"""
News agent — uses tools to fetch news and prices for stocks, then answers.

Run:  python news_agent.py
"""

import os
from datetime import date, datetime, timedelta
from typing import Annotated, TypedDict

import requests
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def get_news(symbol: str) -> str:
    """Get recent news articles (last 7 days) about a publicly traded company.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL", "NVDA").

    Returns:
        A text block listing recent news articles, one per line, with date,
        headline, and short summary.
    """
    api_key = os.environ["FINNHUB_API_KEY"]
    today = date.today()
    week_ago = today - timedelta(days=7)

    response = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": symbol,
            "from": week_ago.isoformat(),
            "to": today.isoformat(),
            "token": api_key,
        },
    )
    response.raise_for_status()
    articles = response.json()

    if not articles:
        return f"No recent news found for {symbol}."

    lines = []
    for a in articles:
        ts = a.get("datetime")
        date_str = datetime.fromtimestamp(ts).strftime("%b %d") if ts else "unknown"
        lines.append(f"- {date_str}: {a.get('headline')} — {a.get('summary')}")
    return "\n".join(lines)


@tool
def get_stock_price(symbol: str) -> str:
    """Get the current stock price and today's change for a publicly traded company.

    Args:
        symbol: Stock ticker symbol (e.g. "AAPL", "NVDA").

    Returns:
        A short string with the current price, absolute change, and percent change.
    """
    api_key = os.environ["FINNHUB_API_KEY"]
    response = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": api_key},
    )
    response.raise_for_status()
    data = response.json()

    if not data.get("pc"):
        return f"No price data found for {symbol}."

    return (
        f"{symbol.upper()}: ${data['c']:.2f} "
        f"(change {data['d']:+.2f}, {data['dp']:+.2f}%)"
    )


class State(TypedDict):
    messages: Annotated[list, add_messages]


tools = [get_news, get_stock_price]
llm = ChatOpenAI(model="gpt-4o-mini").bind_tools(tools)


def agent(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


graph = StateGraph(State)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")

app = graph.compile()


if __name__ == "__main__":
    result = app.invoke(
        {"messages": [HumanMessage(content="Summarize the latest news about NVDA.")]}
    )
    print(result["messages"][-1].content)
