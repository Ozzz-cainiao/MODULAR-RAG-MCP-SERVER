"""Modular RAG MCP Server 应用入口。"""

from __future__ import annotations

def main() -> int:
    """启动 MCP server。"""

    from mcp_server.server import main as server_main

    return server_main()


if __name__ == "__main__":
    raise SystemExit(main())
