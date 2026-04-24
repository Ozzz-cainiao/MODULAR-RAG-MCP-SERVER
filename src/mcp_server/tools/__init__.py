"""MCP 工具定义模块。"""

from mcp_server.protocol_handler import ToolDefinition
from mcp_server.tools.get_document_summary import tool_entry as get_document_summary_tool
from mcp_server.tools.list_collections import tool_entry as list_collections_tool
from mcp_server.tools.query_knowledge_hub import tool_entry as query_knowledge_hub_tool


def get_tool_definitions() -> list[ToolDefinition]:
    """Return the registered MCP tools."""

    return [
        ToolDefinition(
            name="query_knowledge_hub",
            description="执行混合检索并返回带引用的相关片段。",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "collection": {"type": "string"},
                },
                "required": ["query"],
            },
            handler=query_knowledge_hub_tool,
        ),
        ToolDefinition(
            name="list_collections",
            description="列出当前知识库中的集合。",
            input_schema={"type": "object", "properties": {}},
            handler=list_collections_tool,
        ),
        ToolDefinition(
            name="get_document_summary",
            description="返回指定文档的摘要和元信息。",
            input_schema={
                "type": "object",
                "properties": {"doc_id": {"type": "string"}},
                "required": ["doc_id"],
            },
            handler=get_document_summary_tool,
        ),
    ]
