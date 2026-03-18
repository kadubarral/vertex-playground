"""
Google Gen AI connection config.

Selects the backend based on GENAI_BACKEND env var:

  GENAI_BACKEND=gemini    → Gemini Developer API (API key auth)
  GENAI_BACKEND=vertex    → Vertex AI direct (ADC / service account)  [default]
  GENAI_BACKEND=gateway   → Vertex AI via NeuralTrust API Gateway (ADC Bearer + TG API key)

--- Gemini Developer API ---
  GENAI_BACKEND=gemini
  GEMINI_API_KEY=your-api-key
  MODEL_ID=gemini-2.5-flash        # optional

--- Vertex AI (base URL) ---
  GENAI_BACKEND=vertex
  VERTEX_AI_ENDPOINT=https://europe-west1-aiplatform.googleapis.com
  VERTEX_AI_API_VERSION=v1beta1
  GOOGLE_CLOUD_PROJECT=my-project
  GOOGLE_CLOUD_LOCATION=europe-west1
  MODEL_ID=gemini-2.5-flash

--- Vertex AI (full URL — project/location/model/version parsed automatically) ---
  GENAI_BACKEND=vertex
  VERTEX_AI_ENDPOINT=https://europe-west1-aiplatform.googleapis.com/v1beta1/projects/my-project/locations/europe-west1/publishers/google/models/gemini-2.5-flash:generateContent

--- NeuralTrust Gateway ---
  GENAI_BACKEND=gateway
  NEURALTRUST_GATEWAY_URL=https://gateway.neuraltrust.ai/vertex
  NEURALTRUST_API_KEY=your-tg-api-key
  GOOGLE_CLOUD_PROJECT=my-project
  MODEL_ID=gemini-2.5-flash
"""

import os
import re

import google.auth
import google.auth.transport.requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_FULL_URL_PATTERN = re.compile(
    r"^(?P<base>https://[^/]+)"
    r"/(?P<api_version>v\d+(?:beta\d+|alpha)?)"
    r"/projects/(?P<project>[^/]+)"
    r"/locations/(?P<location>[^/]+)"
    r"/publishers/[^/]+"
    r"/models/(?P<model>[^/:]+)"
    r"(?::[a-zA-Z]+)?$"
)


def _get_access_token() -> str:
    """Obtain a fresh access token using Application Default Credentials."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


def _parse_vertex_config() -> dict:
    raw_endpoint = os.getenv("VERTEX_AI_ENDPOINT", "")
    project_env = os.getenv("GOOGLE_CLOUD_PROJECT")
    location_env = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model_env = os.getenv("MODEL_ID", "gemini-2.5-flash")
    api_version_env = os.getenv("VERTEX_AI_API_VERSION", "v1beta1")

    if raw_endpoint and _FULL_URL_PATTERN.match(raw_endpoint):
        m = _FULL_URL_PATTERN.match(raw_endpoint)
        p = m.groupdict()
        return {
            "project": p["project"], "location": p["location"],
            "model": p["model"], "base_url": p["base"],
            "api_version": p["api_version"], "_source": "full_url",
        }

    base_url = raw_endpoint or f"https://{location_env}-aiplatform.googleapis.com"
    return {
        "project": project_env, "location": location_env,
        "model": model_env, "base_url": base_url,
        "api_version": api_version_env, "_source": "env_vars",
    }


def load_config() -> dict:
    """
    Return a unified config dict with keys:
      backend, model
      api_key                          (gemini only)
      project, location, base_url, api_version  (vertex only)
      gateway_url, gateway_api_key, project     (gateway only)
    """
    backend = os.getenv("GENAI_BACKEND", "vertex").lower()

    if backend == "gemini":
        return {
            "backend":     "gemini",
            "model":       os.getenv("MODEL_ID", "gemini-2.5-flash"),
            "api_key":     os.getenv("GEMINI_API_KEY"),
            "project":     None,
            "location":    None,
            "base_url":    None,
            "api_version": None,
        }

    if backend == "gateway":
        return {
            "backend":         "gateway",
            "model":           os.getenv("MODEL_ID", "gemini-2.5-flash"),
            "project":         os.getenv("GOOGLE_CLOUD_PROJECT"),
            "gateway_url":     os.getenv("NEURALTRUST_GATEWAY_URL", "https://gateway.neuraltrust.ai/vertex"),
            "gateway_api_key": os.getenv("NEURALTRUST_API_KEY"),
            "location":        None,
            "base_url":        None,
            "api_version":     None,
        }

    cfg = _parse_vertex_config()
    cfg["backend"] = "vertex"
    return cfg


def build_client(cfg: dict | None = None) -> genai.Client:
    """Instantiate a genai.Client from the resolved config."""
    if cfg is None:
        cfg = load_config()

    if cfg["backend"] == "gemini":
        return genai.Client(api_key=cfg["api_key"])

    if cfg["backend"] == "gateway":
        return genai.Client(
            vertexai=True,
            project=cfg["project"],
            http_options=types.HttpOptions(
                base_url=cfg["gateway_url"],
                headers={
                    "X-TG-API-Key": cfg["gateway_api_key"],
                    "Authorization": f"Bearer {_get_access_token()}",
                },
            ),
        )

    return genai.Client(
        vertexai=True,
        project=cfg["project"],
        location=cfg["location"],
        http_options=types.HttpOptions(
            base_url=cfg["base_url"],
            api_version=cfg["api_version"],
        ),
    )
