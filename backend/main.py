import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage

from agent.news_agent import app as news_agent_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@app.get("/health")
def health():
    return {"status": "ok"}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    lc_messages = []
    for m in req.messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    async def event_stream():
        async for chunk in news_agent_app.astream(
            {"messages": lc_messages}, stream_mode="updates"
        ):
            for node_name, output in chunk.items():
                if node_name == "agent":
                    msg = output["messages"][-1]
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            yield _sse({
                                "type": "tool_call",
                                "name": tc["name"],
                                "args": tc.get("args", {}),
                            })
                    elif msg.content:
                        yield _sse({"type": "reply", "content": msg.content})
                elif node_name == "tools":
                    for msg in output["messages"]:
                        preview = (msg.content or "")[:200]
                        yield _sse({
                            "type": "tool_result",
                            "name": getattr(msg, "name", None),
                            "preview": preview,
                        })
        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
