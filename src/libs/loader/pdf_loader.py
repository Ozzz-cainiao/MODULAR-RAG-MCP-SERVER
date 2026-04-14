"""PDF Loader 默认实现。"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from pathlib import Path
import re
from typing import Any
import zlib

from core.settings import Settings
from core.types import Document, build_image_placeholder
from libs.loader.base_loader import BaseLoader

PdfTextConverter = Callable[[Path], str]
PdfImageExtractor = Callable[[Path, Path], list[dict[str, Any]]]

_STREAM_PATTERN = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
_TEXT_LITERAL_PATTERN = re.compile(rb"\((?:\\.|[^\\)])*\)\s*TJ?|\[(.*?)\]\s*TJ", re.DOTALL)
_STRING_PATTERN = re.compile(rb"\((?:\\.|[^\\)])*\)")


class PdfLoader(BaseLoader):
    """将 PDF 文件转换为 `Document` 的最小实现。"""

    def __init__(
        self,
        settings: Settings,
        text_converter: PdfTextConverter | None = None,
        image_extractor: PdfImageExtractor | None = None,
        image_root_dir: str = "data/images",
    ) -> None:
        """初始化 PDF Loader。

        参数:
            settings: 项目全局配置对象。
            text_converter: 可选 PDF 文本转换器，便于替换为 MarkItDown 等实现。
            image_extractor: 可选图片提取器，负责落盘并返回图片元数据。
            image_root_dir: 图片存储根目录。
        """

        super().__init__(settings)
        self._text_converter = text_converter or self._default_text_converter
        self._image_extractor = image_extractor
        self._image_root_dir = Path(image_root_dir)

    def load(self, path: str) -> Document:
        """加载 PDF 文件并输出标准文档对象。"""

        pdf_path = Path(path).expanduser().resolve()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"仅支持 PDF 文件: {pdf_path}")

        file_bytes = pdf_path.read_bytes()
        document_id = hashlib.sha256(file_bytes).hexdigest()
        text = self._normalize_text(self._text_converter(pdf_path))
        images = self._extract_images(pdf_path, document_id)
        document_text = self._inject_image_placeholders(text, images)

        metadata: dict[str, Any] = {
            "source_path": str(pdf_path),
            "doc_type": "pdf",
            "title": pdf_path.stem,
            "images": images,
        }
        return Document(id=document_id, text=document_text, metadata=metadata)

    def _extract_images(self, pdf_path: Path, document_id: str) -> list[dict[str, Any]]:
        if self._image_extractor is None:
            return []

        output_dir = self._image_root_dir / document_id
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            images = self._image_extractor(pdf_path, output_dir)
        except Exception:
            return []

        return [self._normalize_image_metadata(item, index, output_dir) for index, item in enumerate(images)]

    def _normalize_image_metadata(
        self,
        image: dict[str, Any],
        index: int,
        output_dir: Path,
    ) -> dict[str, Any]:
        if not isinstance(image, dict):
            raise TypeError("图片元数据必须是字典")

        image_id = self._require_non_empty_string(image.get("id"), f"images[{index}].id")
        image_path = image.get("path")
        if not isinstance(image_path, str) or not image_path.strip():
            image_path = str(output_dir / f"{image_id}.bin")

        text_offset = self._to_non_negative_int(image.get("text_offset", 0), f"images[{index}].text_offset")
        text_length = self._to_non_negative_int(image.get("text_length", 0), f"images[{index}].text_length")

        normalized: dict[str, Any] = {
            "id": image_id,
            "path": image_path.strip(),
            "text_offset": text_offset,
            "text_length": text_length,
        }

        if image.get("page") is not None:
            normalized["page"] = self._to_non_negative_int(image["page"], f"images[{index}].page")
        if image.get("position") is not None:
            if not isinstance(image["position"], dict):
                raise TypeError(f"images[{index}].position 必须是字典")
            normalized["position"] = dict(image["position"])

        return normalized

    def _inject_image_placeholders(self, text: str, images: list[dict[str, Any]]) -> str:
        if not images:
            return text

        segments: list[str] = []
        cursor = 0
        sorted_images = sorted(images, key=lambda item: (item["text_offset"], item["id"]))

        for image in sorted_images:
            text_offset = min(image["text_offset"], len(text))
            if text_offset < cursor:
                text_offset = cursor

            segments.append(text[cursor:text_offset])
            segments.append(build_image_placeholder(image["id"]))

            next_cursor = text_offset + image["text_length"]
            if next_cursor <= cursor:
                next_cursor = text_offset
            cursor = min(next_cursor, len(text))

        segments.append(text[cursor:])
        return self._normalize_text("".join(segments))

    def _default_text_converter(self, pdf_path: Path) -> str:
        try:
            from markitdown import MarkItDown  # type: ignore
        except ImportError:
            return self._extract_text_with_builtin_parser(pdf_path.read_bytes())

        result = MarkItDown().convert(str(pdf_path))
        text = getattr(result, "text_content", "") or ""
        return text if isinstance(text, str) else str(text)

    def _extract_text_with_builtin_parser(self, file_bytes: bytes) -> str:
        candidates: list[bytes] = [file_bytes]
        for match in _STREAM_PATTERN.finditer(file_bytes):
            raw_stream = match.group(1)
            candidates.append(raw_stream)
            try:
                candidates.append(zlib.decompress(raw_stream))
            except zlib.error:
                continue

        parts: list[str] = []
        for blob in candidates:
            text = self._extract_pdf_text_literals(blob)
            if text:
                parts.append(text)

        return self._normalize_text("\n\n".join(parts))

    def _extract_pdf_text_literals(self, data: bytes) -> str:
        fragments: list[str] = []
        for match in _TEXT_LITERAL_PATTERN.finditer(data):
            fragment = match.group(0)
            for string_match in _STRING_PATTERN.finditer(fragment):
                decoded = self._decode_pdf_string(string_match.group(0)[1:-1])
                if decoded:
                    fragments.append(decoded)
        return "\n".join(fragments)

    def _decode_pdf_string(self, payload: bytes) -> str:
        text = payload.decode("latin-1", errors="ignore")
        replacements = {
            r"\(": "(",
            r"\)": ")",
            r"\n": "\n",
            r"\r": "\r",
            r"\t": "\t",
            r"\b": "\b",
            r"\f": "\f",
            r"\\": "\\",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text.strip()

    def _normalize_text(self, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("PDF 转换结果必须是字符串")

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _require_non_empty_string(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} 必须是非空字符串")
        return value.strip()

    def _to_non_negative_int(self, value: Any, field_name: str) -> int:
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} 必须是非负整数")
        return value

