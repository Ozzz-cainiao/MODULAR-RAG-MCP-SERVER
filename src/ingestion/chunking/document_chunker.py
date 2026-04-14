"""Document Chunking 适配器。"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from core.settings import Settings
from core.types import Chunk, Document
from libs.splitter.splitter_factory import SplitterFactory


class DocumentChunker:
    """将 Document 转换为 Chunk 列表的适配器。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Chunker。

        参数:
            settings: 项目全局配置对象。
        """

        self._splitter = SplitterFactory.create(settings)

    def split_document(self, document: Document) -> list[Chunk]:
        """将文档切分为业务 Chunk 对象列表。"""

        if not isinstance(document, Document):
            raise TypeError("document 必须是 Document 类型")

        raw_chunks = self._splitter.split_text(document.text)
        chunks: list[Chunk] = []
        cursor = 0

        for index, chunk_text in enumerate(raw_chunks):
            if not isinstance(chunk_text, str) or not chunk_text.strip():
                continue

            start_offset = self._find_offset(document.text, chunk_text, cursor)
            end_offset = start_offset + len(chunk_text)
            cursor = max(end_offset, cursor)

            chunk_id = self._generate_chunk_id(document.id, index, chunk_text)
            metadata = self._inherit_metadata(document, index)

            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    metadata=metadata,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    source_ref=document.id,
                )
            )

        return chunks

    def _generate_chunk_id(self, doc_id: str, index: int, chunk_text: str) -> str:
        hash_value = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:8]
        return f"{doc_id}_{index:04d}_{hash_value}"

    def _inherit_metadata(self, document: Document, chunk_index: int) -> dict[str, Any]:
        metadata = deepcopy(document.metadata)
        metadata["chunk_index"] = chunk_index
        return metadata

    def _find_offset(self, text: str, chunk_text: str, cursor: int) -> int:
        start = text.find(chunk_text, cursor)
        if start == -1:
            return min(cursor, len(text))
        return start
