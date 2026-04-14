"""PDF Loader 契约测试。"""

from __future__ import annotations

from pathlib import Path

from core.settings import (
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.types import parse_image_placeholders
from libs.loader.pdf_loader import PdfLoader


def _build_settings() -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider="azure_openai"),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
    )


def test_pdf_loader_load_when_text_only_pdf_then_return_document_with_source_metadata() -> None:
    """纯文本 PDF 应输出带基础 metadata 的 Document。"""

    fixture_path = Path("tests/fixtures/sample_documents/simple.pdf")
    loader = PdfLoader(
        _build_settings(),
        text_converter=lambda _: "# 简单文档\n\n这是一段 PDF 文本。",
    )

    document = loader.load(str(fixture_path))

    assert document.text == "# 简单文档\n\n这是一段 PDF 文本。"
    assert document.metadata["source_path"].endswith("tests\\fixtures\\sample_documents\\simple.pdf")
    assert document.metadata["doc_type"] == "pdf"
    assert document.metadata["images"] == []
    assert len(document.id) == 64


def test_pdf_loader_load_when_pdf_contains_images_then_insert_placeholders_and_persist_images(
    tmp_path: Path,
) -> None:
    """带图片的 PDF 应插入占位符并返回图片元数据。"""

    fixture_path = Path("tests/fixtures/sample_documents/with_images.pdf")

    def image_extractor(_: Path, output_dir: Path) -> list[dict[str, object]]:
        image_path = output_dir / "img-001.png"
        image_path.write_bytes(b"fake-image")
        return [
            {
                "id": "img-001",
                "path": str(image_path),
                "text_offset": 5,
                "text_length": 0,
                "page": 1,
            }
        ]

    loader = PdfLoader(
        _build_settings(),
        text_converter=lambda _: "封面段落\n正文继续。",
        image_extractor=image_extractor,
        image_root_dir=str(tmp_path),
    )

    document = loader.load(str(fixture_path))

    assert parse_image_placeholders(document.text) == ["img-001"]
    assert "[IMAGE: img-001]" in document.text
    assert document.metadata["images"][0]["page"] == 1
    assert Path(document.metadata["images"][0]["path"]).exists()


def test_pdf_loader_load_when_image_extractor_fails_then_continue_without_images(tmp_path: Path) -> None:
    """图片提取失败时不应阻塞文本解析。"""

    fixture_path = Path("tests/fixtures/sample_documents/with_images.pdf")

    def broken_extractor(_: Path, __: Path) -> list[dict[str, object]]:
        raise RuntimeError("image extraction failed")

    loader = PdfLoader(
        _build_settings(),
        text_converter=lambda _: "仅保留文本内容。",
        image_extractor=broken_extractor,
        image_root_dir=str(tmp_path),
    )

    document = loader.load(str(fixture_path))

    assert document.text == "仅保留文本内容。"
    assert document.metadata["images"] == []

