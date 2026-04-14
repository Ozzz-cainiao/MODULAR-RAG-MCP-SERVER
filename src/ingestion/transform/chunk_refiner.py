"""ChunkRefiner 实现。"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from core.settings import Settings
from core.trace import TraceContext
from core.types import Chunk
from ingestion.transform.base_transform import BaseTransform
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory


_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADER_FOOTER_PATTERN = re.compile(
    r"^(page\s+\d+(\s+of\s+\d+)?)$|^[-_]{3,}$",
    re.IGNORECASE,
)


class ChunkRefiner(BaseTransform):
    """对 Chunk 进行规则清洗与可选 LLM 精炼。"""

    def __init__(
        self,
        settings: Settings,
        llm: BaseLLM | None = None,
        prompt_path: str | None = None,
    ) -> None:
        """初始化 ChunkRefiner。"""

        self._settings = settings
        self._llm = llm
        self._prompt_path = (
            prompt_path or settings.ingestion.chunk_refiner.prompt_path
        )
        self._use_llm = settings.ingestion.chunk_refiner.use_llm
        self._prompt_template = self._load_prompt(self._prompt_path)

    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        """执行 Chunk 精炼。"""

        refined: list[Chunk] = []
        for chunk in chunks:
            try:
                result = self._refine_single(chunk, trace)
            except Exception as error:
                metadata = deepcopy(chunk.metadata)
                metadata["refined_by"] = "error"
                metadata["refine_error"] = type(error).__name__
                result = Chunk(
                    id=chunk.id,
                    text=chunk.text,
                    metadata=metadata,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    source_ref=chunk.source_ref,
                )
            refined.append(result)
        return refined

    def _refine_single(self, chunk: Chunk, trace: TraceContext | None) -> Chunk:
        if trace is not None:
            trace.record_stage("chunk_refiner", {"chunk_id": chunk.id})

        rule_text = self._rule_based_refine(chunk.text)
        metadata = deepcopy(chunk.metadata)

        if not self._use_llm:
            metadata["refined_by"] = "rule"
            return self._build_chunk(chunk, rule_text, metadata)

        llm_text = self._llm_refine(rule_text)
        if llm_text is None:
            metadata["refined_by"] = "rule"
            metadata["refine_fallback_reason"] = "llm_failed_or_empty"
            return self._build_chunk(chunk, rule_text, metadata)

        metadata["refined_by"] = "llm"
        return self._build_chunk(chunk, llm_text, metadata)

    def _build_chunk(self, chunk: Chunk, text: str, metadata: dict[str, Any]) -> Chunk:
        return Chunk(
            id=chunk.id,
            text=text,
            metadata=metadata,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            source_ref=chunk.source_ref,
        )

    def _rule_based_refine(self, text: str) -> str:
        segments = self._split_by_code_block(text)
        cleaned_segments: list[str] = []
        for index, segment in enumerate(segments):
            if index % 2 == 1:
                cleaned_segments.append(segment)
            else:
                cleaned_segments.append(self._clean_text_segment(segment))
        return self._normalize_text("".join(cleaned_segments))

    def _clean_text_segment(self, text: str) -> str:
        cleaned = _HTML_COMMENT_PATTERN.sub("", text)
        lines = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if stripped and _HEADER_FOOTER_PATTERN.match(stripped):
                continue
            lines.append(line)
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    def _split_by_code_block(self, text: str) -> list[str]:
        if "```" not in text:
            return [text]
        parts = text.split("```")
        segments: list[str] = []
        for index, part in enumerate(parts):
            if index == 0:
                segments.append(part)
                continue
            segments.append("```" + part)
        return segments

    def _llm_refine(self, text: str) -> str | None:
        llm = self._llm or LLMFactory.create(self._settings)
        prompt = self._prompt_template.format(text=text)
        messages = [
            {"role": "user", "content": prompt},
        ]
        try:
            response = llm.chat(messages)
        except Exception:
            return None
        if not isinstance(response, str) or not response.strip():
            return None
        return response.strip()

    def _load_prompt(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                template = handle.read()
        except FileNotFoundError:
            template = "Refine the following chunk while preserving key facts.\n\n{text}"

        if "{text}" not in template:
            template = f"{template}\n\n{{text}}"
        return template

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()
