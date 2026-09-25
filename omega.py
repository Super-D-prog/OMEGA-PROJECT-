"""OMEGA v0.1 conversational core."""
from __future__ import annotations

import datetime as dt
import re
import subprocess
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
from modules.proactive import MorningBriefing
from modules.weather import WeatherUnavailable, parse_weather_request, weather_report

VERSION = "0.1.6"


def print_help() -> None:
    print("OMEGA: Commands: /help, /status, /briefing, /clear, /remember <fact>, /memories, /forget-all, /exit")


def is_casual_challenge(text: str) -> bool:
    return bool(re.search(
        r"\b(?:i can|i could|i will|i'll|i am going to|i'm going to|"
        r"im going to|i bet|bet you|definitely|you can't|you cannot|"
        r"i(?:'ll| will) beat)\b",
        text.lower(),
    ))


def asks_for_full_profile(text: str) -> bool:
    normalized = " ".join(text.lower().replace("?", "").split())
    return normalized in {
        "what do you know about me", "tell me what you know about me",
        "tell me about me", "who am i",
    }


def answer_clock_question(text: str, now: dt.datetime) -> str | None:
    normalized = " ".join(text.lower().strip(" .?!").split())
    if normalized in {"what time is it", "what's the time", "whats the time", "current time"}:
        return f"It is {now:%-I:%M %p %Z}."
    if normalized in {
        "what is today's date", "what's today's date", "whats todays date",
        "what date is it", "today's date", "todays date",
    }:
        return f"Today is {now:%A, %B} {now.day}, {now.year}."
    if normalized in {"what day is it", "what day is today"}:
        return f"Today is {now:%A}."
    if normalized in {"what year is it", "what is the current year", "current year"}:
        return f"It is {now.year}."
    return None


def parse_birthday(birthday: str) -> dt.date | None:
    for date_format in ("%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(birthday, date_format).date()
        except ValueError:
            pass
    return None


def calculate_age(birthday: str, today: dt.date) -> int | None:
    born = parse_birthday(birthday)
    if born is None:
        return None
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def asks_for_birthday_countdown(text: str) -> bool:
    normalized = " ".join(text.lower().strip(" .?!").split())
    return normalized in {
        "how many days until my birthday",
        "how long until my birthday",
        "when is my next birthday",
    }


def birthday_countdown(birthday: str, today: dt.date) -> tuple[int, dt.date] | None:
    born = parse_birthday(birthday)
    if born is None:
        return None
    try:
        next_birthday = dt.date(today.year, born.month, born.day)
    except ValueError:
        next_birthday = dt.date(today.year, 2, 28)
    if next_birthday < today:
        try:
            next_birthday = dt.date(today.year + 1, born.month, born.day)
        except ValueError:
            next_birthday = dt.date(today.year + 1, 2, 28)
    return (next_birthday - today).days, next_birthday


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

    def announce(message: str) -> None:
        print(f"\nOMEGA: {message}\n")
        if settings.speak_briefings:
            try:
                subprocess.Popen(
                    ["/usr/bin/say", message],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError:
                pass

    briefing = MorningBriefing(
        state_path=data_dir / "proactive.json",
        location=settings.home_location,
        briefing_time=settings.morning_briefing_time,
        announce=announce,
    )

    print(f"OMEGA ONLINE — Version {VERSION}")
    print(f"Local model: {settings.model}")
    print_help()
    if settings.proactive_enabled:
        briefing.start()

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
                f"{len(profile.facts)} verified facts loaded; "
                f"morning briefing {'enabled' if settings.proactive_enabled else 'disabled'} "
                f"for {settings.morning_briefing_time}."
            )
            continue
        if command == "/briefing":
            briefing.run_now()
            continue
        if command == "/clear":
            memory.clear()
            print("OMEGA: Conversation history cleared. Verified facts were kept.")
            continue
        if command.startswith("/remember "):
            fact_text = user_input[len("/remember "):].strip()
            extracted = extract_personal_fact(fact_text)
            if not extracted:
                print("OMEGA: Tell me in a form like 'my favorite color is green' or 'I was born on July 24, 2007.'")
            elif profile.remember(*extracted):
                print(f"OMEGA: I'll remember your {extracted[0]} is {profile.get(extracted[0])}.")
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

        now = dt.datetime.now().astimezone()
        clock_answer = answer_clock_question(user_input, now)
        if clock_answer:
            print(f"OMEGA: {clock_answer}")
            continue

        weather_request = parse_weather_request(user_input, settings.home_location)
        if weather_request:
            try:
                report = weather_report(weather_request)
                print(f"OMEGA: {report}")
            except WeatherUnavailable as exc:
                print(f"OMEGA: {exc}")
            continue

        if asks_for_birthday_countdown(user_input):
            birthday = profile.get("birthday")
            result = birthday_countdown(birthday, now.date()) if birthday else None
            if result is None:
                print("OMEGA: I don't know your birthday yet.")
            else:
                days, next_birthday = result
                if days == 0:
                    print("OMEGA: Your birthday is today.")
                else:
                    print(
                        f"OMEGA: Your next birthday is {next_birthday:%B} "
                        f"{next_birthday.day}, {next_birthday.year} — {days} days away."
                    )
            continue

        requested_key = extract_requested_key(user_input)
        if requested_key:
            if requested_key == "age":
                birthday = profile.get("birthday")
                age = calculate_age(birthday, now.date()) if birthday else None
                print(f"OMEGA: You are {age} years old." if age is not None else "OMEGA: I don't know that yet.")
                continue
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
                print(f"OMEGA: Got it. Your {extracted[0]} is {profile.get(extracted[0])}.")
            else:
                print("OMEGA: I remember.")
            memory.append("user", user_input)
            continue

        runtime_context = (
            f"CURRENT LOCAL DATE AND TIME: {now:%A, %B} {now.day}, {now.year}, "
            f"{now:%-I:%M:%S %p %Z}. Treat this as authoritative."
        )
        intent_context = ""
        if is_casual_challenge(user_input):
            intent_context = (
                "CURRENT MESSAGE TYPE: casual boast, prediction, or challenge. "
                "Respond with fresh competitive banter. Do not treat it as a factual "
                "memory question, do not say you lack information, and do not become "
                "a motivational coach."
            )
        system_content = (
            f"{SYSTEM_PROMPT}\n\n{runtime_context}\n\n"
            f"{profile.prompt_context()}\n\n{intent_context}"
        )
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

    briefing.stop()


if __name__ == "__main__":
    main()
