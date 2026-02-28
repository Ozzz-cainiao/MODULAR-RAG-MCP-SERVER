"""VectorStoreFactory：按配置构建 Vector Store 实例。"""

from __future__ import annotations

from collections.abc import Callable

from core.settings import Settings
from libs.vector_store.base_vector_store import BaseVectorStore


VectorStoreBuilder = Callable[[Settings], BaseVectorStore]


class VectorStoreFactory:
    """Vector Store 工厂。

    通过 provider 名称路由到已注册的 Vector Store 构建器。
    """

    _registry: dict[str, VectorStoreBuilder] = {}

    @classmethod
    def register(cls, provider: str, builder: VectorStoreBuilder) -> None:
        """注册 provider 对应的 Vector Store 构建器。

        参数:
            provider: provider 名称。
            builder: 接收 Settings 并返回 BaseVectorStore 的构建器。
        """

        normalized_provider = provider.strip().lower()
        if not normalized_provider:
            raise ValueError("provider 不能为空")
        cls._registry[normalized_provider] = builder

    @classmethod
    def create(cls, settings: Settings) -> BaseVectorStore:
        """根据配置创建 Vector Store 实例。

        参数:
            settings: 项目全局配置对象。

        返回:
            BaseVectorStore 的具体实现实例。

        异常:
            ValueError: 当 provider 未注册时抛出。
        """

        provider = settings.vector_store.provider.strip().lower()
        if not provider:
            raise ValueError("vector_store.provider 不能为空")

        builder = cls._registry.get(provider)
        if builder is None:
            raise ValueError(f"未注册的 vector_store provider: {provider}")

        return builder(settings)

