# src/agents/utils/llm_client.py
"""
Thin wrapper around the Gemini (google-genai) API.

All builder modules call this instead of importing google.genai directly.
If you switch to Claude, OpenAI, or a local model later, only this file
needs to change.
"""

import json
from google import genai
from google.genai import types


def call_llm(
    api_key: str,
    system_instruction: str,
    user_prompt: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Send a text-only prompt to the LLM and parse the JSON response.

    Args:
        api_key: API key for authentication.
        system_instruction: System-level instructions for the model.
        user_prompt: The user-facing prompt with clinical data.
        model: Model identifier (default: gemini-2.5-flash).

    Returns:
        Parsed JSON dict from the LLM response.

    Raises:
        ValueError: If the LLM response is not valid JSON.
        Exception: Propagated from the API client for network / quota errors.
    """
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
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON. "
            f"First 500 chars: {raw_text[:500]!r}"
        ) from e
