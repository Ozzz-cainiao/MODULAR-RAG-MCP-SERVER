"""Modular RAG MCP Server 应用入口。"""

from __future__ import annotations

from core.settings import SettingsValidationError, load_settings
from observability.logger import get_logger


def main() -> int:
    """加载配置并在配置无效时快速失败。"""
    logger = get_logger("bootstrap")

    try:
        settings = load_settings("config/settings.yaml")
    except (FileNotFoundError, SettingsValidationError) as error:
        logger.error("Failed to load settings: %s", error)
        return 1

    logger.info("Settings loaded successfully. LLM provider: %s", settings.llm.provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
