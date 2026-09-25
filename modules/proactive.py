"""Clock-driven, permission-scoped proactive behavior for OMEGA."""
from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path
from typing import Callable

from modules.weather import WeatherRequest, WeatherUnavailable, weather_report


class MorningBriefing:
    """Announce one morning briefing per local calendar day while OMEGA is running."""

    def __init__(
        self,
        state_path: Path,
        location: str,
        briefing_time: str,
        announce: Callable[[str], None],
    ) -> None:
        self.state_path = state_path
        self.location = location
        self.hour, self.minute = self._parse_time(briefing_time)
        self.announce = announce
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_date = self._load_last_date()

    @staticmethod
    def _parse_time(value: str) -> tuple[int, int]:
        try:
            parsed = dt.datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("OMEGA_BRIEFING_TIME must use 24-hour HH:MM format.") from exc
        return parsed.hour, parsed.minute

    def _load_last_date(self) -> str | None:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            value = payload.get("last_morning_briefing")
            return value if isinstance(value, str) else None
        except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError):
            return None

    def _save_last_date(self, date_value: str) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"last_morning_briefing": date_value}, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.state_path)
        self._last_date = date_value

    def _is_due(self, now: dt.datetime) -> bool:
        today = now.date().isoformat()
        scheduled = now.replace(
            hour=self.hour,
            minute=self.minute,
            second=0,
            microsecond=0,
        )
        # A briefing is useful in the morning, not when OMEGA is first opened at night.
        return self._last_date != today and scheduled <= now < scheduled + dt.timedelta(hours=3)

    def build(self, now: dt.datetime | None = None) -> str:
        now = now or dt.datetime.now().astimezone()
        opening = f"Good morning. It's {now:%A, %B} {now.day} at {now:%-I:%M %p}."
        try:
            weather = weather_report(WeatherRequest(location=self.location))
        except WeatherUnavailable:
            weather = "I couldn't reach the weather service, so apparently the sky is keeping secrets."
        return f"{opening} {weather}"

    def run_now(self) -> str:
        """Build and announce a briefing without changing the daily schedule state."""
        message = self.build()
        self.announce(message)
        return message

    def _run(self) -> None:
        while not self._stop.is_set():
            now = dt.datetime.now().astimezone()
            if self._is_due(now):
                message = self.build(now)
                self.announce(message)
                self._save_last_date(now.date().isoformat())
            self._stop.wait(20)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="omega-morning-briefing",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
