"""Build MCP content blocks that include referenced images."""

from __future__ import annotations

import base64
from pathlib import Path

from core.types import RetrievalResult, parse_image_placeholders
from ingestion.storage.image_storage import ImageStorage


class MultimodalAssembler:
    """Assemble text and image content blocks for MCP tool responses."""

    def __init__(self, image_storage: ImageStorage | None = None) -> None:
        self._image_storage = image_storage or ImageStorage()

    def build_content(
        self,
        markdown_text: str,
        retrieval_results: list[RetrievalResult],
    ) -> list[dict[str, object]]:
        """Return MCP content blocks with optional base64 encoded images."""

        content: list[dict[str, object]] = [{"type": "text", "text": markdown_text}]
        seen_image_ids: set[str] = set()

        for result in retrieval_results:
            for image_id in parse_image_placeholders(result.text):
                if image_id in seen_image_ids:
                    continue
                image_path = self._image_storage.get_path(image_id)
                if image_path is None:
                    continue

                path = Path(image_path)
                if not path.exists():
                    continue

                seen_image_ids.add(image_id)
                content.append(
                    {
                        "type": "image",
                        "mimeType": _guess_mime_type(path.suffix),
                        "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                        "image_id": image_id,
                    }
                )

        return content


def _guess_mime_type(suffix: str) -> str:
    normalized = suffix.lower()
    if normalized in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if normalized == ".gif":
        return "image/gif"
    if normalized == ".webp":
        return "image/webp"
    return "image/png"
