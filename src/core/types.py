"""核心数据类型契约定义。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

Metadata = dict[str, Any]
SparseVector = dict[str, float]

IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\[IMAGE:\s*(?P<image_id>[^\]]+?)\]")


def build_image_placeholder(image_id: str) -> str:
    """构造图片占位符文本。

    参数:
        image_id: 图片唯一标识符。

    返回:
        标准占位符字符串，格式为 `[IMAGE: {image_id}]`。
    """

    normalized_id = _require_non_empty_string(image_id, "image_id")
    return f"[IMAGE: {normalized_id}]"


def parse_image_placeholders(text: str) -> list[str]:
    """从文本中提取图片占位符里的 image_id 列表。

    参数:
        text: 待解析文本。

    返回:
        按出现顺序提取出的 image_id 列表。
    """

    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")
    return [match.group("image_id").strip() for match in IMAGE_PLACEHOLDER_PATTERN.finditer(text)]


@dataclass(slots=True)
class Document:
    """文档级数据契约。"""

    id: str
    text: str
    metadata: Metadata

    def __post_init__(self) -> None:
        self.id = _require_non_empty_string(self.id, "id")
        if not isinstance(self.text, str):
            raise TypeError("text 必须是字符串")
        self.metadata = _normalize_metadata(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""

        return {
            "id": self.id,
            "text": self.text,
            "metadata": deepcopy(self.metadata),
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""

        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Document:
        """从字典反序列化为文档对象。"""

        payload = _require_mapping(data, "data")
        return cls(
            id=payload.get("id"),
            text=payload.get("text"),
            metadata=payload.get("metadata"),
        )

    @classmethod
    def from_json(cls, payload: str) -> Document:
        """从 JSON 字符串反序列化为文档对象。"""

        if not isinstance(payload, str):
            raise TypeError("payload 必须是字符串")
        return cls.from_dict(json.loads(payload))


@dataclass(slots=True)
class Chunk:
    """切块级数据契约。"""

    id: str
    text: str
    metadata: Metadata
    start_offset: int
    end_offset: int
    source_ref: str | None = None

    def __post_init__(self) -> None:
        self.id = _require_non_empty_string(self.id, "id")
        if not isinstance(self.text, str):
            raise TypeError("text 必须是字符串")
        self.metadata = _normalize_metadata(self.metadata)
        self.start_offset = _require_non_negative_int(self.start_offset, "start_offset")
        self.end_offset = _require_non_negative_int(self.end_offset, "end_offset")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset 不能小于 start_offset")
        if self.source_ref is not None:
            self.source_ref = _require_non_empty_string(self.source_ref, "source_ref")

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""

        return {
            "id": self.id,
            "text": self.text,
            "metadata": deepcopy(self.metadata),
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "source_ref": self.source_ref,
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""

        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Chunk:
        """从字典反序列化为切块对象。"""

        payload = _require_mapping(data, "data")
        return cls(
            id=payload.get("id"),
            text=payload.get("text"),
            metadata=payload.get("metadata"),
            start_offset=payload.get("start_offset"),
            end_offset=payload.get("end_offset"),
            source_ref=payload.get("source_ref"),
        )

    @classmethod
    def from_json(cls, payload: str) -> Chunk:
        """从 JSON 字符串反序列化为切块对象。"""

        if not isinstance(payload, str):
            raise TypeError("payload 必须是字符串")
        return cls.from_dict(json.loads(payload))


@dataclass(slots=True)
class ChunkRecord:
    """存储与检索阶段使用的切块记录契约。"""

    id: str
    text: str
    metadata: Metadata
    dense_vector: list[float] | None = None
    sparse_vector: SparseVector | None = None

    def __post_init__(self) -> None:
        self.id = _require_non_empty_string(self.id, "id")
        if not isinstance(self.text, str):
            raise TypeError("text 必须是字符串")
        self.metadata = _normalize_metadata(self.metadata)
        self.dense_vector = _normalize_dense_vector(self.dense_vector)
        self.sparse_vector = _normalize_sparse_vector(self.sparse_vector)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""

        return {
            "id": self.id,
            "text": self.text,
            "metadata": deepcopy(self.metadata),
            "dense_vector": deepcopy(self.dense_vector),
            "sparse_vector": deepcopy(self.sparse_vector),
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""

        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ChunkRecord:
        """从字典反序列化为切块记录对象。"""

        payload = _require_mapping(data, "data")
        return cls(
            id=payload.get("id"),
            text=payload.get("text"),
            metadata=payload.get("metadata"),
            dense_vector=payload.get("dense_vector"),
            sparse_vector=payload.get("sparse_vector"),
        )

    @classmethod
    def from_json(cls, payload: str) -> ChunkRecord:
        """从 JSON 字符串反序列化为切块记录对象。"""

        if not isinstance(payload, str):
            raise TypeError("payload 必须是字符串")
        return cls.from_dict(json.loads(payload))


def _normalize_metadata(metadata: Mapping[str, Any]) -> Metadata:
    payload = _require_mapping(metadata, "metadata")
    normalized = deepcopy(dict(payload))
    source_path = normalized.get("source_path")
    normalized["source_path"] = _require_non_empty_string(source_path, "metadata.source_path")
    _validate_images_metadata(normalized.get("images"))
    return normalized


def _validate_images_metadata(images: Any) -> None:
    if images is None:
        return

    if not isinstance(images, list):
        raise TypeError("metadata.images 必须是 list")

    for index, image in enumerate(images):
        image_path = f"metadata.images[{index}]"
        payload = _require_mapping(image, image_path)
        _require_non_empty_string(payload.get("id"), f"{image_path}.id")
        _require_non_empty_string(payload.get("path"), f"{image_path}.path")
        _require_non_negative_int(payload.get("text_offset"), f"{image_path}.text_offset")
        _require_non_negative_int(payload.get("text_length"), f"{image_path}.text_length")

        page = payload.get("page")
        if page is not None:
            _require_non_negative_int(page, f"{image_path}.page")

        position = payload.get("position")
        if position is not None and not isinstance(position, dict):
            raise TypeError(f"{image_path}.position 必须是 dict")


def _normalize_dense_vector(vector: Any) -> list[float] | None:
    if vector is None:
        return None
    if not isinstance(vector, list):
        raise TypeError("dense_vector 必须是 list[float]")

    normalized: list[float] = []
    for value in vector:
        if not isinstance(value, (int, float)):
            raise TypeError("dense_vector 必须是 list[float]")
        normalized.append(float(value))
    return normalized


def _normalize_sparse_vector(vector: Any) -> SparseVector | None:
    if vector is None:
        return None

    payload = _require_mapping(vector, "sparse_vector")
    normalized: SparseVector = {}
    for key, value in payload.items():
        normalized_key = _require_non_empty_string(key, "sparse_vector.key")
        if not isinstance(value, (int, float)):
            raise TypeError("sparse_vector 的值必须是 float")
        normalized[normalized_key] = float(value)
    return normalized


def _require_mapping(value: Any, field_path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_path} 必须是映射类型")
    return dict(value)


def _require_non_empty_string(value: Any, field_path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_path} 必须是非空字符串")
    return value.strip()


def _require_non_negative_int(value: Any, field_path: str) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{field_path} 必须是整数")
    if value < 0:
        raise ValueError(f"{field_path} 不能小于 0")
    return value

