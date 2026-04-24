"""Vector Store 抽象接口定义。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeAlias

from core.settings import Settings


TraceContext: TypeAlias = Any
VectorRecord: TypeAlias = dict[str, Any]
VectorQueryResult: TypeAlias = dict[str, Any]


class BaseVectorStore(ABC):
    """Vector Store 适配器基类。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Vector Store 实例。

        参数:
            settings: 项目全局配置对象。
        """

        self.settings = settings

    @abstractmethod
    def upsert(
        self,
        records: list[VectorRecord],
        trace: TraceContext | None = None,
    ) -> None:
        """写入或更新向量记录。

        参数:
            records: 向量记录列表。
            trace: 可选 TraceContext，用于链路追踪。
        """

    @abstractmethod
    def query(
        self,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[VectorQueryResult]:
        """按向量检索相似记录。

        参数:
            vector: 查询向量。
            top_k: 返回结果数量上限。
            filters: 可选过滤条件。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            查询结果列表，每项应至少包含 `chunk_id/score/text/metadata`。
        """

    @abstractmethod
    def get_by_ids(
        self,
        chunk_ids: list[str],
        trace: TraceContext | None = None,
    ) -> list[VectorQueryResult]:
        """按 chunk_id 列表获取记录。

        参数:
            chunk_ids: 待查询的 chunk_id 列表。
            trace: 可选 TraceContext，用于链路追踪。

        返回:
            与输入顺序一致的结果列表，不存在的 chunk_id 会被忽略。
        """
        raise NotImplementedError

    def get_by_metadata(
        self,
        filters: dict[str, Any] | None = None,
        trace: TraceContext | None = None,
    ) -> list[VectorQueryResult]:
        """按 metadata 过滤获取记录。"""

        raise NotImplementedError

    def delete_by_metadata(
        self,
        filters: dict[str, Any],
        trace: TraceContext | None = None,
    ) -> int:
        """按 metadata 条件删除记录并返回删除数量。"""

        raise NotImplementedError

    def get_collection_stats(self, trace: TraceContext | None = None) -> dict[str, Any]:
        """返回集合维度的统计信息。"""

        raise NotImplementedError
