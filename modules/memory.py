"""Transparent conversation and verified-profile storage for OMEGA."""
from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


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
        _write_json(self.path, self.messages)


class VerifiedProfile:
    """Facts the user explicitly asked OMEGA to remember."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.facts: list[str] = []

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.facts = [item.strip() for item in data if isinstance(item, str) and item.strip()]
        except (OSError, json.JSONDecodeError):
            self.facts = []

    def remember(self, fact: str) -> bool:
        clean = fact.strip()
        if not clean or clean in self.facts:
            return False
        self.facts.append(clean)
        self.save()
        return True

    def clear(self) -> None:
        self.facts = []
        self.save()

    def save(self) -> None:
        _write_json(self.path, self.facts)

    def prompt_context(self) -> str:
        if not self.facts:
            return "VERIFIED USER FACTS: none."
        lines = "\n".join(f"- {fact}" for fact in self.facts)
        return f"VERIFIED USER FACTS (the only personal facts you may claim):\n{lines}"
