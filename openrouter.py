"""OpenRouter Chat Completions API client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from product_cards import product_prompt


API_URL = "https://openrouter.ai/api/v1/chat/completions"


class ApiError(RuntimeError):
    """Raised when the OpenRouter request or response fails."""


def generate_product_card(
    source: dict[str, Any],
    *,
    api_key: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    if not api_key:
        raise ApiError("Не задан OPENROUTER_API_KEY.")
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты аккуратный технический B2B-копирайтер. Не выдумывай факты.",
                },
                {"role": "user", "content": product_prompt(source)},
            ],
            "response_format": {"type": "json_object"},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "B2B Product Card Draft Generator",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        result = json.loads(content)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise ApiError(f"OpenRouter вернул HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Не удалось подключиться к OpenRouter: {exc.reason}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ApiError(f"Некорректный ответ OpenRouter: {exc}") from exc
    if not isinstance(result, dict):
        raise ApiError("Ответ модели должен быть JSON-объектом.")
    return result
