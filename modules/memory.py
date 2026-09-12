"""Small, transparent conversation store for OMEGA v0.1."""
from __future__ import annotations

import json
from pathlib import Path


class ConversationMemory:
    def __init__(self, path: Path, limit: int = 20) -> None:
        self.path = path
        self.limit = max(2, limit)
        self.messages: list[dict[str, str]] = []

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.messages = [
                    item for item in data
                    if isinstance(item, dict)
                    and item.get("role") in {"user", "assistant"}
                    and isinstance(item.get("content"), str)
                ][-self.limit:]
        except (OSError, json.JSONDecodeError):
            self.messages = []

    def append(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Unsupported conversation role")
        self.messages.append({"role": role, "content": content})
        self.messages = self.messages[-self.limit:]
        self.save()

    def clear(self) -> None:
        self.messages = []
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.messages, indent=2), encoding="utf-8")
        temporary.replace(self.path)
