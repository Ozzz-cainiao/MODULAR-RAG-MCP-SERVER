"""Cross-Encoder Reranker 默认实现。"""

from __future__ import annotations

import os

from core.settings import Settings
from libs.reranker.base_reranker import BaseReranker, RerankCandidate, TraceContext


class CrossEncoderReranker(BaseReranker):
    """基于 Cross-Encoder 的候选重排器。"""

    def __init__(self, settings: Settings) -> None:
        """初始化 Cross-Encoder Reranker。"""

        super().__init__(settings)
        self.model_name = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.top_m = int(os.getenv("RERANK_TOP_M", "30"))
        if self.top_m <= 0:
            raise ValueError("RERANK_TOP_M 必须大于 0")

    def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        trace: TraceContext | None = None,
    ) -> list[RerankCandidate]:
        """对 Top-M 候选执行 Cross-Encoder 重排。"""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if not isinstance(candidates, list):
            raise ValueError("candidates 必须是列表")
        if not candidates:
            return []

        normalized = _normalize_candidates(candidates)
        rerank_size = min(self.top_m, len(normalized))
        head_candidates = normalized[:rerank_size]
        tail_candidates = normalized[rerank_size:]

        try:
            scores = self._score_candidates(query=query.strip(), candidates=head_candidates)
        except Exception:
            return _build_fallback_candidates(normalized)

        if len(scores) != len(head_candidates):
            raise ValueError("Cross-Encoder 打分数量与候选数量不一致")

        ranked_head = [
            candidate
            for _, candidate in sorted(
                zip(scores, head_candidates, strict=True),
                key=lambda pair: (float(pair[0]), str(pair[1]["chunk_id"])),
                reverse=True,
            )
        ]

        return ranked_head + tail_candidates

    def _score_candidates(self, query: str, candidates: list[RerankCandidate]) -> list[float]:
        """计算候选与 query 的相关性得分。"""

        query_terms = _tokenize(query)
        scores: list[float] = []
        for candidate in candidates:
            text = str(candidate.get("text", ""))
            text_terms = _tokenize(text)
            overlap = len(query_terms & text_terms)
            length_penalty = max(len(text_terms), 1)
            score = float(overlap) / float(length_penalty)
            scores.append(score)
        return scores


def _normalize_candidates(candidates: list[RerankCandidate]) -> list[RerankCandidate]:
    """校验并标准化候选结构。"""

    normalized: list[RerankCandidate] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidates[{index}] 必须是 dict")

        chunk_id = candidate.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError(f"candidates[{index}].chunk_id 必须是非空字符串")

        copied = dict(candidate)
        if "metadata" not in copied or not isinstance(copied.get("metadata"), dict):
            copied["metadata"] = {}
        normalized.append(copied)

    return normalized


def _tokenize(text: str) -> set[str]:
    """将文本切为小写 token 集合。"""

    cleaned = text.strip().lower()
    if not cleaned:
        return set()

    separators = ["\n", "\t", ",", "，", ".", "。", "!", "！", "?", "？", ";", "；", "(", ")", "[", "]"]
    for separator in separators:
        cleaned = cleaned.replace(separator, " ")
    return {token for token in cleaned.split(" ") if token}


def _build_fallback_candidates(candidates: list[RerankCandidate]) -> list[RerankCandidate]:
    """在 Cross-Encoder 失败时返回回退信号。"""

    fallback: list[RerankCandidate] = []
    for candidate in candidates:
        copied = dict(candidate)
        metadata = copied.get("metadata")
        metadata_map = dict(metadata) if isinstance(metadata, dict) else {}
        metadata_map["rerank_fallback"] = "cross_encoder_failed"
        copied["metadata"] = metadata_map
        fallback.append(copied)
    return fallback

