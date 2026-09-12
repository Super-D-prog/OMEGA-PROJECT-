"""OMEGA v0.1 conversational core."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from modules.config import Settings
from modules.llm import ModelUnavailable, OllamaClient
from modules.memory import ConversationMemory
from modules.personality import SYSTEM_PROMPT

VERSION = "0.1.0"


def print_help() -> None:
    print("OMEGA: Commands: /help, /status, /clear, /exit")


def main() -> None:
    settings = Settings()
    memory_path = Path(settings.data_dir) / "conversation.json"
    memory = ConversationMemory(memory_path, settings.history_limit)
    memory.load()
    model = OllamaClient(settings.ollama_url, settings.model, settings.request_timeout)

    print(f"OMEGA ONLINE — Version {VERSION}")
    print(f"Local model: {settings.model}")
    print_help()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nOMEGA: Powering down cleanly.")
            break

        if not user_input:
            continue

        command = user_input.lower()
        if command in {"/exit", "exit", "quit"}:
            print("OMEGA: Powering down. Try not to cause an existential crisis without me.")
            break
        if command == "/help":
            print_help()
            continue
        if command == "/status":
            now = dt.datetime.now().astimezone()
            print(
                f"OMEGA: Online. Model {settings.model}; "
                f"local time {now:%Y-%m-%d %H:%M:%S %Z}; "
                f"{len(memory.messages)} recent messages loaded."
            )
            continue
        if command == "/clear":
            memory.clear()
            print("OMEGA: Conversation history cleared.")
            continue

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *memory.messages]
        messages.append({"role": "user", "content": user_input})
        try:
            answer = model.chat(messages)
        except ModelUnavailable as exc:
            print(f"OMEGA: {exc}")
            continue

        print(f"OMEGA: {answer}")
        memory.append("user", user_input)
        memory.append("assistant", answer)


if __name__ == "__main__":
    main()
