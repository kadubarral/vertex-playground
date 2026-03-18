"""
FastAPI chat server powered by Google Gemini (Vertex AI or Gemini Developer API)
with automatic function calling against a local SQLite customer database.

Start with:  uvicorn server:app --reload
Docs at:     http://localhost:8000/docs
"""

import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from google import genai
from google.genai import types

from db import init_db, lookup_customer, list_customers_by_plan, get_customer_stats
from genai_config import load_config, build_client

_cfg = load_config()
MODEL = _cfg["model"]

SYSTEM_INSTRUCTION = (
    "You are a helpful internal assistant with access to a customer database. "
    "When the user asks about customers, accounts, revenue (MRR), or plan details, "
    "use the available tools to look up real data before answering. "
    "Always base your answers on the actual data returned by the tools. "
    "If no results are found, say so clearly. "
    "Be concise and format numbers and tables nicely."
)

DB_TOOLS = [lookup_customer, list_customers_by_plan, get_customer_stats]

client: genai.Client = None  # type: ignore[assignment]
sessions: dict[str, genai.chats.Chat] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global client
    init_db()
    client = build_client(_cfg)
    yield
    client.close()


app = FastAPI(
    title="Gemini Chat API",
    description=(
        "Chat with Gemini, enriched with customer data from SQLite. "
        f"Backend: {_cfg['backend'].upper()}"
    ),
    lifespan=lifespan,
)


# -- Request / Response models ------------------------------------------------

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    backend: str


# -- Endpoints ----------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "backend": _cfg["backend"], "model": MODEL}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())

    if sid not in sessions:
        sessions[sid] = client.chats.create(
            model=MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=DB_TOOLS,
            ),
        )

    chat_session = sessions[sid]

    try:
        response = chat_session.send_message(req.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model error: {exc}") from exc

    return ChatResponse(session_id=sid, response=response.text, backend=_cfg["backend"])


@app.delete("/chat/{session_id}")
def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del sessions[session_id]
    return {"status": "deleted", "session_id": session_id}
