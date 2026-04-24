"""ImageCaptioner implementation for optional vision-based image descriptions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from core.settings import Settings
from core.trace import TraceContext
from core.types import Chunk, parse_image_placeholders
from ingestion.transform.base_transform import BaseTransform
from libs.llm.base_vision_llm import BaseVisionLLM
from libs.llm.llm_factory import LLMFactory


class ImageCaptioner(BaseTransform):
    """Generate image captions for chunk-referenced images when Vision LLM is available."""

    def __init__(
        self,
        settings: Settings,
        vision_llm: BaseVisionLLM | None = None,
        prompt_path: str = "config/prompts/image_captioning.txt",
    ) -> None:
        self._settings = settings
        self._vision_llm = vision_llm
        self._resolved_vision_llm = vision_llm
        self._prompt_template = self._load_prompt(prompt_path)

    def transform(self, chunks: list[Chunk], trace: TraceContext | None = None) -> list[Chunk]:
        """Caption images referenced by chunk text without blocking ingestion on failure."""

        transformed: list[Chunk] = []
        for chunk in chunks:
            try:
                transformed.append(self._caption_single(chunk, trace))
            except Exception as error:
                metadata = deepcopy(chunk.metadata)
                metadata["has_unprocessed_images"] = bool(parse_image_placeholders(chunk.text))
                metadata["image_captioned_by"] = "error"
                metadata["image_caption_error"] = type(error).__name__
                transformed.append(self._build_chunk(chunk, metadata))
        return transformed

    def _caption_single(self, chunk: Chunk, trace: TraceContext | None) -> Chunk:
        if trace is not None:
            trace.record_stage("image_captioner", {"chunk_id": chunk.id})

        image_ids = parse_image_placeholders(chunk.text)
        metadata = deepcopy(chunk.metadata)

        if not image_ids:
            metadata["image_captioned_by"] = "skipped"
            metadata["has_unprocessed_images"] = False
            return self._build_chunk(chunk, metadata)

        image_map = self._build_image_map(metadata.get("images"))
        referenced_ids = [image_id for image_id in image_ids if image_id in image_map]
        if not referenced_ids:
            metadata["image_captioned_by"] = "skipped"
            metadata["has_unprocessed_images"] = True
            metadata["image_caption_fallback_reason"] = "missing_image_metadata"
            return self._build_chunk(chunk, metadata)

        vision_llm = self._get_vision_llm()
        if vision_llm is None:
            metadata["image_captioned_by"] = "disabled"
            metadata["has_unprocessed_images"] = True
            return self._build_chunk(chunk, metadata)

        image_captions: dict[str, str] = {}
        unprocessed_ids: list[str] = []
        for image_id in referenced_ids:
            image_info = image_map[image_id]
            caption = self._generate_caption(image_info["path"], trace)
            if caption is None:
                unprocessed_ids.append(image_id)
                continue
            image_captions[image_id] = caption

        if image_captions:
            metadata["image_captions"] = image_captions

        metadata["has_unprocessed_images"] = bool(unprocessed_ids or len(referenced_ids) < len(image_ids))
        metadata["image_captioned_by"] = "vision_llm" if image_captions else "disabled"
        if unprocessed_ids:
            metadata["image_caption_fallback_reason"] = "vision_llm_failed_or_empty"
        return self._build_chunk(chunk, metadata)

    def _build_image_map(self, images: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(images, list):
            return {}
        image_map: dict[str, dict[str, Any]] = {}
        for image in images:
            if not isinstance(image, dict):
                continue
            image_id = image.get("id")
            image_path = image.get("path")
            if isinstance(image_id, str) and image_id.strip() and isinstance(image_path, str) and image_path.strip():
                image_map[image_id.strip()] = image
        return image_map

    def _generate_caption(self, image_path: str, trace: TraceContext | None) -> str | None:
        vision_llm = self._get_vision_llm()
        if vision_llm is None:
            return None

        try:
            response = vision_llm.chat_with_image(
                text=self._prompt_template,
                image_input=image_path,
                trace=trace,
            )
        except Exception as error:
            if trace is not None:
                trace.record_stage(
                    "image_captioner_vision_llm",
                    {"status": "error", "error_type": type(error).__name__},
                )
            return None

        caption = response.get("text") if isinstance(response, dict) else None
        if not isinstance(caption, str) or not caption.strip():
            if trace is not None:
                trace.record_stage(
                    "image_captioner_vision_llm",
                    {"status": "empty_response"},
                )
            return None

        if trace is not None:
            trace.record_stage(
                "image_captioner_vision_llm",
                {"status": "success", "caption_length": len(caption.strip())},
            )
        return caption.strip()

    def _get_vision_llm(self) -> BaseVisionLLM | None:
        provider = self._settings.vision_llm.provider.strip().lower()
        if not provider:
            return None
        if self._resolved_vision_llm is None:
            self._resolved_vision_llm = LLMFactory.create_vision_llm(self._settings)
        return self._resolved_vision_llm

    def _load_prompt(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8").strip() or "Describe the image accurately."
        except FileNotFoundError:
            return "Describe the image accurately."

    def _build_chunk(self, chunk: Chunk, metadata: dict[str, Any]) -> Chunk:
        return Chunk(
            id=chunk.id,
            text=chunk.text,
            metadata=metadata,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            source_ref=chunk.source_ref,
        )
