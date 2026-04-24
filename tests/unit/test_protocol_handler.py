"""Unit tests for the MCP protocol handler."""

from __future__ import annotations

from mcp_server.protocol_handler import JsonRpcError, ProtocolHandler, ToolDefinition


def _build_handler() -> ProtocolHandler:
    def echo_tool(arguments: dict[str, object] | None) -> dict[str, object]:
        payload = arguments or {}
        if "message" not in payload:
            raise ValueError("message is required")
        return {"content": [{"type": "text", "text": str(payload["message"])}]}

    tools = [
        ToolDefinition(
            name="echo",
            description="Echo the provided message.",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
            handler=echo_tool,
        )
    ]
    return ProtocolHandler(tools=tools, server_version="test")


def test_protocol_handler_when_initialize_then_return_capabilities() -> None:
    handler = _build_handler()

    response = handler.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )

    assert response["result"]["serverInfo"]["name"] == "modular-rag-mcp-server"
    assert "tools" in response["result"]["capabilities"]


def test_protocol_handler_when_tools_list_then_return_schema() -> None:
    handler = _build_handler()

    response = handler.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    assert response["result"]["tools"][0]["name"] == "echo"
    assert response["result"]["tools"][0]["inputSchema"]["type"] == "object"


def test_protocol_handler_when_tools_call_then_route_to_tool() -> None:
    handler = _build_handler()

    response = handler.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"message": "hello"}},
        }
    )

    assert response["result"]["content"][0]["text"] == "hello"


def test_protocol_handler_when_method_unknown_then_raise_jsonrpc_error() -> None:
    handler = _build_handler()

    try:
        handler.handle_request({"jsonrpc": "2.0", "id": 4, "method": "unknown"})
    except JsonRpcError as error:
        assert error.code == -32601
    else:
        raise AssertionError("Expected JsonRpcError for unknown method")


def test_protocol_handler_when_tool_params_invalid_then_raise_invalid_params() -> None:
    handler = _build_handler()

    try:
        handler.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {}},
            }
        )
    except JsonRpcError as error:
        assert error.code == -32602
        assert "message is required" in error.message
    else:
        raise AssertionError("Expected JsonRpcError for invalid params")
