"""OMEGA v0.1 conversational core."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from modules.config import Settings
from modules.llm import ModelUnavailable, OllamaClient
from modules.memory import (
    ConversationMemory,
    VerifiedProfile,
    extract_personal_fact,
    extract_requested_key,
)
from modules.personality import SYSTEM_PROMPT

VERSION = "0.1.2"


def print_help() -> None:
    print("OMEGA: Commands: /help, /status, /clear, /remember <fact>, /memories, /forget-all, /exit")


def asks_for_full_profile(text: str) -> bool:
    normalized = " ".join(text.lower().replace("?", "").split())
    return normalized in {
        "what do you know about me",
        "tell me what you know about me",
        "tell me about me",
        "who am i",
    }


def print_verified_facts(profile: VerifiedProfile) -> None:
    if not profile.facts:
        print("OMEGA: I don't know anything verified about you yet.")
        return
    print("OMEGA: This is what I know for certain:")
    for key, value in profile.facts.items():
        print(f"  - {key}: {value}")


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
            fact_text = user_input[len("/remember "):].strip()
            extracted = extract_personal_fact(fact_text)
            if not extracted:
                print("OMEGA: Tell me in a form like 'my favorite color is green.'")
            elif profile.remember(*extracted):
                print(f"OMEGA: I'll remember your {extracted[0]} is {extracted[1]}.")
            else:
                print("OMEGA: I already had that saved.")
            continue
        if command == "/memories":
            print_verified_facts(profile)
            continue
        if command == "/forget-all":
            profile.clear()
            print("OMEGA: All verified personal facts deleted.")
            continue

        requested_key = extract_requested_key(user_input)
        if requested_key:
            value = profile.get(requested_key)
            if value is None:
                print("OMEGA: I don't know that yet.")
            else:
                print(f"OMEGA: Your {requested_key} is {value}.")
            continue
        if asks_for_full_profile(user_input):
            print_verified_facts(profile)
            continue

        extracted = extract_personal_fact(user_input)
        if extracted:
            changed = profile.remember(*extracted)
            if changed:
                print(f"OMEGA: Got it. Your {extracted[0]} is {extracted[1]}.")
            else:
                print("OMEGA: I remember.")
            memory.append("user", user_input)
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
