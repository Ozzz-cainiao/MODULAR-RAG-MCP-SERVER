"""配置加载与校验测试。"""

from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from core.settings import SettingsValidationError, load_settings


def test_load_settings_when_valid_yaml_then_returns_settings(tmp_path: Path) -> None:
    """加载有效 YAML 并返回配置对象。"""
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            llm:
              provider: openai
            embedding:
              provider: openai
            vector_store:
              provider: chroma
            retrieval:
              top_k: 5
            rerank:
              provider: none
            evaluation:
              provider: custom
            observability:
              level: INFO
            """
        ).strip(),
        encoding="utf-8",
    )

    settings = load_settings(str(config_path))

    assert settings.embedding.provider == "openai"
    assert settings.retrieval.top_k == 5


def test_load_settings_when_embedding_provider_missing_then_raise_readable_error(tmp_path: Path) -> None:
    """缺失字段时抛出包含字段路径的可读错误。"""
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            llm:
              provider: openai
            embedding: {}
            vector_store:
              provider: chroma
            retrieval:
              top_k: 5
            rerank:
              provider: none
            evaluation:
              provider: custom
            observability:
              level: INFO
            """
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(SettingsValidationError, match="embedding.provider"):
        load_settings(str(config_path))
