"""JSON-RPC protocol handling for the MCP server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


JSON = dict[str, Any]
ToolHandler = Callable[[dict[str, Any] | None], dict[str, Any]]


@dataclass(slots=True)
class ToolDefinition:
    """Registered MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class JsonRpcError(RuntimeError):
    """Structured JSON-RPC error."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message}


class ProtocolHandler:
    """Handle initialize/tools/list/tools/call JSON-RPC messages."""

    def __init__(
        self,
        tools: list[ToolDefinition] | None = None,
        server_name: str = "modular-rag-mcp-server",
        server_version: str = "0.1.0",
    ) -> None:
        self._tool_map = {tool.name: tool for tool in (tools or [])}
        self._server_name = server_name
        self._server_version = server_version

    def handle_request(self, request: JSON) -> JSON:
        """Process a JSON-RPC request object."""

        if not isinstance(request, dict):
            raise JsonRpcError(-32600, "Invalid Request")

        jsonrpc = request.get("jsonrpc")
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})

        if jsonrpc != "2.0" or not isinstance(method, str):
            raise JsonRpcError(-32600, "Invalid Request")

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list()
            elif method == "tools/call":
                result = self._handle_tools_call_request(params)
            else:
                raise JsonRpcError(-32601, "Method not found")
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except JsonRpcError:
            raise
        except Exception:
            raise JsonRpcError(-32603, "Internal error") from None

    def handle_initialize(self, params: dict[str, Any] | None) -> JSON:
        """Return server capabilities and identity."""

        if params is not None and not isinstance(params, dict):
            raise JsonRpcError(-32602, "Invalid params")
        return {
            "serverInfo": {
                "name": self._server_name,
                "version": self._server_version,
            },
            "capabilities": {
                "tools": {},
            },
        }

    def handle_tools_list(self) -> JSON:
        """Return the registered tool schema list."""

        return {"tools": [tool.to_dict() for tool in self._tool_map.values()]}

    def handle_tools_call(
        self,
        name: str,
        arguments: dict[str, Any] | None,
    ) -> JSON:
        """Dispatch a tool call and normalize failures."""

        if not isinstance(name, str) or not name.strip():
            raise JsonRpcError(-32602, "Invalid params")

        tool = self._tool_map.get(name)
        if tool is None:
            raise JsonRpcError(-32601, "Method not found")

        if arguments is not None and not isinstance(arguments, dict):
            raise JsonRpcError(-32602, "Invalid params")

        try:
            return tool.handler(arguments or {})
        except JsonRpcError:
            raise
        except ValueError as error:
            raise JsonRpcError(-32602, str(error)) from None
        except FileNotFoundError as error:
            raise JsonRpcError(-32602, str(error)) from None
        except Exception:
            raise JsonRpcError(-32603, "Internal error") from None

    def _handle_tools_call_request(self, params: dict[str, Any] | None) -> JSON:
        if not isinstance(params, dict):
            raise JsonRpcError(-32602, "Invalid params")
        if "name" not in params:
            raise JsonRpcError(-32602, "Invalid params")
        arguments = params.get("arguments", {})
        return self.handle_tools_call(str(params["name"]), arguments)
