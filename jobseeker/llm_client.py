"""LLM backend dispatch: Anthropic's Claude API, or a free local model via
Ollama (auto-selected when no ANTHROPIC_API_KEY is set - see config.LLM_BACKEND).
Both paths expose the same call()/call_json() interface so the rest of the
app never needs to know which one is active.
"""
import json
import re
import urllib.error
import urllib.request
from typing import Any

from . import config

_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic

        _anthropic_client = anthropic.Anthropic(api_key=config.require_api_key())
    return _anthropic_client


def _call_anthropic(system: str, user: str, max_tokens: int, temperature: float) -> str:
    client = _get_anthropic_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_ollama(system: str, user: str, max_tokens: int, temperature: float) -> str:
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    req = urllib.request.Request(
        f"{config.OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach Ollama at {config.OLLAMA_HOST} ({exc}). "
            "Make sure Ollama is running (`ollama serve`) and the model is pulled "
            f"(`ollama pull {config.OLLAMA_MODEL}`), or set ANTHROPIC_API_KEY in .env instead."
        )
    return body.get("message", {}).get("content", "")


def call(system: str, user: str, max_tokens: int = 4096, temperature: float = 0.4) -> str:
    if config.LLM_BACKEND == "ollama":
        return _call_ollama(system, user, max_tokens, temperature)
    return _call_anthropic(system, user, max_tokens, temperature)


def call_json(system: str, user: str, max_tokens: int = 4096, temperature: float = 0.3) -> Any:
    """Call the active LLM and parse a JSON object/array out of the reply, tolerating
    stray prose or markdown code fences around the JSON payload."""
    strict_system = (
        system
        + "\n\nRespond with ONLY valid JSON. No markdown fences, no commentary before or after."
    )
    text = call(strict_system, user, max_tokens=max_tokens, temperature=temperature)
    return _extract_json(text)


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        # strict=False tolerates raw control characters (e.g. a literal newline)
        # inside string values - a common local-model mistake instead of \n.
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        pass
    start_candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not start_candidates:
        raise ValueError(f"Could not find JSON in the model's response: {text[:500]}")
    start = min(start_candidates)
    end_char = "}" if text[start] == "{" else "]"
    end = text.rfind(end_char)
    if end == -1:
        raise ValueError(f"Could not find JSON in the model's response: {text[:500]}")
    return json.loads(text[start : end + 1], strict=False)
