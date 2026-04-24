"""List available document collections."""

from __future__ import annotations

from pathlib import Path


def list_collections(documents_root: str = "data/documents") -> dict[str, object]:
    """List collection directories under the documents root."""

    root = Path(documents_root)
    if not root.exists():
        return {
            "content": [{"type": "text", "text": "暂无可用集合。"}],
            "structuredContent": {"collections": []},
        }

    collections: list[dict[str, object]] = []
    for entry in sorted(path for path in root.iterdir() if path.is_dir()):
        document_count = len([path for path in entry.rglob("*") if path.is_file()])
        collections.append(
            {
                "name": entry.name,
                "document_count": document_count,
            }
        )

    return {
        "content": [
            {
                "type": "text",
                "text": "\n".join(
                    f"- {item['name']} ({item['document_count']} docs)" for item in collections
                )
                or "暂无可用集合。",
            }
        ],
        "structuredContent": {"collections": collections},
    }


def tool_entry(arguments: dict[str, object] | None = None) -> dict[str, object]:
    payload = arguments or {}
    documents_root = str(payload["documents_root"]) if payload.get("documents_root") else "data/documents"
    return list_collections(documents_root=documents_root)
