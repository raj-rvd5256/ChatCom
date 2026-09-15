"""Run one customer-support question through the existing orchestrator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.orchestrator import orchestrate_customer_support  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+", help="Complete customer question")
    parser.add_argument(
        "--evaluation",
        action="store_true",
        help="Print customer response and internal evaluation metadata",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    question = " ".join(arguments.question).strip()
    if not question:
        print("Customer question must not be empty.", file=sys.stderr)
        return 2

    try:
        result = orchestrate_customer_support(question)
    except Exception as exc:
        print(f"Customer-support execution failed: {exc}", file=sys.stderr)
        return 1

    if not arguments.evaluation:
        print(result["response"])
        return 0

    _print_evaluation(result)
    return 0


def _print_evaluation(result: dict[str, Any]) -> None:
    print(f"Customer-facing response: {result['response']}")
    print(f"Intent: {result['intent']}")
    print(f"Sentiment: {result['sentiment']}")
    print(f"Frustration level: {result['frustration_level']}")
    print(f"Answerability: {result.get('answerability_state', result['answerable'])}")
    print(f"Escalation decision: {'required' if result['escalation_required'] else 'not_required'}")
    print(f"Escalation reason: {result.get('escalation_reason') or 'none'}")
    print(f"Retrieved source IDs: {', '.join(result['retrieved_knowledge_ids']) or 'none'}")
    print(f"Documentation status: Excel={_status(result.get('excel_documentation_result'))}; JSONL={_status(result.get('documentation_result'))}")
    print(f"Generation mode: {result['generation_mode']}")
    print(f"Guardrail result: {result['guardrail_result']}")


def _status(documentation_result: Any) -> str:
    if not isinstance(documentation_result, dict):
        return "unavailable"
    return "success" if documentation_result.get("success") else "failed"


if __name__ == "__main__":
    raise SystemExit(main())
