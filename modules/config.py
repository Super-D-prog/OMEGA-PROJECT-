"""Environment-driven OMEGA configuration."""
from dataclasses import dataclass
import os


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("OMEGA_MODEL", "llama3.2")
    ollama_url: str = os.getenv("OMEGA_OLLAMA_URL", "http://localhost:11434")
    history_limit: int = int(os.getenv("OMEGA_HISTORY_LIMIT", "20"))
    request_timeout: int = int(os.getenv("OMEGA_REQUEST_TIMEOUT", "120"))
    data_dir: str = os.getenv("OMEGA_DATA_DIR", "data")
    home_location: str = os.getenv("OMEGA_HOME_LOCATION", "Woodbridge, New Jersey")
    proactive_enabled: bool = env_flag("OMEGA_PROACTIVE", True)
    morning_briefing_time: str = os.getenv("OMEGA_BRIEFING_TIME", "09:00")
    speak_briefings: bool = env_flag("OMEGA_SPEAK_BRIEFINGS", False)
