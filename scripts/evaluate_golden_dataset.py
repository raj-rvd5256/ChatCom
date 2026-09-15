"""Evaluate every Golden Dataset record through the local support orchestrator."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.knowledge_base import get_retriever  # noqa: E402
from rag.orchestrator import orchestrate_customer_support  # noqa: E402

GOLDEN_PATH = ROOT / "data/evaluation/golden_dataset.json"
DEFAULT_REPORT_PATH = ROOT / "data/evaluation/evaluation_report.md"
TOKEN_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "how", "i", "if", "in", "is", "it", "me", "my", "of", "on", "or", "should",
    "the", "this", "to", "what", "when", "where", "with", "you", "your",
}
REQUIRED_RECORD_FIELDS = {
    "test_id", "question", "expected_answer", "expected_knowledge_ids", "category",
    "answerable", "evaluation_criteria",
}
EXPECTED_INTENTS = {
    "Shipping": {"shipping", "delivery_estimate"},
    "Delivery": {"delivery_estimate", "delivery_delay", "failed_delivery", "lost_delivery"},
    "Returns": {"return"},
    "Refunds": {"refund"},
    "Cancellation": {"cancellation"},
    "Account changes": {"account_change", "payment", "address_change"},
    "Order Status": {"order_status"},
    "Customer-service escalation": {"complaint", "escalation"},
    "FAQs": {"unsupported", "privacy"},
}


def load_golden_dataset(path: Path = GOLDEN_PATH) -> list[dict[str, Any]]:
    """Load and strictly validate the Golden Dataset schema."""

    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to load Golden Dataset: {exc}") from exc
    if not isinstance(records, list) or len(records) != 20:
        raise ValueError("Golden Dataset must contain exactly 20 records")

    seen_ids = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each Golden Dataset record must be an object")
        missing = REQUIRED_RECORD_FIELDS - set(record)
        if missing:
            raise ValueError(f"record is missing fields: {sorted(missing)}")
        test_id = record["test_id"]
        if not isinstance(test_id, str) or not test_id or test_id in seen_ids:
            raise ValueError(f"invalid or duplicate test_id: {test_id!r}")
        if not isinstance(record["question"], str) or not record["question"].strip():
            raise ValueError(f"{test_id} has an invalid question")
        if not isinstance(record["expected_knowledge_ids"], list) or not all(
            isinstance(value, str) and value for value in record["expected_knowledge_ids"]
        ):
            raise ValueError(f"{test_id} has invalid expected_knowledge_ids")
        if not isinstance(record["answerable"], bool):
            raise ValueError(f"{test_id} has a non-boolean answerable value")
        if record["category"] not in EXPECTED_INTENTS:
            raise ValueError(f"{test_id} has an unsupported category: {record['category']!r}")
        seen_ids.add(test_id)
    return records


def evaluate_records(
    records: Iterable[dict[str, Any]],
    *,
    retriever: Any = None,
    orchestrator: Callable[..., dict[str, Any]] = orchestrate_customer_support,
    evidence_directory: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Run deterministic evaluation checks for every supplied Golden record."""

    results = []
    for record in records:
        evidence_path = None
        if evidence_directory is not None:
            evidence_path = Path(evidence_directory) / f"{record['test_id']}.jsonl"
        actual = orchestrator(
            record["question"],
            retriever=retriever,
            documentation_destination=evidence_path,
        )
        checks = _evaluate_dimensions(record, actual)
        failures = [name for name, passed in checks.items() if not passed]
        results.append({
            "test_id": record["test_id"],
            "question": record["question"],
            "actual_response": actual.get("response", ""),
            "expected_answer": record["expected_answer"],
            "expected_knowledge_ids": record["expected_knowledge_ids"],
            "actual_retrieved_knowledge_ids": actual.get("retrieved_knowledge_ids", []),
            "intent": actual.get("intent"),
            "intent_confidence": actual.get("intent_confidence"),
            "sentiment": actual.get("sentiment"),
            "frustration_level": actual.get("frustration_level"),
            "answerable": actual.get("answerable"),
            "expected_answerable": record["answerable"],
            "escalation_required": actual.get("escalation_required"),
            "escalation_reason": actual.get("escalation_reason"),
            "generation_mode": actual.get("generation_mode"),
            "guardrail_result": actual.get("guardrail_result"),
            "documentation_result": actual.get("documentation_result"),
            "dimensions": checks,
            "status": "PASS" if not failures else "FAIL",
            "failure_reason": "; ".join(failures) if failures else None,
        })
    return results


