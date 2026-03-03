"""RerankerFactory：按配置构建 Reranker 实例。"""

from __future__ import annotations

from collections.abc import Callable

from core.settings import Settings
from libs.reranker.base_reranker import BaseReranker, RerankCandidate, TraceContext
from libs.reranker.llm_reranker import LLMReranker


RerankerBuilder = Callable[[Settings], BaseReranker]


class NoneReranker(BaseReranker):
    """默认回退 Reranker。

    保持输入候选顺序不变。
    """

    def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        trace: TraceContext | None = None,
    ) -> list[RerankCandidate]:
        """不做重排，直接返回原顺序候选。"""

        return list(candidates)


class RerankerFactory:
    """Reranker 工厂。

    通过 provider 名称路由到已注册的 Reranker 构建器。
    """

    _registry: dict[str, RerankerBuilder] = {
        "none": NoneReranker,
        "llm": LLMReranker,
    }

    @classmethod
    def register(cls, provider: str, builder: RerankerBuilder) -> None:
        """注册 provider 对应的 Reranker 构建器。

        参数:
            provider: provider 名称。
            builder: 接收 Settings 并返回 BaseReranker 的构建器。
        """

        normalized_provider = provider.strip().lower()
        if not normalized_provider:
            raise ValueError("provider 不能为空")
        cls._registry[normalized_provider] = builder

    @classmethod
    def create(cls, settings: Settings) -> BaseReranker:
        """根据配置创建 Reranker 实例。

        参数:
            settings: 项目全局配置对象。

        返回:
            BaseReranker 的具体实现实例。

        异常:
            ValueError: 当 provider 未注册时抛出。
        """

        provider = settings.rerank.provider.strip().lower()
        if not provider:
            raise ValueError("rerank.provider 不能为空")

        builder = cls._registry.get(provider)
        if builder is None:
            raise ValueError(f"未注册的 rerank provider: {provider}")

        return builder(settings)
