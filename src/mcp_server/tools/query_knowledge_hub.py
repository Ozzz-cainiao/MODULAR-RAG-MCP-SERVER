"""Primary MCP tool for hybrid retrieval."""

from __future__ import annotations

from core.query_engine import HybridSearch, Reranker
from core.response import ResponseBuilder
from core.settings import load_settings


def query_knowledge_hub(
    query: str,
    top_k: int | None = None,
    collection: str | None = None,
    hybrid_search: HybridSearch | None = None,
    reranker: Reranker | None = None,
    response_builder: ResponseBuilder | None = None,
    settings_path: str = "config/settings.yaml",
) -> dict[str, object]:
    """Run hybrid retrieval and build an MCP response."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query 必须是非空字符串")
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k 必须大于 0")

    settings = load_settings(settings_path)
    search = hybrid_search or HybridSearch(settings)
    ranker = reranker or Reranker(settings)
    builder = response_builder or ResponseBuilder()

    search_result = search.search(query=query, top_k=top_k, collection=collection)
    ranked_results = ranker.rerank(
        query=query,
        candidates=search_result.fused_results,
        top_k=top_k or settings.retrieval.top_k,
    )
    return builder.build(ranked_results, query)


def tool_entry(arguments: dict[str, object] | None = None) -> dict[str, object]:
    """Adapter for ProtocolHandler tool dispatch."""

    payload = arguments or {}
    return query_knowledge_hub(
        query=str(payload.get("query", "")),
        top_k=int(payload["top_k"]) if payload.get("top_k") is not None else None,
        collection=str(payload["collection"]) if payload.get("collection") is not None else None,
    )
