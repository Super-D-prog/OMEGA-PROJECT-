"""Local language-model provider using Ollama's HTTP API."""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailable(RuntimeError):
    """Raised when the configured model service cannot produce a response."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "stop": ["\nDarihan:", "\nYou:", "\nUser:", "\nOMEGA:"]
            },
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result: dict[str, Any] = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ModelUnavailable(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise ModelUnavailable(
                "OMEGA cannot reach Ollama. Make sure Ollama is installed and running."
            ) from exc
        try:
            content = result["message"]["content"].strip()
            content = re.sub(
                r'^(?:["\']?\s*OMEGA\s*:\s*)+',
                "",
                content,
                flags=re.I,
            )
            cut_points = [
                position for marker in ("\nDarihan:", "\nYou:", "\nUser:", "\nOMEGA:")
                if (position := content.find(marker)) >= 0
            ]
            if cut_points:
                content = content[:min(cut_points)].rstrip()
            if len(content) >= 2 and content[0] == content[-1] and content[0] in {'"', "'"}:
                content = content[1:-1].strip()
        except (KeyError, TypeError, AttributeError) as exc:
            raise ModelUnavailable("Ollama returned an unexpected response.") from exc
        if not content:
            raise ModelUnavailable("The model returned an empty response.")
        return content
