# src/agents/utils/llm_client.py
"""
Thin wrapper around the LLM API.

- By default uses Gemini (google-genai) as before.
- If an environment variable ``LLM_API`` is present, the wrapper switches to the OpenRouter API.
  The model can be overridden with ``LLM_MODEL`` or via the ``model`` argument.

All builder modules import ``call_llm`` so the change is transparent to the rest of the code.
"""

import os
import json

# Optional: the Gemini client is only needed when the OpenRouter key is not set.
# Import lazily so the package does not fail on systems without google‑genai installed.
try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None
    types = None

import requests


def _call_gemini(
    api_key: str,
    system_instruction: str,
    user_prompt: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """Internal Gemini call – unchanged from the original implementation."""
    if genai is None:
        raise RuntimeError("Google genai library not available. Install it or provide LLM_API for OpenRouter.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=[user_prompt],
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()

    # Strip markdown code fences if the model wraps JSON in them
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # Remove any fence lines (``` or ```json)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON. First 500 chars: {raw_text[:500]!r}"
        ) from e


def _call_openrouter(
    api_key: str,
    system_instruction: str,
    user_prompt: str,
    model: str = "meta-llama/llama-3.1-8b-instruct",
) -> dict:
    """Call the OpenRouter API and request a JSON‑object response.

    The OpenRouter endpoint expects a ``messages`` list with ``system`` and ``user`` roles.
    We ask for ``response_format`` ``json_object`` so the model is encouraged to emit pure JSON.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # OpenRouter returns the content in choices[0].message.content
    content = data["choices"][0]["message"]["content"].strip()

    # In case the model still wraps JSON in fences, strip them
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"OpenRouter returned invalid JSON. First 500 chars: {content[:500]!r}"
        ) from e


def call_llm(
    api_key: str,
    system_instruction: str,
    user_prompt: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """Unified entry point used by all builders.

    If the environment variable ``LLM_API`` is set, the call is routed to OpenRouter.
    Otherwise we fall back to the original Gemini implementation.
    """
    # ``LLM_API`` is the OpenRouter key. ``LLM_MODEL`` can override the default model.
    openrouter_key = os.getenv("LLM_API")
    if openrouter_key:
        # Allow the caller to specify a model name, otherwise read from LLM_MODEL or use default.
        openrouter_model = os.getenv("LLM_MODEL", model)
        return _call_openrouter(
            api_key=openrouter_key,
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            model=openrouter_model,
        )
    else:
        # Use Gemini – the ``api_key`` argument is expected to be the Gemini key.
        return _call_gemini(
            api_key=api_key,
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            model=model,
        )