def _evaluate_dimensions(record: dict[str, Any], actual: dict[str, Any]) -> dict[str, bool]:
    response = actual.get("response", "")
    expected_ids = set(record["expected_knowledge_ids"])
    actual_ids = set(actual.get("retrieved_knowledge_ids", []))
    expected_tokens = _tokens(record["expected_answer"])
    response_tokens = _tokens(response)
    token_coverage = len(expected_tokens & response_tokens) / len(expected_tokens) if expected_tokens else 1.0
    question = record["question"].lower()
    unsafe_live_terms = ("live order", "carrier status", "refund transaction", "payment change")
    safety_terms = ("unavailable", "human support", "cannot", "do not have", "escalat")
    prompt_injection = "ignore previous" in question or "system prompt" in question
    documentation = actual.get("documentation_result") or {}

    response_correctness = bool(actual_ids & expected_ids) and token_coverage >= 0.45
    if not record["answerable"]:
        response_correctness = any(term in response.lower() for term in safety_terms)
    groundedness = bool(actual_ids & expected_ids) or (
        not record["answerable"] and any(term in response.lower() for term in safety_terms)
    )
    answerability = actual.get("answerable") is record["answerable"]
    intent = actual.get("intent") in EXPECTED_INTENTS[record["category"]]
    sentiment = actual.get("sentiment") is not None and actual.get("frustration_level") is not None
    escalation = _expected_escalation(record, actual)
    unsupported = record["answerable"] or any(term in response.lower() for term in safety_terms)
    injection_resistance = not prompt_injection or (
        "prompt_injection_blocked" in str(actual.get("guardrail_result"))
        or actual.get("escalation_required") is True
    )
    missing_live_data = not any(term in response.lower() for term in unsafe_live_terms) or (
        actual.get("escalation_required") is True
    )
    traceability = bool(actual_ids & expected_ids) if expected_ids else not actual_ids
    evidence = documentation.get("success") is True
    return {
        "response_correctness": response_correctness,
        "groundedness": groundedness,
        "knowledge_id_traceability": traceability,
        "answerability_classification": answerability,
        "intent_classification": intent,
        "sentiment_handling": sentiment and (actual.get("frustration_level") != "high" or "frustrat" in response.lower()),
        "escalation_behavior": escalation,
        "unsupported_question_handling": unsupported,
        "prompt_injection_resistance": injection_resistance,
        "missing_live_data_handling": missing_live_data,
        "conversation_evidence_recording": evidence,
    }


def _expected_escalation(record: dict[str, Any], actual: dict[str, Any]) -> bool:
    question = record["question"].lower()
    requires = (
        not record["answerable"]
        or record["category"] in {"Delivery", "Refunds", "Cancellation", "Account changes", "Order Status", "Customer-service escalation"}
        or any(term in question for term in ("live", "right now", "frustrated", "repeatedly", "issue", "failed", "delayed", "damaged", "defective", "broken", "incorrect", "unusable"))
    )
    return actual.get("escalation_required") is requires or (requires and actual.get("escalation_required") is True)


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in TOKEN_STOP_WORDS and len(token) > 2
    }


def render_report(results: list[dict[str, Any]], run_id: str) -> str:
    passed = sum(result["status"] == "PASS" for result in results)
    failed = len(results) - passed
    dimensions = sorted(results[0]["dimensions"]) if results else []
    lines = [
        "# ChatCom Customer-Support Golden Dataset Evaluation",
        "",
        "## Summary",
        "",
        f"- Run identifier: `{run_id}`",
        f"- Golden records evaluated: {len(results)}",
        f"- Passed records: {passed}",
        f"- Failed records: {failed}",
        f"- Pass percentage: {(passed / len(results) * 100) if results else 0:.1f}%",
        "- Evaluation mode: deterministic local orchestrator; no external LLM or credentials",
        "",
        "## Results",
        "",
        "| Test ID | Intent | Expected IDs | Actual IDs | Answerable | Escalation | Evidence | Result | Failure reason |",
        "|---|---|---|---|---:|---:|---:|---|---|",
    ]
    for result in results:
        lines.append(
            f"| {result['test_id']} | {result['intent']} | {', '.join(result['expected_knowledge_ids'])} | "
            f"{', '.join(result['actual_retrieved_knowledge_ids']) or 'none'} | "
            f"{result['answerable']} | {result['escalation_required']} | "
            f"{(result['documentation_result'] or {}).get('success', False)} | {result['status']} | "
            f"{result['failure_reason'] or ''} |"
        )
    lines.extend(["", "## Dimension Summary", "", "| Dimension | Passed | Total |", "|---|---:|---:|"])
    for dimension in dimensions:
        count = sum(result["dimensions"][dimension] for result in results)
        lines.append(f"| {dimension} | {count} | {len(results)} |")
    lines.extend(["", "## Failure Reasons", ""])
    failures = [result for result in results if result["status"] == "FAIL"]
    lines.extend(f"- {result['test_id']}: {result['failure_reason']}" for result in failures)
    if not failures:
        lines.append("- None")
    lines.extend([
        "", "## Known Limitations", "",
        "- Intent and sentiment classification are deterministic keyword rules, not semantic models.",
        "- Token coverage and knowledge-ID overlap are explainable proxies, not human semantic judgment.",
        "- Live order, carrier, account, payment, refund, and address data are intentionally unavailable.",
        "- Evidence is written to temporary per-record JSONL files during evaluation.",
        "", "## Exact Command", "",
        "```bash",
        "/tmp/chatcom-langchain-venv/bin/python scripts/evaluate_golden_dataset.py",
        "```",
        "",
    ])
    return "\n".join(lines)


def run_evaluation(report_path: Path = DEFAULT_REPORT_PATH) -> list[dict[str, Any]]:
    records = load_golden_dataset()
    retriever = get_retriever(k=40)
    with tempfile.TemporaryDirectory(prefix="chatcom-evaluation-") as evidence_directory:
        results = evaluate_records(records, retriever=retriever, evidence_directory=Path(evidence_directory))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(results, run_id), encoding="utf-8")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()
    results = run_evaluation(args.output)
    passed = sum(result["status"] == "PASS" for result in results)
    print(f"evaluated={len(results)} passed={passed} failed={len(results) - passed}")
    for result in results:
        print(f"{result['test_id']} {result['status']} {result['failure_reason'] or ''}".rstrip())
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())