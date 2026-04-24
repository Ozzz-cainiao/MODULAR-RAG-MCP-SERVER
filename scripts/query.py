"""CLI entry point for offline hybrid search."""

from __future__ import annotations

import argparse
import sys

from core.query_engine import HybridSearch, Reranker
from core.settings import load_settings


def build_parser() -> argparse.ArgumentParser:
    """Build the query CLI parser."""

    parser = argparse.ArgumentParser(description="Query the Modular RAG knowledge base.")
    parser.add_argument("--query", required=True, help="User query text.")
    parser.add_argument("--top-k", type=int, default=None, help="Maximum number of results to return.")
    parser.add_argument("--collection", default=None, help="Optional collection filter.")
    parser.add_argument("--verbose", action="store_true", help="Print dense/sparse/fusion intermediates.")
    parser.add_argument("--no-rerank", action="store_true", help="Skip the rerank stage.")
    parser.add_argument(
        "--settings",
        default="config/settings.yaml",
        help="Path to the project settings YAML.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the hybrid query CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings(args.settings)
    hybrid_search = HybridSearch(settings)
    reranker = Reranker(settings)
    search_result = hybrid_search.search(
        query=args.query,
        top_k=args.top_k,
        collection=args.collection,
    )

    if not search_result.fused_results:
        print("未找到相关文档，请先运行 ingest.py 摄取数据。")
        return 0

    final_results = (
        search_result.fused_results
        if args.no_rerank
        else reranker.rerank(
            query=args.query,
            candidates=search_result.fused_results,
            top_k=args.top_k or settings.retrieval.top_k,
        )
    )

    if args.verbose:
        _print_section("Dense", search_result.dense_results)
        _print_section("Sparse", search_result.sparse_results)
        _print_section("Fusion", search_result.fused_results)
        if not args.no_rerank:
            _print_section("Rerank", final_results)

    _print_section("Top-K", final_results)
    return 0


def _print_section(title: str, results: list) -> None:
    print(f"[{title}]")
    if not results:
        print("(empty)")
        return

    for index, result in enumerate(results, start=1):
        metadata = result.metadata
        source = metadata.get("source_path", "unknown")
        page = metadata.get("page", "-")
        excerpt = " ".join(result.text.split())[:120]
        print(
            f"{index}. score={result.score:.4f} source={source} page={page} "
            f"chunk={result.chunk_id} text={excerpt}"
        )


if __name__ == "__main__":
    sys.exit(main())
