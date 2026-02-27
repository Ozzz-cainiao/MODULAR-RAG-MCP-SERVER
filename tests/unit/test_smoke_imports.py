"""顶层包导入的冒烟测试。"""

from pathlib import Path
import sys


def test_import_top_level_packages_when_src_path_added_then_success() -> None:
    """确保项目顶层包可被成功导入。"""
    repo_root = Path(__file__).resolve().parents[2]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    import core
    import ingestion
    import libs
    import mcp_server
    import observability

    assert core is not None
    assert ingestion is not None
    assert libs is not None
    assert mcp_server is not None
    assert observability is not None
