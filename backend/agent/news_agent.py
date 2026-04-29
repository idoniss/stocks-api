"""
News agent — uses tools to fetch news and prices for stocks, then answers.

Run:  python news_agent.py
"""

import os
from datetime import date, datetime, timedelta
from typing import Annotated, TypedDict

import requests
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def get_news(symbol: str) -> str:
    """Get recent news headlines (last 7 days) about a publicly traded company.

    Use when: the user asks about news, recent developments, what's happening
    with a company, or any qualitative update on a stock.
    Do NOT use for: current price or today's price change — use get_stock_price.
    Historical prices and news older than 7 days are not available.

    Args:
        symbol: Exchange ticker symbol (e.g. "AAPL", "NVDA"). Use the canonical
            ticker, not the company name.

    Returns:
        A text block of articles, one per line, formatted "<Mon DD>: <headline> — <summary>".
        Returns "No recent news found for {symbol}." if there are no articles
        in the last 7 days.
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
    """Get the current price and today's intraday change for a publicly traded company.

    Use when: the user asks about price, today's change, percent change, or
    current value of a stock.
    Do NOT use for: news, qualitative company updates, or historical prices —
    use get_news for news; historical data is not available from this agent.

    Args:
        symbol: Exchange ticker symbol (e.g. "AAPL", "NVDA"). Use the canonical
            ticker, not the company name.

    Returns:
        A single-line string formatted "<SYMBOL>: $<price> (change <±N.NN>, <±N.NN>%)".
        Returns "No price data found for {symbol}." if the ticker is unrecognized.
        During US market hours: real-time intraday data. Outside market hours:
        previous close.
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
llm = ChatOpenAI(model="o4-mini", reasoning_effort="low").bind_tools(tools)


SYSTEM_PROMPT = """<role>
You are a stocks assistant that helps users understand publicly traded companies. You have tools to fetch live prices and recent news.
</role>

<behavior>
- Respond in the same language the user wrote in. If the user writes in Hebrew, reply in fluent, natural Hebrew — rephrase the article content the way a native Hebrew financial-news writer would summarize it, rather than producing a literal word-by-word translation of the English source. The same principle applies for any other language: prioritize natural phrasing in the target language over fidelity to the English wording.
- Decide which tools to call based on the user's question. You may call zero, one, or both tools.
- For news, format each item as a short bullet starting with the date, using the natural date format of the user's language. In English: "Apr 22 — Company announced...". In Hebrew: "22 באפריל — ...". Default to 3-5 bullets.
- For prices, answer in one or two short sentences.
- If a tool returns "No data found" or "No recent news", relay that clearly. Do not fabricate values.
</behavior>

<tools>
- get_stock_price(symbol): current price and today's intraday change.
- get_news(symbol): rolling 7-day news headlines and short summaries.
</tools>"""


def agent(state: State):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
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
