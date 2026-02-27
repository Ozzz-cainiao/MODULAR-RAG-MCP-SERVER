"""项目日志工具。"""

from __future__ import annotations

import logging
import sys


def get_logger(name: str = "modular_rag") -> logging.Logger:
    """创建输出到标准错误流的日志器。

    参数:
        name: 日志器名称。

    返回:
        已配置好的日志器实例。
    """

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
