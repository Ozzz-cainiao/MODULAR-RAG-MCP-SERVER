"""ChromaStore 默认实现（轻量本地持久化版）。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.settings import Settings
from libs.vector_store.base_vector_store import BaseVectorStore, TraceContext, VectorQueryResult, VectorRecord


class ChromaStore(BaseVectorStore):
    """面向本地开发的 ChromaStore 轻量实现。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 ChromaStore，并加载本地持久化数据。"""

        super().__init__(settings)
        persist_path = os.getenv("CHROMA_PERSIST_PATH", "data/db/chroma")
        self.persist_dir = Path(persist_path)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.persist_dir / "records.json"
        self._records: list[VectorRecord] = self._load_records()

    def upsert(
        self,
        records: list[VectorRecord],
        trace: TraceContext | None = None,
    ) -> None:
        """写入记录并持久化到本地目录。"""

        if not isinstance(records, list) or not records:
            raise ValueError("records 必须是非空列表")

        for record in records:
            self._validate_record(record)

        index_by_chunk_id: dict[str, int] = {
            str(record["chunk_id"]): index for index, record in enumerate(self._records)
        }

        for record in records:
            chunk_id = str(record["chunk_id"])
            normalized_record = {
                "chunk_id": chunk_id,
                "vector": [float(value) for value in record["vector"]],
                "text": str(record["text"]),
                "metadata": dict(record["metadata"]),
            }

            existing_index = index_by_chunk_id.get(chunk_id)
            if existing_index is None:
                index_by_chunk_id[chunk_id] = len(self._records)
                self._records.append(normalized_record)
            else:
                self._records[existing_index] = normalized_record

        self._save_records()

    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[VectorQueryResult]:
        """按向量相似度查询记录。"""

        if not isinstance(vector, list) or not vector:
            raise ValueError("vector 必须是非空 list[float]")
        if not all(isinstance(value, (int, float)) for value in vector):
            raise ValueError("vector 必须是非空 list[float]")
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")

        filtered_records = [record for record in self._records if self._match_filters(record, filters)]

        def score_of(record: VectorRecord) -> float:
            stored_vector = record["vector"]
            if len(stored_vector) != len(vector):
                return -1.0
            return float(sum(left * right for left, right in zip(stored_vector, vector)))

        ranked_records = sorted(
            filtered_records,
            key=lambda item: (score_of(item), str(item["chunk_id"])),
            reverse=True,
        )

        return [
            {
                "chunk_id": str(record["chunk_id"]),
                "score": score_of(record),
                "text": str(record["text"]),
                "metadata": dict(record["metadata"]),
            }
            for record in ranked_records[:top_k]
        ]

    def get_by_ids(
        self,
        chunk_ids: list[str],
        trace: TraceContext | None = None,
    ) -> list[VectorQueryResult]:
        """按 chunk_id 获取记录，保持输入顺序。"""

        if not isinstance(chunk_ids, list):
            raise ValueError("chunk_ids 必须是 list[str]")

        records_by_id = {
            str(record["chunk_id"]): {
                "chunk_id": str(record["chunk_id"]),
                "score": 0.0,
                "text": str(record["text"]),
                "metadata": dict(record["metadata"]),
            }
            for record in self._records
        }
        ordered_results: list[VectorQueryResult] = []
        for chunk_id in chunk_ids:
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError("chunk_ids 必须是 list[str]")
            payload = records_by_id.get(chunk_id)
            if payload is not None:
                ordered_results.append(dict(payload))
        return ordered_results

    def _match_filters(self, record: VectorRecord, filters: dict[str, Any] | None) -> bool:
        """判断记录是否命中过滤条件。"""

        if filters is None:
            return True
        if not isinstance(filters, dict):
            raise ValueError("filters 必须是 dict 或 None")

        metadata = record.get("metadata")
        if not isinstance(metadata, dict):
            return False

        for key, value in filters.items():
            if metadata.get(key) != value:
                return False
        return True

    def _validate_record(self, record: VectorRecord) -> None:
        """校验记录契约是否满足输入要求。"""

        required_keys = {"chunk_id", "vector", "text", "metadata"}
        if not isinstance(record, dict) or not required_keys.issubset(record.keys()):
            raise ValueError("record 缺少必填键: chunk_id/vector/text/metadata")

        if not isinstance(record["chunk_id"], str) or not record["chunk_id"].strip():
            raise ValueError("record.chunk_id 必须是非空字符串")
        if not isinstance(record["vector"], list) or not record["vector"]:
            raise ValueError("record.vector 必须是非空 list[float]")
        if not all(isinstance(value, (int, float)) for value in record["vector"]):
            raise ValueError("record.vector 必须是非空 list[float]")
        if not isinstance(record["text"], str):
            raise ValueError("record.text 必须是字符串")
        if not isinstance(record["metadata"], dict):
            raise ValueError("record.metadata 必须是 dict")

    def _load_records(self) -> list[VectorRecord]:
        """从本地文件加载已持久化记录。"""

        if not self.data_file.exists():
            return []

        raw_text = self.data_file.read_text(encoding="utf-8").strip()
        if not raw_text:
            return []

        try:
            loaded = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise ValueError(f"Chroma 持久化文件损坏: {self.data_file}") from error

        if not isinstance(loaded, list):
            raise ValueError("Chroma 持久化文件格式非法，根节点必须是数组")

        records: list[VectorRecord] = []
        for item in loaded:
            self._validate_record(item)
            records.append(
                {
                    "chunk_id": str(item["chunk_id"]),
                    "vector": [float(value) for value in item["vector"]],
                    "text": str(item["text"]),
                    "metadata": dict(item["metadata"]),
                }
            )
        return records

    def _save_records(self) -> None:
        """将记录持久化到本地文件。"""

        self.data_file.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
