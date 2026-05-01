"""
OpenAI Chat Completions 
Model: OPENAI_MODEL (defaults to gpt-5.4-mini when unset).
"""
import json
import os

from openai import OpenAI


def resolve_api_key():
    # Prefer standard name; support OPEN_AI_API_KEY from .env spelling.
    raw = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY") or ""
    return raw.strip().strip('"').strip("'")


def resolve_model():
    # User-facing default matches GPT-5.4 mini; override with OPENAI_MODEL if OpenAI uses a different id.
    return (os.getenv("OPENAI_MODEL") or "gpt-5.4-mini").strip()


def chat_completion(user_message, system_prompt, finance_context_obj):
    # Sends system + serialized finance JSON + user text; returns assistant string or raises.
    key = resolve_api_key()
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY or OPEN_AI_API_KEY in .env")
    payload = json.dumps(finance_context_obj, default=str)
    if len(payload) > 120000:
        payload = payload[:120000] + "\n...truncated..."
    client = OpenAI(api_key=key)
    model = resolve_model()
    messages = [
        {
            "role": "system",
            "content": system_prompt + "\n\nFINANCE_CONTEXT_JSON:\n" + payload,
        },
        {"role": "user", "content": user_message},
    ]
    response = client.chat.completions.create(model=model, messages=messages)
    choice = response.choices[0].message
    return (choice.content or "").strip()


def chat_completion_stream(user_message, system_prompt, finance_context_obj):
    """Yields text fragments from OpenAI chat completions (stream=True)."""
    key = resolve_api_key()
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY or OPEN_AI_API_KEY in .env")
    payload = json.dumps(finance_context_obj, default=str)
    if len(payload) > 120000:
        payload = payload[:120000] + "\n...truncated..."
    client = OpenAI(api_key=key)
    model = resolve_model()
    messages = [
        {
            "role": "system",
            "content": system_prompt + "\n\nFINANCE_CONTEXT_JSON:\n" + payload,
        },
        {"role": "user", "content": user_message},
    ]
    stream = client.chat.completions.create(model=model, messages=messages, stream=True)
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
