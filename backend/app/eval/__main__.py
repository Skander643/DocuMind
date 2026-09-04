"""CLI: python -m app.eval [--limit N] [--gold path]"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.eval.ragas_eval import GOLD_PATH, run_batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DocuMind RAGAS batch (Phase 4)")
    parser.add_argument("--gold", default=str(GOLD_PATH), help="Path to gold_qa.json")
    parser.add_argument("--limit", type=int, default=None, help="Score only the first N items")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        payload = run_batch(args.gold, limit=args.limit)
    except Exception as exc:
        print(f"Eval failed: {exc}", file=sys.stderr)
        return 2
    metrics = payload.get("metrics") or {}
    print(json.dumps({"n_questions": payload.get("n_questions"), **metrics}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
