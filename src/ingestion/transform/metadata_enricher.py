"""MetadataEnricher 实现。"""

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from core.settings import Settings
from core.trace import TraceContext
from core.types import Chunk
from ingestion.transform.base_transform import BaseTransform
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory


_WORD_PATTERN = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]+")


class MetadataEnricher(BaseTransform):
    """为 Chunk 生成 title/summary/tags。"""

    def __init__(
        self,
        settings: Settings,
        llm: BaseLLM | None = None,
        prompt_path: str | None = None,
    ) -> None:
        self._settings = settings
        self._llm = llm
        self._use_llm = settings.ingestion.metadata_enricher.use_llm
        self._prompt_path = (
            prompt_path or settings.ingestion.metadata_enricher.prompt_path
        )
        self._prompt_template = self._load_prompt(self._prompt_path)

    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        enriched: list[Chunk] = []
        for chunk in chunks:
            try:
                result = self._enrich_single(chunk, trace)
            except Exception as error:
                metadata = deepcopy(chunk.metadata)
                metadata["metadata_enriched_by"] = "error"
                metadata["metadata_enrich_error"] = type(error).__name__
                result = self._build_chunk(chunk, metadata)
            enriched.append(result)
        return enriched

    def _enrich_single(self, chunk: Chunk, trace: TraceContext | None) -> Chunk:
        if trace is not None:
            trace.record_stage("metadata_enricher", {"chunk_id": chunk.id})

        rule_metadata = self._rule_based_metadata(chunk.text)
        metadata = deepcopy(chunk.metadata)

        if not self._use_llm:
            metadata.update(rule_metadata)
            metadata["metadata_enriched_by"] = "rule"
            return self._build_chunk(chunk, metadata)

        llm_metadata = self._llm_metadata(chunk.text)
        if llm_metadata is None:
            metadata.update(rule_metadata)
            metadata["metadata_enriched_by"] = "rule"
            metadata["metadata_enrich_fallback_reason"] = "llm_failed_or_invalid"
            return self._build_chunk(chunk, metadata)

        metadata.update(llm_metadata)
        metadata["metadata_enriched_by"] = "llm"
        return self._build_chunk(chunk, metadata)

    def _build_chunk(self, chunk: Chunk, metadata: dict[str, Any]) -> Chunk:
        return Chunk(
            id=chunk.id,
            text=chunk.text,
            metadata=metadata,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            source_ref=chunk.source_ref,
        )

    def _rule_based_metadata(self, text: str) -> dict[str, Any]:
        normalized = text.strip()
        title = self._derive_title(normalized)
        summary = self._derive_summary(normalized)
        tags = self._derive_tags(normalized)
        return {"title": title, "summary": summary, "tags": tags}

    def _derive_title(self, text: str) -> str:
        if not text:
            return "Untitled"
        first_line = text.splitlines()[0].strip()
        return first_line[:60] if first_line else "Untitled"

    def _derive_summary(self, text: str) -> str:
        if not text:
            return "No summary available."
        compressed = re.sub(r"\s+", " ", text).strip()
        return compressed[:160]

    def _derive_tags(self, text: str) -> list[str]:
        words = _WORD_PATTERN.findall(text.lower())
        filtered = [word for word in words if len(word) >= 2]
        unique: list[str] = []
        for word in filtered:
            if word not in unique:
                unique.append(word)
            if len(unique) >= 5:
                break
        return unique or ["general"]

    def _llm_metadata(self, text: str) -> dict[str, Any] | None:
        llm = self._llm or LLMFactory.create(self._settings)
        prompt = self._prompt_template.format(text=text)
        messages = [{"role": "user", "content": prompt}]
        try:
            response = llm.chat(messages)
        except Exception:
            return None
        if not isinstance(response, str) or not response.strip():
            return None
        try:
            payload = json.loads(response)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        title = payload.get("title")
        summary = payload.get("summary")
        tags = payload.get("tags")
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(tags, list) or not tags:
            return None
        normalized_tags = [tag for tag in tags if isinstance(tag, str) and tag.strip()]
        if not normalized_tags:
            return None
        return {
            "title": title.strip(),
            "summary": summary.strip(),
            "tags": normalized_tags,
        }

    def _load_prompt(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                template = handle.read()
        except FileNotFoundError:
            template = "Generate JSON with title, summary, tags for:\n\n{text}"
        if "{text}" not in template:
            template = f"{template}\n\n{{text}}"
        return template
