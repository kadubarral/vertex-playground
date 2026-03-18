"""
Vertex AI Playground — sample application using the Google Gen AI Python SDK.

Demonstrates:
  1. Basic text generation
  2. Streaming text generation
  3. Structured JSON output (Pydantic schema)
  4. System instructions & config tuning
  5. Multi-turn chat
  6. Function calling (automatic)
  7. Embeddings
  8. Token counting
"""

import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from genai_config import load_config, build_client

load_dotenv()

_cfg = load_config()
MODEL = _cfg["model"]


def get_client() -> genai.Client:
    return build_client(_cfg)


# ---------------------------------------------------------------------------
# 1. Basic text generation
# ---------------------------------------------------------------------------
def demo_basic_generation(client: genai.Client):
    print("\n=== 1. Basic Text Generation ===\n")
    response = client.models.generate_content(
        model=MODEL,
        contents="Explain quantum computing in three sentences.",
    )
    print(response.text)


# ---------------------------------------------------------------------------
# 2. Streaming text generation
# ---------------------------------------------------------------------------
def demo_streaming(client: genai.Client):
    print("\n=== 2. Streaming Text Generation ===\n")
    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents="Write a haiku about distributed systems.",
    ):
        print(chunk.text, end="", flush=True)
    print()


# ---------------------------------------------------------------------------
# 3. Structured JSON output with a Pydantic model
# ---------------------------------------------------------------------------
class CityInfo(BaseModel):
    name: str
    country: str
    population: int
    famous_landmark: str
    short_description: str


def demo_json_output(client: genai.Client):
    print("\n=== 3. Structured JSON Output ===\n")
    response = client.models.generate_content(
        model=MODEL,
        contents="Give me information about Tokyo.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=CityInfo.model_json_schema(),
        ),
    )
    parsed = json.loads(response.text)
    print(json.dumps(parsed, indent=2))


# ---------------------------------------------------------------------------
# 4. System instructions & config tuning
# ---------------------------------------------------------------------------
def demo_system_instructions(client: genai.Client):
    print("\n=== 4. System Instructions & Config ===\n")
    response = client.models.generate_content(
        model=MODEL,
        contents="Tell me about Python.",
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a grumpy senior engineer who answers everything "
                "with reluctant sarcasm but still gives accurate information."
            ),
            temperature=0.9,
            max_output_tokens=256,
        ),
    )
    print(response.text)


# ---------------------------------------------------------------------------
# 5. Multi-turn chat
# ---------------------------------------------------------------------------
def demo_chat(client: genai.Client):
    print("\n=== 5. Multi-Turn Chat ===\n")
    chat = client.chats.create(model=MODEL)

    messages = [
        "Hi! I'm building a REST API in Python. Which framework should I use?",
        "Can you compare FastAPI and Flask in a table?",
        "Which one would you recommend for a high-throughput async service?",
    ]

    for msg in messages:
        print(f"User: {msg}")
        response = chat.send_message(msg)
        print(f"Model: {response.text}\n")


# ---------------------------------------------------------------------------
# 6. Function calling (automatic)
# ---------------------------------------------------------------------------
def get_current_weather(location: str) -> str:
    """Returns the current weather for a location.

    Args:
        location: The city and state, e.g. San Francisco, CA
    """
    weather_data = {
        "San Francisco, CA": "Foggy, 58°F",
        "New York, NY": "Sunny, 72°F",
        "London, UK": "Rainy, 55°F",
    }
    return weather_data.get(location, f"No data available for {location}")


def demo_function_calling(client: genai.Client):
    print("\n=== 6. Function Calling (Automatic) ===\n")
    response = client.models.generate_content(
        model=MODEL,
        contents="What's the weather like in San Francisco, CA and London, UK?",
        config=types.GenerateContentConfig(
            tools=[get_current_weather],
        ),
    )
    print(response.text)


# ---------------------------------------------------------------------------
# 7. Embeddings
# ---------------------------------------------------------------------------
def demo_embeddings(client: genai.Client):
    print("\n=== 7. Embeddings ===\n")
    texts = [
        "Machine learning is a subset of artificial intelligence.",
        "I love eating pizza on Friday nights.",
        "Neural networks are inspired by the human brain.",
    ]
    response = client.models.embed_content(
        model="text-embedding-005",
        contents=texts,
    )
    for i, emb in enumerate(response.embeddings):
        preview = emb.values[:5]
        print(f"  Text {i+1}: dims={len(emb.values)}, first 5={preview}")


# ---------------------------------------------------------------------------
# 8. Token counting
# ---------------------------------------------------------------------------
def demo_token_count(client: genai.Client):
    print("\n=== 8. Token Counting ===\n")
    prompt = "Explain the theory of relativity in simple terms."
    response = client.models.count_tokens(model=MODEL, contents=prompt)
    print(f"  Prompt: \"{prompt}\"")
    print(f"  Token count: {response.total_tokens}")


# ---------------------------------------------------------------------------
# 9. Interactive chat (free-form Q&A)
# ---------------------------------------------------------------------------
def demo_interactive_chat(client: genai.Client):
    print("\n=== Interactive Chat ===")
    print("Type your questions freely. The model remembers the conversation.")
    print("Commands:  /new  — start a fresh conversation")
    print("           /exit — return to the main menu\n")

    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a helpful, concise assistant. "
                "Answer clearly and ask for clarification when needed."
            ),
        ),
    )

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() == "/exit":
            break
        if user_input.lower() == "/new":
            chat = client.chats.create(
                model=MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a helpful, concise assistant. "
                        "Answer clearly and ask for clarification when needed."
                    ),
                ),
            )
            print("-- new conversation started --\n")
            continue

        print("Model: ", end="", flush=True)
        for chunk in chat.send_message_stream(user_input):
            print(chunk.text, end="", flush=True)
        print("\n")


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------
DEMOS = {
    "1": ("Basic text generation", demo_basic_generation),
    "2": ("Streaming text generation", demo_streaming),
    "3": ("Structured JSON output", demo_json_output),
    "4": ("System instructions & config", demo_system_instructions),
    "5": ("Multi-turn chat (scripted)", demo_chat),
    "6": ("Function calling (automatic)", demo_function_calling),
    "7": ("Embeddings", demo_embeddings),
    "8": ("Token counting", demo_token_count),
    "9": ("Interactive chat", demo_interactive_chat),
    "all": ("Run all demos (excludes chat)", None),
}


def main():
    if not PROJECT:
        print("ERROR: GOOGLE_CLOUD_PROJECT is not set.")
        print("Copy .env.example to .env and fill in your project details.")
        return

    client = get_client()

    print("Gemini Playground")
    print(f"  Backend:  {_cfg['backend'].upper()}")
    if _cfg["backend"] == "vertex":
        print(f"  Project:  {_cfg['project']}")
        print(f"  Location: {_cfg['location']}")
    print(f"  Model:    {MODEL}")
    print()

    for key, (label, _) in DEMOS.items():
        print(f"  [{key}] {label}")
    print(f"  [q] Quit")
    print()

    while True:
        choice = input("Select a demo (1-9, all, q): ").strip().lower()

        if choice == "q":
            print("Bye!")
            break
        elif choice == "all":
            for key, (_, fn) in DEMOS.items():
                if fn is not None and key != "9":
                    fn(client)
        elif choice in DEMOS and DEMOS[choice][1] is not None:
            DEMOS[choice][1](client)
        else:
            print("Invalid choice. Try again.")

    client.close()


if __name__ == "__main__":
    main()
