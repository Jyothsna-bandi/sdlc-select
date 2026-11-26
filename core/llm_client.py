"""Optional OpenAI-compatible API helper; never required for local operation."""

import json
import urllib.error
import urllib.request

from config.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def is_configured() -> bool:
    return bool(LLM_API_KEY)


def complete_json(system_prompt: str, user_prompt: str) -> dict:
    if not is_configured():
        raise RuntimeError("LLM mode is not configured. Set OPENAI_API_KEY to enable it.")
    body = json.dumps({
        "model": LLM_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{LLM_BASE_URL}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"LLM request failed: {error}") from error
    try:
        content = payload["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("LLM response did not contain valid JSON.") from error
    if not isinstance(result, dict):
        raise RuntimeError("LLM response must be a JSON object.")
    return result
