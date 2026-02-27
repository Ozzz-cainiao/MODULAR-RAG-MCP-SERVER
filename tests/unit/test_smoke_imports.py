"""Smoke tests for top-level package imports."""

from pathlib import Path
import sys


def test_import_top_level_packages_when_src_path_added_then_success() -> None:
    """Ensure top-level project packages are importable."""
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    import core  # noqa: F401
    import ingestion  # noqa: F401
    import libs  # noqa: F401
    import mcp_server  # noqa: F401
    import observability  # noqa: F401

