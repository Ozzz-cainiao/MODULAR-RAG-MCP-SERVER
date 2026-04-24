"""Dashboard config reading helpers."""

from __future__ import annotations

from core.settings import Settings, load_settings


class ConfigService:
    def __init__(self, settings_path: str = "config/settings.yaml") -> None:
        self._settings_path = settings_path

    def load(self) -> Settings:
        return load_settings(self._settings_path)

    def summary(self) -> dict[str, str]:
        settings = self.load()
        return {
            "llm": settings.llm.provider,
            "embedding": settings.embedding.provider,
            "vector_store": settings.vector_store.provider,
            "rerank": settings.rerank.provider,
            "evaluation": settings.evaluation.provider,
        }
