"""TraceContext 最小实现。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TraceStage:
    """单个追踪阶段记录。"""

    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class TraceContext:
    """追踪上下文最小实现。"""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stages: list[TraceStage] = field(default_factory=list)
    finished_at: str | None = None

    def record_stage(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """记录阶段信息。"""

        if not isinstance(name, str) or not name.strip():
            raise ValueError("stage name 必须是非空字符串")
        self.stages.append(TraceStage(name=name.strip(), metadata=metadata or {}))

    def finish(self) -> None:
        """标记追踪结束。"""

        self.finished_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""

        return {
            "trace_id": self.trace_id,
            "stages": [
                {"name": stage.name, "metadata": stage.metadata, "started_at": stage.started_at}
                for stage in self.stages
            ],
            "finished_at": self.finished_at,
        }
