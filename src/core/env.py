"""Lightweight .env loader for local project configuration."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(dotenv_path: str = ".env", override: bool = False) -> bool:
    """Load key=value pairs from a .env file into os.environ.

    Parameters:
        dotenv_path: Path to the .env file, relative to cwd when not absolute.
        override: Whether existing environment variables should be overwritten.

    Returns:
        True when the file exists and was processed, otherwise False.
    """

    path = Path(dotenv_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            continue

        normalized_value = _strip_quotes(value.strip())
        if override or normalized_key not in os.environ:
            os.environ[normalized_key] = normalized_value
    return True


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
