"""
ai/llm.py
---------
Thin wrapper around an external LLM API (OpenAI-compatible schema, which
also works with many hosted Mistral/LLaMA endpoints).

Key design goal: NEVER crash the application because the LLM is
unavailable. If Config.DEMO_MODE is True, or if the live API call fails
for any reason (missing key, network error, bad response), we fall back
to the structured Demo Mode template response.
"""

import requests
from config import Config
from ai.prompts import SYSTEM_PROMPT, build_chat_prompt, demo_chat_response


class LLMError(Exception):
    """Raised internally when the live LLM call fails; always caught."""
    pass


def _call_openai_compatible_api(prompt: str) -> str:
    """
    Calls an OpenAI-compatible /chat/completions endpoint.
    Works with OpenAI itself, and with many providers (incl. Groq,
    Mistral, LLaMA) that mirror the same request schema.
    """
    api_key = str(Config.LLM_API_KEY).strip().strip('"').strip("'")
    api_base = str(Config.LLM_API_BASE).strip().strip('"').strip("'")
    model = str(Config.LLM_MODEL).strip().strip('"').strip("'")

    if not api_base:
        api_base = "https://api.groq.com/openai/v1" if api_key.startswith("gsk_") else "https://api.openai.com/v1"
    if not model or model.startswith("gsk_") or len(model) > 30:
        model = "openai/gpt-oss-120b"

    url = f"{api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 800,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        # If the configured model failed on Groq, fallback to known working openai/gpt-oss-120b
        if "groq.com" in api_base and model != "openai/gpt-oss-120b":
            try:
                payload["model"] = "openai/gpt-oss-120b"
                resp = requests.post(url, headers=headers, json=payload, timeout=25)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                pass
        raise LLMError(f"LLM API call failed: {exc}")


def generate_business_response(user_query: str, intent: str, context: str) -> dict:
    """
    Main entry point used by routes/chatbot.py.

    Returns:
        {
            "response": str,      # the final text to show the user
            "mode": "live" | "demo",
        }
    """
    if Config.DEMO_MODE:
        return {
            "response": f"[Config.DEMO_MODE is True | provider={Config.LLM_PROVIDER} | has_key={bool(Config.LLM_API_KEY)}]\n\n" + demo_chat_response(user_query, intent, context),
            "mode": "demo",
        }

    prompt = build_chat_prompt(user_query, intent, context)
    try:
        text = _call_openai_compatible_api(prompt)
        return {"response": text, "mode": "live"}
    except LLMError as exc:
        # Fail gracefully -> demo fallback, app never crashes
        return {
            "response": f"[API Error: {exc} | url={Config.LLM_API_BASE} | model={Config.LLM_MODEL} | key={Config.LLM_API_KEY[:6] if Config.LLM_API_KEY else 'none'}...]\n\n" + demo_chat_response(user_query, intent, context),
            "mode": "demo-fallback",
        }


def generate_raw_completion(prompt: str) -> dict:
    """
    Generic helper for other features (business plan / market analysis) that
    want free-form LLM text. Falls back to None on failure/demo mode so the
    caller can use its own template fallback.
    """
    if Config.DEMO_MODE:
        return {"response": None, "mode": "demo"}
    try:
        text = _call_openai_compatible_api(prompt)
        return {"response": text, "mode": "live"}
    except LLMError:
        return {"response": None, "mode": "demo-fallback"}
