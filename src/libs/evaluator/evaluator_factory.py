"""EvaluatorFactory：按配置构建 Evaluator 实例。"""

from __future__ import annotations

from collections.abc import Callable

from core.settings import Settings
from libs.evaluator.base_evaluator import BaseEvaluator
from libs.evaluator.custom_evaluator import CustomEvaluator


EvaluatorBuilder = Callable[[Settings], BaseEvaluator]


class EvaluatorFactory:
    """Evaluator 工厂。

    通过 provider 名称路由到已注册的 Evaluator 构建器。
    """

    _registry: dict[str, EvaluatorBuilder] = {"custom": CustomEvaluator}

    @classmethod
    def register(cls, provider: str, builder: EvaluatorBuilder) -> None:
        """注册 provider 对应的 Evaluator 构建器。

        参数:
            provider: provider 名称。
            builder: 接收 Settings 并返回 BaseEvaluator 的构建器。
        """

        normalized_provider = provider.strip().lower()
        if not normalized_provider:
            raise ValueError("provider 不能为空")
        cls._registry[normalized_provider] = builder

    @classmethod
    def create(cls, settings: Settings) -> BaseEvaluator:
        """根据配置创建 Evaluator 实例。

        参数:
            settings: 项目全局配置对象。

        返回:
            BaseEvaluator 的具体实现实例。

        异常:
            ValueError: 当 provider 未注册时抛出。
        """

        provider = settings.evaluation.provider.strip().lower()
        if not provider:
            raise ValueError("evaluation.provider 不能为空")

        builder = cls._registry.get(provider)
        if builder is None:
            raise ValueError(f"未注册的 evaluation provider: {provider}")

        return builder(settings)

