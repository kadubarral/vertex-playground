# Vertex AI Playground

Sample application to explore Google Gemini integration using the [Google Gen AI Python SDK](https://github.com/googleapis/python-genai).

Supports three backends out of the box:

| Backend | Auth | Use case |
|---------|------|----------|
| **Vertex AI** | Application Default Credentials | Production / GCP-native |
| **Gemini Developer API** | API key | Quick prototyping |
| **NeuralTrust Gateway** | ADC Bearer + TG API key | Proxied access via NeuralTrust |

Two entry points are provided:

| Entry point | What it is |
|-------------|------------|
| `app.py` | Interactive CLI with 9 focused demos (text generation, chat, function calling, embeddings, etc.) |
| `server.py` | FastAPI REST API for multi-turn chat, enriched with real customer data from SQLite via Gemini function calling |

## Prerequisites

- Python 3.10+
- One of the following, depending on the backend:
  - **Vertex AI** — A Google Cloud project with the Vertex AI API enabled, authenticated locally via `gcloud auth application-default login`
  - **Gemini Developer API** — A Gemini API key from [Google AI Studio](https://aistudio.google.com/)
  - **NeuralTrust Gateway** — A NeuralTrust API key + GCP credentials

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env — pick a backend and fill in the required values (see below)
```

---

## Configuration — `.env`

Set `GENAI_BACKEND` to choose how the SDK connects to Gemini. Configuration is resolved by `genai_config.py`.

### Backend: Vertex AI (default)

```bash
GENAI_BACKEND=vertex
```

Two endpoint formats are supported:

**Option A — Full URL (recommended).** Project, location, model, and API version are all parsed from the URL automatically.

```bash
VERTEX_AI_ENDPOINT=https://us-central1-aiplatform.googleapis.com/v1beta1/projects/my-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
```

**Option B — Base URL + individual variables.**

```bash
VERTEX_AI_ENDPOINT=https://us-central1-aiplatform.googleapis.com
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_AI_API_VERSION=v1beta1
MODEL_ID=gemini-2.5-flash
```

> When a full URL is set, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `MODEL_ID`, and `VERTEX_AI_API_VERSION` are all ignored — every value comes from the URL.

### Backend: Gemini Developer API

```bash
GENAI_BACKEND=gemini
GEMINI_API_KEY=your-api-key
MODEL_ID=gemini-2.5-flash          # optional, defaults to gemini-2.5-flash
```

### Backend: NeuralTrust Gateway

```bash
GENAI_BACKEND=gateway
NEURALTRUST_GATEWAY_URL=https://gateway.neuraltrust.ai/vertex
NEURALTRUST_API_KEY=your-tg-api-key
GOOGLE_CLOUD_PROJECT=my-project
MODEL_ID=gemini-2.5-flash
```

### All variables

| Variable | Description | Used by |
|----------|-------------|---------|
| `GENAI_BACKEND` | `vertex` (default), `gemini`, or `gateway` | all |
| `MODEL_ID` | Gemini model name (default `gemini-2.5-flash`) | gemini, vertex (Option B), gateway |
| `VERTEX_AI_ENDPOINT` | Full URL **or** base hostname | vertex |
| `VERTEX_AI_API_VERSION` | `v1beta1` (default) or `v1` | vertex (Option B) |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | vertex (Option B), gateway |
| `GOOGLE_CLOUD_LOCATION` | GCP region (default `us-central1`) | vertex (Option B) |
| `GEMINI_API_KEY` | API key from Google AI Studio | gemini |
| `NEURALTRUST_GATEWAY_URL` | Gateway base URL | gateway |
| `NEURALTRUST_API_KEY` | NeuralTrust TG API key | gateway |
| `GOOGLE_GENAI_USE_VERTEXAI` | Must be `true` for vertex/gateway backends | vertex, gateway |

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

A FastAPI server that exposes a stateful chat endpoint backed by Gemini. The model is equipped with three tools that query a local SQLite database of customer data; it calls them automatically whenever relevant.

### Start the server

```bash
uvicorn server:app --reload
```

Swagger UI is available at **http://localhost:8000/docs** for interactive testing.

### Endpoints

#### `GET /health`

```bash
curl http://localhost:8000/health
# {"status":"ok","backend":"vertex","model":"gemini-2.5-flash"}
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
  "response": "Model answer here",
  "backend": "vertex"
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
| `lookup_customer(query)` | Fuzzy search by customer name, company, CPF, or credit card number |
| `list_customers_by_plan(plan)` | Filter customers by `free`, `pro`, or `enterprise` |
| `get_customer_stats()` | Aggregate stats: total count, total MRR, breakdown by plan |

The SQLite database (`data.db`) is created and seeded with 10 sample customers on first run.

### Postman setup

1. Import a new request: `POST http://localhost:8000/chat`
2. Set **Body > raw > JSON**:
   ```json
   { "message": "Show me a summary of our customer base" }
   ```
3. Copy the `session_id` from the response and add it to subsequent requests to maintain conversation context.

---

## Project structure

```
├── app.py            # CLI playground — 9 interactive demos
├── server.py         # FastAPI chat API with function calling
├── genai_config.py   # Backend selection & SDK client builder
├── db.py             # SQLite schema, seed data, and query tools
├── requirements.txt  # Python dependencies
├── .env.example      # Template for environment variables
└── data.db           # SQLite database (auto-created on first run, gitignored)
```

## License

MIT
