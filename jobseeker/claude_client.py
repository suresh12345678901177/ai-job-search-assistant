import json
import re
from typing import Any

import anthropic

from . import config

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.require_api_key())
    return _client


def call(system: str, user: str, max_tokens: int = 4096, temperature: float = 0.4) -> str:
    client = get_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def call_json(system: str, user: str, max_tokens: int = 4096, temperature: float = 0.3) -> Any:
    """Call Claude and parse a JSON object/array out of the reply, tolerating
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
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start_candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not start_candidates:
        raise ValueError(f"Could not find JSON in Claude response: {text[:500]}")
    start = min(start_candidates)
    end_char = "}" if text[start] == "{" else "]"
    end = text.rfind(end_char)
    if end == -1:
        raise ValueError(f"Could not find JSON in Claude response: {text[:500]}")
    return json.loads(text[start : end + 1])
