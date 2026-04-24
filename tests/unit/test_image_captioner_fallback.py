"""Unit tests for ImageCaptioner fallback and success behavior."""

from __future__ import annotations

from pathlib import Path

from core.settings import (
    ChunkRefinerSettings,
    IngestionSettings,
    MetadataEnricherSettings,
    ObservabilitySettings,
    ProviderSettings,
    RetrievalSettings,
    Settings,
)
from core.trace import TraceContext
from core.types import Chunk, build_image_placeholder
from ingestion.transform.image_captioner import ImageCaptioner
from libs.llm.base_vision_llm import BaseVisionLLM, ChatResponse


class FakeVisionLLM(BaseVisionLLM):
    """Fake Vision LLM used for image captioner tests."""

    def __init__(
        self,
        settings: Settings,
        response_text: str | None = None,
        raise_error: bool = False,
    ) -> None:
        super().__init__(settings)
        self._response_text = response_text
        self._raise_error = raise_error
        self.calls: list[tuple[str, str | bytes]] = []

    def chat_with_image(
        self,
        text: str,
        image_input: str | bytes,
        trace: TraceContext | None = None,
    ) -> ChatResponse:
        self.calls.append((text, image_input))
        if self._raise_error:
            raise RuntimeError("vision llm error")
        return {"text": self._response_text or ""}


def _build_settings(vision_provider: str = "azure") -> Settings:
    return Settings(
        llm=ProviderSettings(provider="openai"),
        vision_llm=ProviderSettings(provider=vision_provider),
        embedding=ProviderSettings(provider="openai"),
        splitter=ProviderSettings(provider="recursive"),
        vector_store=ProviderSettings(provider="chroma"),
        retrieval=RetrievalSettings(top_k=5),
        rerank=ProviderSettings(provider="none"),
        evaluation=ProviderSettings(provider="custom"),
        observability=ObservabilitySettings(level="INFO"),
        ingestion=IngestionSettings(
            chunk_refiner=ChunkRefinerSettings(
                use_llm=False,
                prompt_path="config/prompts/chunk_refinement.txt",
            ),
            metadata_enricher=MetadataEnricherSettings(
                use_llm=False,
                prompt_path="config/prompts/metadata_enricher.txt",
            ),
        ),
    )


def _build_chunk(image_id: str = "img-001") -> Chunk:
    placeholder = build_image_placeholder(image_id)
    image_path = "tests/fixtures/sample_documents/test_vision_llm.jpg"
    return Chunk(
        id="chunk-img-001",
        text=f"图片说明如下：{placeholder}",
        metadata={
            "source_path": "tests/fixtures/sample_documents/with_images.pdf",
            "doc_type": "pdf",
            "title": "样例",
            "images": [
                {
                    "id": image_id,
                    "path": image_path,
                    "text_offset": 7,
                    "text_length": len(placeholder),
                    "page": 1,
                }
            ],
        },
        start_offset=0,
        end_offset=100,
        source_ref="doc-001",
    )


def test_image_captioner_when_vision_llm_enabled_then_write_captions_to_metadata() -> None:
    """启用 Vision LLM 且 chunk 引用图片时应写回 caption。"""

    settings = _build_settings()
    vision_llm = FakeVisionLLM(settings, response_text="这是一张测试图片。")
    captioner = ImageCaptioner(settings, vision_llm=vision_llm)

    result = captioner.transform([_build_chunk()])[0]

    assert result.metadata["image_captioned_by"] == "vision_llm"
    assert result.metadata["has_unprocessed_images"] is False
    assert result.metadata["image_captions"] == {"img-001": "这是一张测试图片。"}
    assert len(vision_llm.calls) == 1


def test_image_captioner_when_vision_llm_disabled_then_mark_unprocessed_images() -> None:
    """未配置 Vision LLM 时应保留图片引用并标记未处理。"""

    settings = _build_settings(vision_provider="")
    captioner = ImageCaptioner(settings)

    result = captioner.transform([_build_chunk()])[0]

    assert result.metadata["image_captioned_by"] == "disabled"
    assert result.metadata["has_unprocessed_images"] is True
    assert "image_captions" not in result.metadata


def test_image_captioner_when_vision_llm_fails_then_fallback_without_blocking() -> None:
    """Vision LLM 异常时应优雅降级。"""

    settings = _build_settings()
    vision_llm = FakeVisionLLM(settings, raise_error=True)
    captioner = ImageCaptioner(settings, vision_llm=vision_llm)

    result = captioner.transform([_build_chunk()])[0]

    assert result.metadata["image_captioned_by"] == "disabled"
    assert result.metadata["has_unprocessed_images"] is True
    assert result.metadata["image_caption_fallback_reason"] == "vision_llm_failed_or_empty"


def test_image_captioner_when_chunk_has_no_image_placeholders_then_skip() -> None:
    """没有图片占位符时应直接跳过。"""

    settings = _build_settings()
    captioner = ImageCaptioner(settings)
    chunk = Chunk(
        id="chunk-no-image",
        text="这里没有图片。",
        metadata={"source_path": "sample.pdf", "doc_type": "pdf", "title": "样例", "images": []},
        start_offset=0,
        end_offset=7,
        source_ref="doc-002",
    )

    result = captioner.transform([chunk])[0]

    assert result.metadata["image_captioned_by"] == "skipped"
    assert result.metadata["has_unprocessed_images"] is False


def test_image_captioner_when_prompt_file_missing_then_use_default_prompt(tmp_path: Path) -> None:
    """Prompt 文件不存在时应使用默认提示词。"""

    settings = _build_settings()
    captioner = ImageCaptioner(
        settings,
        vision_llm=FakeVisionLLM(settings, response_text="caption"),
        prompt_path=str(tmp_path / "missing.txt"),
    )

    assert captioner._prompt_template == "Describe the image accurately."


def test_image_captioner_when_trace_provided_then_record_stages() -> None:
    """应记录 transform 和 vision llm 阶段。"""

    settings = _build_settings()
    vision_llm = FakeVisionLLM(settings, response_text="caption")
    captioner = ImageCaptioner(settings, vision_llm=vision_llm)
    trace = TraceContext()

    captioner.transform([_build_chunk()], trace=trace)

    stage_names = [stage.name for stage in trace.stages]
    assert stage_names == ["image_captioner", "image_captioner_vision_llm"]
    assert trace.stages[0].metadata["chunk_id"] == "chunk-img-001"
    assert trace.stages[1].metadata["status"] == "success"
