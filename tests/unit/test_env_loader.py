"""Unit tests for local .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from core.env import load_dotenv


def test_load_dotenv_when_env_file_exists_then_populate_missing_variables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'OPENAI_API_KEY="test-key"\nOPENAI_BASE_URL=https://example.com/v1\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    loaded = load_dotenv(str(env_file))

    assert loaded is True
    assert os.getenv("OPENAI_API_KEY") == "test-key"
    assert os.getenv("OPENAI_BASE_URL") == "https://example.com/v1"


def test_load_dotenv_when_variable_exists_and_override_false_then_keep_original(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "existing-key")

    load_dotenv(str(env_file), override=False)

    assert os.getenv("OPENAI_API_KEY") == "existing-key"
