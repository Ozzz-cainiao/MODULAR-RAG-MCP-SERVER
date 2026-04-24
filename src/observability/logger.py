"""项目日志工具。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
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


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        trace_payload = getattr(record, "trace_payload", None)
        if isinstance(trace_payload, dict):
            payload.update(trace_payload)
        return json.dumps(payload, ensure_ascii=False)


def get_trace_logger(
    name: str = "modular_rag.trace",
    log_path: str = "logs/traces.jsonl",
) -> logging.Logger:
    """Create or reuse a logger that writes JSON Lines traces."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def write_trace(trace_dict: dict) -> None:
    """Append a single trace dict to the JSONL trace log."""

    logger = get_trace_logger()
    logger.info("trace", extra={"trace_payload": trace_dict})
