"""Application configuration and optional .env loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL = "openai/gpt-6-luna"
DEFAULT_TIMEOUT = 90


class ConfigurationError(ValueError):
    """Raised when environment configuration is invalid."""


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding existing environment."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ConfigurationError(f"Не удалось прочитать файл настроек {path}: {exc}") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key or not key.replace("_", "").isalnum() or key[0].isdigit():
            raise ConfigurationError(f"Некорректная запись в {path}, строка {line_number}.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str
    timeout: int

    @classmethod
    def from_environment(cls) -> "Settings":
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip()
        timeout_value = os.getenv("OPENROUTER_TIMEOUT", str(DEFAULT_TIMEOUT)).strip()
        if not model:
            raise ConfigurationError("OPENROUTER_MODEL не может быть пустым.")
        try:
            timeout = int(timeout_value)
        except ValueError as exc:
            raise ConfigurationError("OPENROUTER_TIMEOUT должен быть целым числом секунд.") from exc
        if timeout <= 0:
            raise ConfigurationError("OPENROUTER_TIMEOUT должен быть больше нуля.")
        return cls(api_key=api_key, model=model, timeout=timeout)
