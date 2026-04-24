"""Minimal stdio MCP server."""

from __future__ import annotations

import json
import sys

from mcp_server.protocol_handler import JsonRpcError, ProtocolHandler
from mcp_server.tools import get_tool_definitions
from observability.logger import get_logger


def main() -> int:
    """Serve JSON-RPC requests from stdin and write responses to stdout."""

    logger = get_logger("mcp_server")
    handler = ProtocolHandler(get_tool_definitions())
    logger.info("MCP server started")

    for raw_line in sys.stdin:
        message = raw_line.strip()
        if not message:
            continue
        try:
            request = json.loads(message)
            response = handler.handle_request(request)
        except json.JSONDecodeError:
            response = _error_response(None, JsonRpcError(-32600, "Invalid Request"))
        except JsonRpcError as error:
            request_id = request.get("id") if isinstance(locals().get("request"), dict) else None
            response = _error_response(request_id, error)

        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    logger.info("MCP server stopped")
    return 0


def _error_response(request_id: object, error: JsonRpcError) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error.to_dict(),
    }
