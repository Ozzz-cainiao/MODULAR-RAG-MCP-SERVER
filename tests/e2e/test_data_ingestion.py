"""E2E tests for the ingest CLI entry point."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import ingest


class FakePipeline:
    """Fake pipeline used to test CLI behavior without external dependencies."""

    def __init__(self, settings) -> None:
        self.settings = settings

    def run(self, path: str, collection: str, force: bool = False):
        from ingestion.pipeline import PipelineResult

        file_name = Path(path).name
        if "skip" in file_name:
            return PipelineResult(
                file_hash="hash",
                document_id=None,
                chunk_count=0,
                dense_vector_count=0,
                sparse_vector_count=0,
                vector_ids=[],
                stored_image_paths=[],
                skipped=True,
            )

        return PipelineResult(
            file_hash="hash",
            document_id="doc-001",
            chunk_count=3,
            dense_vector_count=3,
            sparse_vector_count=3,
            vector_ids=["v1", "v2", "v3"],
            stored_image_paths=[],
            skipped=False,
        )


def test_ingest_cli_when_success_then_return_zero_and_print_summary(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """CLI 成功时应返回 0 并打印摘要。"""

    fixture = tmp_path / "simple.pdf"
    fixture.write_bytes(b"%PDF")
    monkeypatch.setattr(ingest, "IngestionPipeline", FakePipeline)

    exit_code = ingest.main(
        ["--collection", "test-col", "--path", str(fixture), "--settings", "config/settings.yaml"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Ingested" in output
    assert "chunks=3" in output


def test_ingest_cli_when_unchanged_then_return_zero_and_print_skip(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """CLI 跳过未变更文件时应返回 0。"""

    fixture = tmp_path / "skip.pdf"
    fixture.write_bytes(b"%PDF")
    monkeypatch.setattr(ingest, "IngestionPipeline", FakePipeline)

    exit_code = ingest.main(
        ["--collection", "test-col", "--path", str(fixture), "--settings", "config/settings.yaml"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Skipped unchanged file" in output
