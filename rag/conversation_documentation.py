"""Append-only local conversation evidence recording."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parents[1] / "data/evaluation/conversation_evidence.jsonl"
REQUIRED_FIELDS = (
    "conversation_id",
    "timestamp",
    "customer_question",
    "intent",
    "sentiment",
    "retrieved_knowledge_ids",
    "response",
    "escalation_decision",
    "guardrail_result",
    "generation_mode",
)
ESCALATION_DECISIONS = {"not_required", "recommended", "required", "confirmed_by_tool"}
GENERATION_MODES = {"deterministic_retrieved_knowledge", "llm_grounded", "unavailable"}
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_ -]?key|password|passwd|secret|access[_ -]?token|bearer)\s*[:=]\s*[^\s,}]+"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    re.compile(r"(?i)(sk-[a-z0-9_-]{8,}|gh[pousr]_[a-z0-9_]{8,})"),
)
PAYMENT_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?!\d{4}-\d{2}-\d{2}(?!\d))(?:\+?\d[\d ()-]{8,}\d)(?!\d)")


def record_conversation_evidence(
    *,
    conversation_id: str,
    timestamp: str,
    customer_question: str,
    intent: str,
    sentiment: str,
    retrieved_knowledge_ids: list[str],
    response: str,
    escalation_decision: str,
    escalation_reason: Optional[str] = None,
    guardrail_result: str,
    generation_mode: str,
    evaluation_metadata: Optional[dict[str, Any]] = None,
    destination: Path = DEFAULT_EVIDENCE_PATH,
    escalation_tool_confirmation: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Validate and append one minimal evidence record, idempotently."""

    record = {
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "customer_question": customer_question,
        "intent": intent,
        "sentiment": sentiment,
        "retrieved_knowledge_ids": retrieved_knowledge_ids,
        "response": response,
        "escalation_decision": escalation_decision,
        "escalation_reason": escalation_reason,
        "guardrail_result": guardrail_result,
        "generation_mode": generation_mode,
    }
    if evaluation_metadata is not None:
        record["evaluation_metadata"] = evaluation_metadata
    if escalation_tool_confirmation is not None:
        record["escalation_tool_confirmation"] = escalation_tool_confirmation

    failures = _validate_record(record)
    if failures:
        return {"success": False, "error": {"code": "invalid_evidence", "failures": failures}}

    evidence_id = _evidence_id(record)
    record["evidence_id"] = evidence_id
    serialized = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    destination = Path(destination)
    try:
        existing = _read_existing(destination)
        for prior in existing:
            if prior.get("evidence_id") == evidence_id:
                if prior == record:
                    return {"success": True, "duplicate": True, "evidence_id": evidence_id, "path": str(destination)}
                return {"success": False, "error": {"code": "duplicate_conflict", "message": "evidence ID has conflicting content"}}
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
    except (OSError, json.JSONDecodeError) as exc:
        return {"success": False, "error": {"code": "write_failed", "message": str(exc)}}
    return {"success": True, "duplicate": False, "evidence_id": evidence_id, "path": str(destination)}


def _validate_record(record: dict[str, Any]) -> list[str]:
    failures = [field for field in REQUIRED_FIELDS if field not in record]
    for field in REQUIRED_FIELDS:
        if field in record and record[field] in (None, ""):
            failures.append(f"missing:{field}")
    if not isinstance(record.get("retrieved_knowledge_ids"), list):
        failures.append("retrieved_knowledge_ids must be a list")
    if record.get("escalation_decision") not in ESCALATION_DECISIONS:
        failures.append("invalid:escalation_decision")
    if record.get("escalation_decision") in {"recommended", "required"} and not record.get("escalation_reason"):
        failures.append("missing:escalation_reason")
    if record.get("escalation_decision") == "confirmed_by_tool" and not record.get("escalation_tool_confirmation"):
        failures.append("missing:escalation_tool_confirmation")
    if record.get("generation_mode") not in GENERATION_MODES:
        failures.append("invalid:generation_mode")
    try:
        datetime.fromisoformat(str(record.get("timestamp")).replace("Z", "+00:00"))
    except ValueError:
        failures.append("invalid:timestamp")
    customer_values = [record.get("customer_question", ""), record.get("evaluation_metadata", {})]
    for value in _string_values(customer_values):
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            failures.append("secret_detected")
        if EMAIL_PATTERN.search(value) or PHONE_PATTERN.search(value):
            failures.append("unnecessary_personal_information_detected")
    generated_values = [record.get("response", "")]
    for value in _string_values(generated_values):
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            failures.append("secret_detected")
        if PAYMENT_PATTERN.search(value):
            failures.append("payment_data_detected")
    return sorted(set(failures))


def _string_values(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_values(item)


def _evidence_id(record: dict[str, Any]) -> str:
    identity = {key: record[key] for key in ("conversation_id", "timestamp", "response")}
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "evidence-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _read_existing(destination: Path) -> list[dict[str, Any]]:
    if not destination.exists():
        return []
    records = []
    for line in destination.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records