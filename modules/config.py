"""Environment-driven OMEGA configuration."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("OMEGA_MODEL", "llama3.2")
    ollama_url: str = os.getenv("OMEGA_OLLAMA_URL", "http://localhost:11434")
    history_limit: int = int(os.getenv("OMEGA_HISTORY_LIMIT", "20"))
    request_timeout: int = int(os.getenv("OMEGA_REQUEST_TIMEOUT", "120"))
    data_dir: str = os.getenv("OMEGA_DATA_DIR", "data")
    home_location: str = os.getenv("OMEGA_HOME_LOCATION", "Woodbridge, New Jersey")
