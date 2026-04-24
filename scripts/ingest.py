"""CLI entry point for offline data ingestion."""

from __future__ import annotations

import argparse
import sys

from core.settings import load_settings
from ingestion.pipeline import IngestionPipeline, PipelineError


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the ingestion script."""

    parser = argparse.ArgumentParser(description="Ingest a document into the Modular RAG pipeline.")
    parser.add_argument("--collection", required=True, help="Collection name for stored artifacts.")
    parser.add_argument("--path", required=True, help="Path to the source document.")
    parser.add_argument("--force", action="store_true", help="Reprocess even if the file hash exists.")
    parser.add_argument(
        "--settings",
        default="config/settings.yaml",
        help="Path to the project settings YAML.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the ingestion CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    settings = load_settings(args.settings)
    pipeline = IngestionPipeline(settings)
    try:
        result = pipeline.run(
            path=args.path,
            collection=args.collection,
            force=args.force,
        )
    except PipelineError as error:
        print(str(error), file=sys.stderr)
        return 1

    if result.skipped:
        print(f"Skipped unchanged file: {args.path}")
    else:
        print(
            f"Ingested {args.path} -> chunks={result.chunk_count} "
            f"dense={result.dense_vector_count} sparse={result.sparse_vector_count}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
