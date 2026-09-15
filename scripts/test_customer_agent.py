"""Demonstrate the local customer-support answer agent against golden examples."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.customer_agent import answer_customer_question  # noqa: E402
from rag.knowledge_base import get_retriever  # noqa: E402


def main() -> int:
    golden_path = ROOT / "data" / "evaluation" / "golden_dataset.json"
    records = json.loads(golden_path.read_text())
    retriever = get_retriever(k=40)
    failures = []

    for record in records[:6]:
        result = answer_customer_question(record["question"], retriever=retriever)
        expected_ids = set(record["expected_knowledge_ids"])
        actual_ids = set(result["retrieved_knowledge_ids"])
        relevant = bool(actual_ids & expected_ids)
        print(f"\nQUESTION: {record['question']}")
        print(f"KNOWLEDGE IDS: {', '.join(result['retrieved_knowledge_ids']) or 'none'}")
        print(f"SUPPORTED: {'Yes' if result['supported'] else 'No'}")
        print(f"ANSWER: {result['answer']}")
        print(f"GOLDEN KNOWLEDGE MATCH: {'PASS' if relevant else 'FAIL'}")
        if not relevant:
            failures.append(record["test_id"])

    print("\nVALIDATION: " + ("PASS" if not failures else f"FAIL ({', '.join(failures)})"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())