"""CLI entry point for evaluation runs."""

from __future__ import annotations

import argparse
import json
import sys

from core.query_engine import HybridSearch
from core.settings import load_settings
from libs.evaluator.evaluator_factory import EvaluatorFactory
from observability.evaluation import EvalRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run retrieval evaluation against a golden set.")
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--test-set", default="tests/fixtures/golden_test_set.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.settings)
    runner = EvalRunner(
        settings=settings,
        hybrid_search=HybridSearch(settings),
        evaluator=EvaluatorFactory.create(settings),
    )
    report = runner.run(args.test_set)
    print(json.dumps({"hit_rate": report.hit_rate, "mrr": report.mrr}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
