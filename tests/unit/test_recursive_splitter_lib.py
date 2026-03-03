"""RecursiveSplitter 默认实现测试。"""

from __future__ import annotations

import pytest

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from libs.splitter.recursive_splitter import RecursiveSplitter
from libs.splitter.splitter_factory import SplitterFactory


def _build_settings(provider: str = "recursive") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider=provider),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_splitter_factory_create_when_provider_recursive_then_return_recursive_splitter() -> None:
    """provider=recursive 时工厂应返回 RecursiveSplitter。"""

    splitter = SplitterFactory.create(_build_settings("recursive"))

    assert isinstance(splitter, RecursiveSplitter)


def test_recursive_splitter_split_text_when_markdown_with_heading_and_code_then_not_break_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Markdown 标题与代码块应保持结构完整。"""

    monkeypatch.setenv("SPLITTER_CHUNK_SIZE", "80")
    monkeypatch.setenv("SPLITTER_CHUNK_OVERLAP", "0")

    splitter = RecursiveSplitter(_build_settings())
    markdown_text = """# 标题一

这是一段较长的介绍文本，用于验证切分器对 Markdown 结构的处理能力。

```python
def hello():
    return "world"
```

## 小节二

第二段正文继续说明切分行为。
"""

    chunks = splitter.split_text(markdown_text)

    assert chunks
    assert any("# 标题一" in chunk for chunk in chunks)
    assert any("## 小节二" in chunk for chunk in chunks)

    code_chunks = [chunk for chunk in chunks if chunk.startswith("```python")]
    assert len(code_chunks) == 1
    assert "def hello():" in code_chunks[0]
    assert code_chunks[0].endswith("```")


def test_recursive_splitter_split_text_when_input_long_then_split_into_multiple_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """长文本输入时应切分为多个 chunk。"""

    monkeypatch.setenv("SPLITTER_CHUNK_SIZE", "40")
    monkeypatch.setenv("SPLITTER_CHUNK_OVERLAP", "0")

    splitter = RecursiveSplitter(_build_settings())
    text = "这是一段用于测试递归切分的长文本。" * 8

    chunks = splitter.split_text(text)

    assert len(chunks) >= 2
    assert all(isinstance(item, str) and item.strip() for item in chunks)


def test_recursive_splitter_split_text_when_empty_then_return_empty_list() -> None:
    """空白文本应返回空列表。"""

    splitter = RecursiveSplitter(_build_settings())

    assert splitter.split_text("   \n\t  ") == []

