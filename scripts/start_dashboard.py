"""Start the Streamlit dashboard."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from streamlit.web import cli as stcli  # type: ignore
    except ImportError:
        print("请先安装 streamlit 后再启动 Dashboard。", file=sys.stderr)
        return 1

    dashboard_path = Path(__file__).resolve().parents[1] / "src" / "observability" / "dashboard" / "app.py"
    sys.argv = ["streamlit", "run", str(dashboard_path)]
    stcli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
