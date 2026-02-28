"""EmbeddingFactory：按配置构建 Embedding 实例。"""

from __future__ import annotations

from collections.abc import Callable

from core.settings import Settings
from libs.embedding.base_embedding import BaseEmbedding


EmbeddingBuilder = Callable[[Settings], BaseEmbedding]


class EmbeddingFactory:
    """Embedding 工厂。

    通过 provider 名称路由到已注册的 Embedding 构建器。
    """

    _registry: dict[str, EmbeddingBuilder] = {}

    @classmethod
    def register(cls, provider: str, builder: EmbeddingBuilder) -> None:
        """注册 provider 对应的 Embedding 构建器。

        参数:
            provider: provider 名称。
            builder: 接收 Settings 并返回 BaseEmbedding 的构建器。
        """

        normalized_provider = provider.strip().lower()
        if not normalized_provider:
            raise ValueError("provider 不能为空")
        cls._registry[normalized_provider] = builder

    @classmethod
    def create(cls, settings: Settings) -> BaseEmbedding:
        """根据配置创建 Embedding 实例。

        参数:
            settings: 项目全局配置对象。

        返回:
            BaseEmbedding 的具体实现实例。

        异常:
            ValueError: 当 provider 未注册时抛出。
        """

        provider = settings.embedding.provider.strip().lower()
        if not provider:
            raise ValueError("embedding.provider 不能为空")

        builder = cls._registry.get(provider)
        if builder is None:
            raise ValueError(f"未注册的 embedding provider: {provider}")

        return builder(settings)

