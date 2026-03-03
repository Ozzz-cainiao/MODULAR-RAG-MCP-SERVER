"""Recursive Splitter 默认实现。"""

from __future__ import annotations

import os
import re

from core.settings import Settings
from libs.splitter.base_splitter import BaseSplitter, TraceContext


class RecursiveSplitter(BaseSplitter):
    """面向 Markdown 的递归切分器。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Recursive Splitter。"""

        super().__init__(settings)
        self.chunk_size = int(os.getenv("SPLITTER_CHUNK_SIZE", "500"))
        self.chunk_overlap = int(os.getenv("SPLITTER_CHUNK_OVERLAP", "50"))

        if self.chunk_size <= 0:
            raise ValueError("SPLITTER_CHUNK_SIZE 必须大于 0")
        if self.chunk_overlap < 0:
            raise ValueError("SPLITTER_CHUNK_OVERLAP 不能小于 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("SPLITTER_CHUNK_OVERLAP 必须小于 SPLITTER_CHUNK_SIZE")

    def split_text(
        self,
        text: str,
        trace: TraceContext | None = None,
    ) -> list[str]:
        """执行 Markdown 结构友好的递归切分。"""

        if not isinstance(text, str):
            raise ValueError("text 必须是字符串")

        normalized = text.strip()
        if not normalized:
            return []

        markdown_segments = _segment_markdown(normalized)

        chunks: list[str] = []
        for segment in markdown_segments:
            segment_text = segment.strip()
            if not segment_text:
                continue

            if segment_text.startswith("```") and segment_text.endswith("```"):
                chunks.append(segment_text)
                continue

            chunks.extend(_recursive_split(segment_text, self.chunk_size))

        return _merge_with_overlap(chunks, self.chunk_size, self.chunk_overlap)


def _segment_markdown(text: str) -> list[str]:
    """按 Markdown 结构进行一级分段，避免打断标题和代码块。"""

    lines = text.splitlines()
    segments: list[str] = []
    paragraph_buffer: list[str] = []
    code_buffer: list[str] = []
    in_code_block = False

    def flush_paragraph() -> None:
        if paragraph_buffer:
            paragraph_text = "\n".join(paragraph_buffer).strip()
            if paragraph_text:
                segments.append(paragraph_text)
            paragraph_buffer.clear()

    for line in lines:
        is_fence = line.strip().startswith("```")

        if in_code_block:
            code_buffer.append(line)
            if is_fence:
                code_text = "\n".join(code_buffer).strip()
                if code_text:
                    segments.append(code_text)
                code_buffer.clear()
                in_code_block = False
            continue

        if is_fence:
            flush_paragraph()
            in_code_block = True
            code_buffer = [line]
            continue

        if re.match(r"^#{1,6}\s+", line.strip()):
            flush_paragraph()
            segments.append(line.strip())
            continue

        paragraph_buffer.append(line)

    if code_buffer:
        code_text = "\n".join(code_buffer).strip()
        if code_text:
            segments.append(code_text)

    flush_paragraph()
    return segments


def _recursive_split(text: str, chunk_size: int) -> list[str]:
    """按分隔符优先级递归切分文本。"""

    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", "，", ",", " "]
    for separator in separators:
        pieces = _split_by_separator(text, separator)
        if len(pieces) <= 1:
            continue

        if max(len(piece) for piece in pieces) >= len(text):
            continue

        chunks: list[str] = []
        for piece in pieces:
            piece_text = piece.strip()
            if not piece_text:
                continue
            chunks.extend(_recursive_split(piece_text, chunk_size))
        if chunks:
            return chunks

    return _force_split(text, chunk_size)


def _split_by_separator(text: str, separator: str) -> list[str]:
    """按分隔符切分并尽量保留原语义边界。"""

    if separator in {"\n\n", "\n", " "}:
        return [piece for piece in text.split(separator) if piece.strip()]

    raw_parts = text.split(separator)
    parts: list[str] = []
    for index, part in enumerate(raw_parts):
        cleaned = part.strip()
        if not cleaned:
            continue
        if index < len(raw_parts) - 1:
            parts.append(f"{cleaned}{separator}")
        else:
            parts.append(cleaned)
    return parts


def _force_split(text: str, chunk_size: int) -> list[str]:
    """在无可用分隔符时按固定长度强制切分。"""

    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]


def _merge_with_overlap(chunks: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    """在切分结果间加入轻量 overlap，提升上下文连续性。"""

    if not chunks:
        return []
    if chunk_overlap == 0:
        return chunks

    merged: list[str] = []
    for index, chunk in enumerate(chunks):
        if index == 0:
            merged.append(chunk)
            continue

        previous_tail = merged[-1][-chunk_overlap:].strip()
        candidate = f"{previous_tail}\n{chunk}" if previous_tail else chunk

        if len(candidate) > chunk_size and len(chunk) <= chunk_size:
            merged.append(chunk)
        else:
            merged.append(candidate)

    return merged

