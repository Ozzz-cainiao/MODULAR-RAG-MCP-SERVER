"""Construct MCP tool responses."""

from __future__ import annotations

from core.response.citation_generator import CitationGenerator
from core.response.multimodal_assembler import MultimodalAssembler
from core.types import RetrievalResult


class ResponseBuilder:
    """Build Markdown and structured content for MCP tool responses."""

    def __init__(
        self,
        citation_generator: CitationGenerator | None = None,
        multimodal_assembler: MultimodalAssembler | None = None,
    ) -> None:
        self._citation_generator = citation_generator or CitationGenerator()
        self._multimodal_assembler = multimodal_assembler or MultimodalAssembler()

    def build(self, retrieval_results: list[RetrievalResult], query: str) -> dict[str, object]:
        """Build an MCP-compatible tool result."""

        citations = self._citation_generator.generate(retrieval_results)
        markdown = self._build_markdown(retrieval_results, query, citations)
        content = self._multimodal_assembler.build_content(markdown, retrieval_results)
        return {
            "content": content,
            "structuredContent": {
                "query": query,
                "result_count": len(retrieval_results),
                "citations": citations,
            },
        }

    def _build_markdown(
        self,
        retrieval_results: list[RetrievalResult],
        query: str,
        citations: list[dict[str, object]],
    ) -> str:
        if not retrieval_results:
            return f"未找到与“{query}”相关的文档内容，请先运行 ingest.py 摄取数据。"

        lines = [f"与“{query}”最相关的内容如下："]
        for citation, result in zip(citations, retrieval_results):
            excerpt = " ".join(result.text.split())
            lines.append(f"[{citation['index']}] {excerpt}")
        return "\n\n".join(lines)
