"""Provider-agnostic JSON-mode LLM calls (OpenAI or Anthropic)."""
import json
import re

import httpx

from .store import get_setting


def provider() -> str | None:
    if get_setting("OPENAI_API_KEY"):
        return "openai"
    if get_setting("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def _extract_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=0)
    return json.loads(text[start:])


def _check(r: httpx.Response):
    if r.is_success:
        return
    try:
        err = r.json().get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else str(err)
    except ValueError:
        msg = r.text[:200]
    raise RuntimeError(f"{r.status_code} from {r.url.host}: {msg or r.reason_phrase}")


async def complete_json(system: str, user: str, max_tokens: int = 4000):
    p = provider()
    if p == "openai":
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {get_setting('OPENAI_API_KEY')}"},
                json={
                    "model": get_setting("OPENAI_MODEL") or "gpt-4o",
                    "response_format": {"type": "json_object"},
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                },
            )
            _check(r)
            return _extract_json(r.json()["choices"][0]["message"]["content"])
    if p == "anthropic":
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": get_setting("ANTHROPIC_API_KEY"),
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": get_setting("ANTHROPIC_MODEL") or "claude-sonnet-4-5",
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                    "system": system + "\nRespond with a single valid JSON object only.",
                    "messages": [{"role": "user", "content": user}],
                },
            )
            _check(r)
            return _extract_json("".join(b.get("text", "") for b in r.json()["content"]))
    raise RuntimeError("No LLM provider configured")
