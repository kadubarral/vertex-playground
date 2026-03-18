# Vertex AI Playground

Sample application to explore Google Vertex AI integration using the [Google Gen AI Python SDK](https://github.com/googleapis/python-genai).

Two entry points are provided:

| Entry point | What it is |
|-------------|------------|
| `app.py` | Interactive CLI with 9 focused demos (text generation, chat, function calling, embeddings, etc.) |
| `server.py` | FastAPI REST API for multi-turn chat, enriched with real customer data from SQLite via Gemini function calling |

## Prerequisites

- Python 3.10+
- A Google Cloud project with the **Vertex AI API** enabled
- Authenticated locally: `gcloud auth application-default login`

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env — set VERTEX_AI_ENDPOINT at minimum (see below)
```

---

## Configuration — `.env`

Connection to Vertex AI is resolved by `vertex_config.py` from a single `VERTEX_AI_ENDPOINT` variable. Two formats are supported:

### Option A — Full URL (recommended)

Paste the complete Vertex AI endpoint URL. Project, location, model, and API version are all parsed from it automatically — no other variables needed.

```bash
VERTEX_AI_ENDPOINT=https://us-central1-aiplatform.googleapis.com/v1beta1/projects/my-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
```

### Option B — Base URL + individual variables

Set only the hostname and control each segment separately.

```bash
VERTEX_AI_ENDPOINT=https://us-central1-aiplatform.googleapis.com
VERTEX_AI_API_VERSION=v1beta1   # v1beta1 (preview) | v1 (stable)
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_CLOUD_LOCATION=us-central1
MODEL_ID=gemini-2.5-flash
```

### All variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VERTEX_AI_ENDPOINT` | Full URL **or** base hostname (see above) | yes |
| `VERTEX_AI_API_VERSION` | API channel — `v1beta1` or `v1` | no — default `v1beta1` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | only for Option B |
| `GOOGLE_CLOUD_LOCATION` | GCP region | only for Option B |
| `MODEL_ID` | Gemini model name | only for Option B |
| `GOOGLE_GENAI_USE_VERTEXAI` | Must be `true` | yes |

> When a full URL is set, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `MODEL_ID`, and `VERTEX_AI_API_VERSION` are ignored — all values come from the URL.

---

## CLI Playground — `app.py`

Runs an interactive menu where you pick a demo and see the raw SDK output.

```bash
python3 app.py
```

| # | Demo |
|---|------|
| 1 | Basic text generation |
| 2 | Streaming text generation |
| 3 | Structured JSON output (Pydantic schema) |
| 4 | System instructions & config tuning |
| 5 | Multi-turn chat (scripted) |
| 6 | Function calling (automatic) |
| 7 | Embeddings |
| 8 | Token counting |
| 9 | **Interactive chat** — free-form Q&A with memory, streaming output, `/new` to reset |
| all | Run demos 1–8 sequentially |

---

## Chat REST API — `server.py`

A FastAPI server that exposes a stateful chat endpoint backed by Vertex AI Gemini. The model is equipped with three tools that query a local SQLite database of customer data; it calls them automatically whenever relevant.

### Start the server

```bash
uvicorn server:app --reload
```

Swagger UI is available at **http://localhost:8000/docs** for interactive testing.

### Endpoints

#### `GET /health`

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

#### `POST /chat`

Start a new conversation (omit `session_id`) or continue an existing one (pass it back).

**Request**
```json
{
  "session_id": "optional-uuid-from-previous-response",
  "message": "Your question here"
}
```

**Response**
```json
{
  "session_id": "uuid",
  "response": "Model answer here"
}
```

**curl examples**

```bash
# New conversation
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many enterprise customers do we have?"}' | jq

# Continue the conversation (replace UUID with the one returned above)
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR-UUID", "message": "What is their total MRR?"}' | jq

# Ask about a specific customer
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR-UUID", "message": "Tell me about Acme Corp"}' | jq
```

#### `DELETE /chat/{session_id}`

Clear a session and its conversation history.

```bash
curl -s -X DELETE http://localhost:8000/chat/YOUR-UUID
# {"status":"deleted","session_id":"YOUR-UUID"}
```

### Database tools available to the model

The model can call these automatically when answering questions:

| Tool | Description |
|------|-------------|
| `lookup_customer(name)` | Fuzzy search by customer name or company |
| `list_customers_by_plan(plan)` | Filter customers by `free`, `pro`, or `enterprise` |
| `get_customer_stats()` | Aggregate stats: total count, total MRR, breakdown by plan |

The SQLite database (`data.db`) is created and seeded with 10 sample customers on first run.

### Postman setup

1. Import a new request: `POST http://localhost:8000/chat`
2. Set **Body → raw → JSON**:
   ```json
   { "message": "Show me a summary of our customer base" }
   ```
3. Copy the `session_id` from the response and add it to subsequent requests to maintain conversation context.
