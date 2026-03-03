"""LLM Reranker 默认实现。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from core.settings import Settings
from libs.llm.base_llm import BaseLLM
from libs.llm.llm_factory import LLMFactory
from libs.reranker.base_reranker import BaseReranker, RerankCandidate, TraceContext


class LLMReranker(BaseReranker):
    """基于 LLM 的候选重排器。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 LLMReranker。"""

        super().__init__(settings)
        self.llm: BaseLLM = LLMFactory.create(settings)
        self.prompt_template = _load_rerank_prompt()

    def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        trace: TraceContext | None = None,
    ) -> list[RerankCandidate]:
        """调用 LLM 对候选进行结构化重排。"""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if not isinstance(candidates, list):
            raise ValueError("candidates 必须是列表")
        if not candidates:
            return []

        candidate_view = _normalize_candidates(candidates)
        prompt = _render_prompt(self.prompt_template, query.strip(), candidate_view)

        messages = [
            {
                "role": "system",
                "content": "你是重排器，只返回严格 JSON：{\"ranked_ids\":[\"id1\",\"id2\"]}",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        try:
            llm_output = self.llm.chat(messages)
        except Exception:
            return _build_fallback_candidates(candidates)

        ranked_ids = _parse_ranked_ids(llm_output)
        return _reorder_candidates(candidates, ranked_ids)


def _load_rerank_prompt() -> str:
    """读取 rerank prompt 模板。"""

    prompt_path = Path(os.getenv("RERANK_PROMPT_PATH", "config/prompts/rerank.txt"))
    if prompt_path.exists():
        content = prompt_path.read_text(encoding="utf-8").strip()
        if content:
            return content

    return (
        "请根据 query 对候选进行相关性重排。\n"
        "query: {query}\n"
        "candidates: {candidates_json}\n"
        "仅输出 JSON：{\"ranked_ids\":[\"...\"]}"
    )


def _normalize_candidates(candidates: list[RerankCandidate]) -> list[dict[str, str]]:
    """提取候选的最小输入视图。"""

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            raise ValueError(f"candidates[{index}] 必须是 dict")

        chunk_id = item.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError(f"candidates[{index}].chunk_id 必须是非空字符串")

        text_value = item.get("text", "")
        text = text_value if isinstance(text_value, str) else str(text_value)

        normalized.append({"chunk_id": chunk_id, "text": text})
    return normalized


def _render_prompt(template: str, query: str, candidates: list[dict[str, str]]) -> str:
    """渲染 prompt 模板。"""

    candidates_json = json.dumps(candidates, ensure_ascii=False)
    if "{query}" in template and "{candidates_json}" in template:
        rendered = template.replace("{query}", query)
        rendered = rendered.replace("{candidates_json}", candidates_json)
        return rendered

    return f"{template}\n\nquery: {query}\ncandidates: {candidates_json}"


def _parse_ranked_ids(llm_output: str) -> list[str]:
    """解析 LLM 返回的 ranked_ids。"""

    try:
        parsed = json.loads(llm_output)
    except json.JSONDecodeError as error:
        raise ValueError("LLM 重排输出不是合法 JSON") from error

    if not isinstance(parsed, dict):
        raise ValueError("LLM 重排输出必须是 JSON 对象")

    ranked_ids = parsed.get("ranked_ids")
    if not isinstance(ranked_ids, list) or not ranked_ids:
        raise ValueError("LLM 重排输出缺少 ranked_ids 列表")

    if not all(isinstance(item, str) and item.strip() for item in ranked_ids):
        raise ValueError("LLM 重排输出 ranked_ids 必须是非空字符串列表")

    return [item.strip() for item in ranked_ids]


def _reorder_candidates(candidates: list[RerankCandidate], ranked_ids: list[str]) -> list[RerankCandidate]:
    """按 ranked_ids 重排候选，并校验 schema 完整性。"""

    candidate_map: dict[str, RerankCandidate] = {}
    for index, candidate in enumerate(candidates):
        chunk_id = candidate.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError(f"candidates[{index}].chunk_id 必须是非空字符串")
        if chunk_id in candidate_map:
            raise ValueError(f"候选 chunk_id 重复: {chunk_id}")
        candidate_map[chunk_id] = dict(candidate)

    if len(set(ranked_ids)) != len(ranked_ids):
        raise ValueError("LLM 重排输出包含重复 chunk_id")

    candidate_ids = set(candidate_map.keys())
    ranked_id_set = set(ranked_ids)
    if ranked_id_set != candidate_ids:
        raise ValueError("LLM 重排输出 ranked_ids 与候选集合不一致")

    return [candidate_map[item] for item in ranked_ids]


def _build_fallback_candidates(candidates: list[RerankCandidate]) -> list[RerankCandidate]:
    """在 LLM 失败时返回可回退信号。"""

    fallback: list[RerankCandidate] = []
    for candidate in candidates:
        copied = dict(candidate)
        metadata = copied.get("metadata")
        if isinstance(metadata, dict):
            metadata_with_signal = dict(metadata)
        else:
            metadata_with_signal = {}
        metadata_with_signal["rerank_fallback"] = "llm_failed"
        copied["metadata"] = metadata_with_signal
        fallback.append(copied)
    return fallback
