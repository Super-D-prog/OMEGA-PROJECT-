"""OMEGA v0.1 conversational core."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from modules.config import Settings
from modules.llm import ModelUnavailable, OllamaClient
from modules.memory import ConversationMemory, VerifiedProfile
from modules.personality import SYSTEM_PROMPT

VERSION = "0.1.1"


def print_help() -> None:
    print("OMEGA: Commands: /help, /status, /clear, /remember <fact>, /memories, /forget-all, /exit")


def asks_about_user_knowledge(text: str) -> bool:
    normalized = " ".join(text.lower().replace("?", "").split())
    exact = {
        "what do you know about me",
        "tell me what you know about me",
        "tell me about me",
        "who am i",
    }
    personal_starts = (
        "what is my ", "what's my ", "whats my ", "do you know my ",
        "when is my ", "where is my ", "who is my ", "how old am i",
    )
    return normalized in exact or normalized.startswith(personal_starts)


def print_verified_facts(profile: VerifiedProfile) -> None:
    if not profile.facts:
        print("OMEGA: I don't know anything verified about you yet.")
        return
    print("OMEGA: This is what you've explicitly asked me to remember:")
    for fact in profile.facts:
        print(f"  - {fact}")


def main() -> None:
    settings = Settings()
    data_dir = Path(settings.data_dir)
    memory = ConversationMemory(data_dir / "conversation.json", settings.history_limit)
    profile = VerifiedProfile(data_dir / "profile.json")
    memory.load()
    profile.load()
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
            print("OMEGA: Powering down.")
            break
        if command == "/help":
            print_help()
            continue
        if command == "/status":
            now = dt.datetime.now().astimezone()
            print(
                f"OMEGA: Online. Model {settings.model}; "
                f"local time {now:%Y-%m-%d %H:%M:%S %Z}; "
                f"{len(memory.messages)} recent messages and "
                f"{len(profile.facts)} verified facts loaded."
            )
            continue
        if command == "/clear":
            memory.clear()
            print("OMEGA: Conversation history cleared. Verified facts were kept.")
            continue
        if command.startswith("/remember "):
            fact = user_input[len("/remember "):].strip()
            if profile.remember(fact):
                print("OMEGA: Saved as a verified fact.")
            else:
                print("OMEGA: Nothing new to save.")
            continue
        if command == "/memories":
            print_verified_facts(profile)
            continue
        if command == "/forget-all":
            profile.clear()
            print("OMEGA: All verified personal facts deleted.")
            continue
        if asks_about_user_knowledge(user_input):
            print_verified_facts(profile)
            continue

        system_content = f"{SYSTEM_PROMPT}\n\n{profile.prompt_context()}"
        messages = [{"role": "system", "content": system_content}, *memory.messages]
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
