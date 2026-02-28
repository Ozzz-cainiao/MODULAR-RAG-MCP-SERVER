"""配置加载与校验工具。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


class SettingsValidationError(ValueError):
    """当配置缺少必填字段时抛出。"""


@dataclass(slots=True)
class ProviderSettings:
    """基于 provider 的配置段。

    属性:
        provider: 当前配置段对应的 provider 名称。
    """

    provider: str


@dataclass(slots=True)
class RetrievalSettings:
    """检索配置段。

    属性:
        top_k: 检索返回条数。
    """

    top_k: int


@dataclass(slots=True)
class ObservabilitySettings:
    """可观测性配置段。

    属性:
        level: 日志级别。
    """

    level: str


@dataclass(slots=True)
class Settings:
    """项目运行时配置。

    属性:
        llm: LLM provider 配置。
        embedding: Embedding provider 配置。
        splitter: Splitter provider 配置。
        vector_store: 向量存储 provider 配置。
        retrieval: 检索配置。
        rerank: 重排 provider 配置。
        evaluation: 评估 provider 配置。
        observability: 可观测性配置。
    """

    llm: ProviderSettings
    embedding: ProviderSettings
    splitter: ProviderSettings
    vector_store: ProviderSettings
    retrieval: RetrievalSettings
    rerank: ProviderSettings
    evaluation: ProviderSettings
    observability: ObservabilitySettings


def load_settings(path: str) -> Settings:
    """加载 YAML 配置并校验必填字段。

    参数:
        path: YAML 配置文件路径。

    返回:
        解析并校验后的配置对象。

    异常:
        SettingsValidationError: 当配置缺少必填字段时抛出。
        FileNotFoundError: 当配置文件不存在时抛出。
    """

    raw_data = _read_yaml(path)
    settings = _build_settings(raw_data)
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    """校验配置值合法性。

    参数:
        settings: 待校验的配置对象。

    异常:
        SettingsValidationError: 当必填字段缺失或值非法时抛出。
    """

    if not settings.llm.provider:
        raise SettingsValidationError("缺少必填字段: llm.provider")
    if not settings.embedding.provider:
        raise SettingsValidationError("缺少必填字段: embedding.provider")
    if not settings.splitter.provider:
        raise SettingsValidationError("缺少必填字段: splitter.provider")
    if not settings.vector_store.provider:
        raise SettingsValidationError("缺少必填字段: vector_store.provider")
    if settings.retrieval.top_k <= 0:
        raise SettingsValidationError("字段非法: retrieval.top_k 必须大于 0")
    if not settings.rerank.provider:
        raise SettingsValidationError("缺少必填字段: rerank.provider")
    if not settings.evaluation.provider:
        raise SettingsValidationError("缺少必填字段: evaluation.provider")
    if not settings.observability.level:
        raise SettingsValidationError("缺少必填字段: observability.level")


def _read_yaml(path: str) -> dict[str, object]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}

    if not isinstance(content, dict):
        raise SettingsValidationError("配置文件内容必须是映射结构")

    return content


def _build_settings(raw_data: dict[str, object]) -> Settings:
    llm = _build_provider_settings(raw_data, "llm")
    embedding = _build_provider_settings(raw_data, "embedding")
    splitter = _build_provider_settings(raw_data, "splitter")
    vector_store = _build_provider_settings(raw_data, "vector_store")
    rerank = _build_provider_settings(raw_data, "rerank")
    evaluation = _build_provider_settings(raw_data, "evaluation")
    retrieval = _build_retrieval_settings(raw_data)
    observability = _build_observability_settings(raw_data)

    return Settings(
        llm=llm,
        embedding=embedding,
        splitter=splitter,
        vector_store=vector_store,
        retrieval=retrieval,
        rerank=rerank,
        evaluation=evaluation,
        observability=observability,
    )


def _build_provider_settings(raw_data: dict[str, object], section: str) -> ProviderSettings:
    section_data = _require_mapping(raw_data, section)
    provider = _require_string(section_data, f"{section}.provider", "provider")
    return ProviderSettings(provider=provider)


def _build_retrieval_settings(raw_data: dict[str, object]) -> RetrievalSettings:
    section_data = _require_mapping(raw_data, "retrieval")
    top_k_value = section_data.get("top_k")
    if not isinstance(top_k_value, int):
        raise SettingsValidationError("缺少必填字段: retrieval.top_k")
    return RetrievalSettings(top_k=top_k_value)


def _build_observability_settings(raw_data: dict[str, object]) -> ObservabilitySettings:
    section_data = _require_mapping(raw_data, "observability")
    level = _require_string(section_data, "observability.level", "level")
    return ObservabilitySettings(level=level)


def _require_mapping(raw_data: dict[str, object], section: str) -> dict[str, object]:
    value = raw_data.get(section)
    if not isinstance(value, dict):
        raise SettingsValidationError(f"缺少必填字段: {section}")
    return value


def _require_string(data: dict[str, object], field_path: str, field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise SettingsValidationError(f"缺少必填字段: {field_path}")
    return value
