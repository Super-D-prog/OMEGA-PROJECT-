"""Transparent conversation and structured verified-profile storage."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def normalize_key(key: str) -> str:
    clean = " ".join(key.lower().strip(" .?!").split())
    return clean.replace("colour", "color")


def extract_personal_fact(text: str) -> tuple[str, str] | None:
    """Extract conservative first-person facts without asking the model to guess."""
    clean = " ".join(text.strip().split()).rstrip(".")
    clean = re.sub(r"^(?:please\s+)?remember(?:\s+that)?\s+", "", clean, flags=re.I)
    patterns = (
        (r"^my favorite ([a-z][a-z ]{0,40}) is (.+)$", lambda m: (f"favorite {m.group(1)}", m.group(2))),
        (r"^my ([a-z][a-z ]{0,40}) is (.+)$", lambda m: (m.group(1), m.group(2))),
        (r"^i am studying (.+)$", lambda m: ("major", m.group(1))),
        (r"^i study (.+)$", lambda m: ("major", m.group(1))),
        (r"^i live in (.+)$", lambda m: ("location", m.group(1))),
    )
    for pattern, builder in patterns:
        match = re.match(pattern, clean, flags=re.I)
        if match:
            key, value = builder(match)
            key = normalize_key(key)
            value = value.strip(" .?!")
            if key and value:
                return key, value
    return None


def extract_requested_key(text: str) -> str | None:
    clean = " ".join(text.lower().strip(" .?!").split())
    patterns = (
        r"^(?:what is|what's|whats) my (.+)$",
        r"^do you know my (.+)$",
        r"^(?:when|where|who) is my (.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, clean)
        if match:
            return normalize_key(match.group(1))
    if clean == "how old am i":
        return "age"
    return None


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
    """Separate verified values instead of blending all user facts together."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.facts: dict[str, str] = {}

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.facts = {
                    normalize_key(str(key)): str(value).strip()
                    for key, value in data.items() if str(value).strip()
                }
            elif isinstance(data, list):
                # Migrate the original list-based profile automatically.
                for item in data:
                    if not isinstance(item, str):
                        continue
                    extracted = extract_personal_fact(item)
                    if extracted:
                        self.facts[extracted[0]] = extracted[1]
                self.save()
        except (OSError, json.JSONDecodeError):
            self.facts = {}

    def remember(self, key: str, value: str) -> bool:
        clean_key = normalize_key(key)
        clean_value = value.strip(" .?!")
        if not clean_key or not clean_value:
            return False
        changed = self.facts.get(clean_key) != clean_value
        self.facts[clean_key] = clean_value
        self.save()
        return changed

    def get(self, key: str) -> str | None:
        return self.facts.get(normalize_key(key))

    def clear(self) -> None:
        self.facts = {}
        self.save()

    def save(self) -> None:
        _write_json(self.path, self.facts)

    def prompt_context(self) -> str:
        if not self.facts:
            return "VERIFIED USER FACTS: none."
        lines = "\n".join(f"- {key}: {value}" for key, value in self.facts.items())
        return f"VERIFIED USER FACTS (the only personal facts you may claim):\n{lines}"
