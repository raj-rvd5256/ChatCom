"""Deterministic local customer-support orchestrator."""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from rag.conversation_documentation import DEFAULT_EVIDENCE_PATH, record_conversation_evidence
from rag.customer_agent import answer_customer_question
from rag.excel_conversation_documentation import (
    DEFAULT_EXCEL_DOCUMENTATION_PATH,
    append_conversation_to_excel,
)
from rag.knowledge_retrieval_tool import retrieve_knowledge

INTENT_RULES = (
    ("prompt_injection", ("ignore previous", "system prompt", "reveal instructions", "developer message")),
    ("account_change", ("change my account", "update my account", "account change", "bank account", "account details", "close my account")),
    ("address_change", ("change my address", "update my address", "shipping address")),
    ("payment", ("change payment", "card number", "my card", "send my card", "payment method", "billing")),
    ("order_status", ("where is my order", "where my order", "order status", "track my order", "order tracking")),
    ("delivery_delay", ("delivery is late", "delivery is delayed", "late delivery", "delayed delivery", "delivery delay")),
    ("failed_delivery", ("delivery failed", "delivery attempt", "could not deliver")),
    ("lost_delivery", ("lost package", "package is lost", "delivery lost")),
    ("delivery_estimate", ("when will", "how long", "delivery time", "arrive", "shipping time")),
    ("refund", ("refund", "money back")),
    ("cancellation", ("cancel my", "cancellation", "cancel order", "cancel an order")),
    ("exchange", ("exchange", "swap item")),
    ("return", ("return", "send back", "damaged item", "arrived damaged", "damaged", "defective", "broken", "incorrect item", "wrong item", "unusable", "final-sale", "returns policy")),
    ("privacy", ("personal data", "privacy", "delete my data")),
    ("complaint", ("complaint", "unhappy", "disappointed", "terrible service", "repeatedly", "without resolution")),
    ("escalation", ("human agent", "speak to a person", "escalate")),
    ("shipping", ("shipping", "ship to", "international", "shipping cost", "shipping method")),
)

LIVE_DATA_INTENTS = {"order_status", "delivery_delay", "failed_delivery", "lost_delivery"}
PRIVILEGED_INTENTS = {"account_change", "address_change", "payment"}
HIGH_RISK_TERMS = ("legal", "lawsuit", "medical", "injury", "fraud", "stolen", "threat", "harm")
SECRET_PATTERN = re.compile(r"(?i)(api[_ -]?key|password|token|secret|bearer)\s*[:=]")
CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
INJECTION_TERMS = ("ignore previous", "reveal system", "show system prompt", "follow these instructions instead")
DAMAGED_ITEM_TERMS = ("damaged", "defective", "broken", "incorrect item", "wrong item", "unusable")
REVIEW_REQUEST_TERMS = ("replacement", "replace", "refund", "exception", "human review", "speak to a person")
UNSUPPORTED_PATTERNS = ("support hours", "customer-support hours", "customer support hours", "opening hours")


def orchestrate_customer_support(
    customer_question: str,
    *,
    retriever: Any = None,
    documentation_destination: Optional[Path] = None,
    excel_documentation_destination: Optional[Path] = None,
) -> dict[str, Any]:
    """Run one customer-support interaction in deterministic local mode."""

    conversation_id = f"conversation-{uuid.uuid4().hex}"
    timestamp = datetime.now(timezone.utc).isoformat()
    intent_result = classify_intent(customer_question)
    sentiment_result = detect_sentiment(customer_question)
    intent = intent_result["intent"]
    risk_reasons = _risk_reasons(customer_question, intent, sentiment_result)
    damaged_item = _contains_any(customer_question, DAMAGED_ITEM_TERMS)
    answerability_state = "directly_answerable"

    retrieval = retrieve_knowledge(
        customer_question,
        retrieval_config={"k": 40},
        retriever=retriever,
    )
    retrieved_ids = retrieval["knowledge_ids"]
    materially_supporting_ids = set()

    if intent in LIVE_DATA_INTENTS:
        answerability_state = "partially_answerable"
        if intent == "failed_delivery":
            response = "A failed delivery attempt requires human support to review the carrier outcome and next step. This service cannot confirm a reattempt or change the delivery address without live transactional tools."
        elif intent == "order_status":
            response = "I cannot see live order or carrier status. A live lookup requires human support, an order reference, and matching customer verification; I will not invent a delivery status or claim that an action was completed."
        else:
            response = "I cannot access live order, delivery, or carrier information in this local support service. Human support is required to review this request."
        response_status = "escalated"
    elif intent in PRIVILEGED_INTENTS or intent in {"privacy", "prompt_injection"}:
        answerability_state = "partially_answerable"
        response = "I cannot perform or confirm account, bank-account, address, payment, privacy, or other privileged changes here. Human support with privileged access is required to review the request; I will not request secrets or claim that a change was completed."
        response_status = "escalated"
    elif damaged_item:
        answerability_state = "partially_answerable"
        if retrieval["answerable"] and retrieval["retrieval_status"] == "success":
            answer = answer_customer_question(customer_question, retriever=retriever, k=40)
            response = answer["answer"]
            materially_supporting_ids = set(answer["retrieved_knowledge_ids"])
            retrieved_ids = list(dict.fromkeys(retrieved_ids + answer["retrieved_knowledge_ids"]))
        else:
            response = "A damaged, defective, broken, incorrect, or unusable item requires human review with evidence. The chatbot cannot approve a replacement, exception, or refund."
        response_status = "escalated"
    elif retrieval["answerable"] and retrieval["retrieval_status"] == "success":
        answer = answer_customer_question(customer_question, retriever=retriever, k=40)
        response = answer["answer"]
        response_status = "supported" if answer["supported"] else "unavailable"
        materially_supporting_ids = set(answer["retrieved_knowledge_ids"])
        retrieved_ids = list(dict.fromkeys(retrieved_ids + answer["retrieved_knowledge_ids"]))
    else:
        answerability_state = "not_answerable"
        response = "I do not have enough approved knowledge to answer that request. Human support may need to review it."
        response_status = "unavailable"

    if _contains_any(customer_question, UNSUPPORTED_PATTERNS):
        answerability_state = "not_answerable"
        response = "The available knowledge does not state a support schedule. Please use the current approved support contact page or support channel for the current hours; I will not invent a schedule."
        response_status = "unavailable"

    escalation_required = bool(risk_reasons) or any(
        metadata.get("knowledge_id") in materially_supporting_ids
        and _supporting_record_requires_escalation(customer_question, metadata)
        for metadata in retrieval["source_metadata"]
    )
    escalation_reason = ", ".join(dict.fromkeys(risk_reasons)) or None
    if escalation_required and escalation_reason is None:
        escalation_reason = "knowledge_base_escalation"

    if sentiment_result["frustration_level"] == "high" and "frustrating" not in response.lower():
        response = "I understand this has been frustrating. " + response
    if escalation_required and "Human support" not in response:
        response += " Human support may need to review this request."

    response_validation = validate_agent_response(
        customer_question,
        response,
        retrieved_ids,
        answerable=answerability_state != "not_answerable",
        escalation_required=escalation_required,
    )
    guardrail_result = "passed" if response_validation["valid"] else "failed:" + ",".join(response_validation["failures"])
    if not response_validation["valid"]:
        response = "I cannot safely provide that information from the approved knowledge base. Human support is required to review this request."
        response_status = "escalated"
        escalation_required = True
        escalation_reason = escalation_reason or "guardrail_rejection"

    try:
        excel_documentation = append_conversation_to_excel(
            conversation_id=conversation_id,
            timestamp=timestamp,
            customer_message=_documentation_question(customer_question, intent),
            agent_response=response,
            intent=intent,
            sentiment=sentiment_result["sentiment"],
            frustration_level=sentiment_result["frustration_level"],
            answerability=answerability_state,
            escalation_decision="required" if escalation_required else "not_required",
            escalation_reason=escalation_reason,
            retrieved_source_ids=retrieved_ids,
            generation_mode="deterministic_retrieved_knowledge" if response_status == "supported" else "unavailable",
            guardrail_result=guardrail_result,
            destination=excel_documentation_destination or DEFAULT_EXCEL_DOCUMENTATION_PATH,
        )
    except Exception as exc:
        excel_documentation = {
            "success": False,
            "path": str(excel_documentation_destination or DEFAULT_EXCEL_DOCUMENTATION_PATH),
            "error": {"code": "excel_documentation_failed", "message": str(exc)},
        }

    documentation = record_conversation_evidence(
        conversation_id=conversation_id,
        timestamp=timestamp,
        customer_question=_documentation_question(customer_question, intent),
        intent=intent,
        sentiment=sentiment_result["sentiment"],
        retrieved_knowledge_ids=retrieved_ids,
        response=response,
        escalation_decision="required" if escalation_required else "not_required",
        escalation_reason=escalation_reason,
        guardrail_result=guardrail_result,
        generation_mode="deterministic_retrieved_knowledge" if response_status == "supported" else "unavailable",
        destination=documentation_destination or DEFAULT_EVIDENCE_PATH,
    )

    errors = []
    if retrieval["limitation_or_error"]:
        errors.append(retrieval["limitation_or_error"])
    if not excel_documentation.get("success"):
        errors.append(excel_documentation["error"])
    if not documentation.get("success"):
        errors.append(documentation["error"])
    return {
        "conversation_id": conversation_id,
        "customer_question": customer_question,
        "intent": intent,
        "intent_confidence": intent_result["confidence"],
        "sentiment": sentiment_result["sentiment"],
        "frustration_level": sentiment_result["frustration_level"],
        "urgency": sentiment_result["urgency"],
        "retrieved_knowledge_ids": retrieved_ids,
        "answerable": answerability_state != "not_answerable",
        "answerability_state": answerability_state,
        "response": response,
        "escalation_required": escalation_required,
        "escalation_reason": escalation_reason,
        "guardrail_result": guardrail_result,
        "generation_mode": "deterministic_retrieved_knowledge" if response_status == "supported" else "unavailable",
        "documentation_result": documentation,
        "excel_documentation_result": excel_documentation,
        "errors_or_limitations": errors,
    }


def classify_intent(question: str) -> dict[str, Any]:
    normalized = (question or "").lower()
    priority = ("prompt_injection", "account_change", "address_change", "payment", "refund", "cancellation", "return", "exchange", "order_status")
    for intent in priority:
        phrases = dict(INTENT_RULES).get(intent, ())
        if any(phrase in normalized for phrase in phrases):
            matches = [intent] + [name for name, values in INTENT_RULES if name != intent and any(phrase in normalized for phrase in values)]
            return {"intent": intent, "secondary_intents": matches[1:], "confidence": 0.95}
    matches = [intent for intent, phrases in INTENT_RULES if any(phrase in normalized for phrase in phrases)]
    primary = matches[0] if matches else "unsupported"
    return {"intent": primary, "secondary_intents": matches[1:], "confidence": 0.95 if matches else 0.2}


def detect_sentiment(question: str) -> dict[str, Any]:
    normalized = (question or "").lower()
    indicators = [term for term in ("angry", "frustrated", "ridiculous", "unacceptable", "again", "still waiting", "repeatedly", "without resolution") if term in normalized]
    high_risk = any(term in normalized for term in HIGH_RISK_TERMS)
    frustration = "high" if len(indicators) >= 2 or high_risk else "medium" if indicators else "low"
    return {
        "sentiment": "frustrated_or_angry" if frustration != "low" else "neutral",
        "frustration_level": frustration,
        "urgency": "critical" if high_risk else "high" if "urgent" in normalized or "asap" in normalized else "normal",
        "indicators": indicators,
    }


def validate_agent_response(
    question: str,
    response: str,
    knowledge_ids: list[str],
    *,
    answerable: bool,
    escalation_required: bool,
) -> dict[str, Any]:
    failures = []
    normalized_question = (question or "").lower()
    normalized_response = (response or "").lower()
    if any(term in normalized_question for term in INJECTION_TERMS):
        failures.append("prompt_injection_blocked")
    if SECRET_PATTERN.search(question or "") or CARD_PATTERN.search(question or ""):
        failures.append("sensitive_data_blocked")
    if not knowledge_ids and answerable:
        failures.append("missing_knowledge_traceability")
    if not answerable and not any(term in normalized_response for term in ("cannot", "do not have", "human support", "unavailable")):
        failures.append("unsupported_claim_blocked")
    if escalation_required and "human support" not in normalized_response and "human" not in normalized_response:
        failures.append("required_escalation_missing")
    return {"valid": not failures, "failures": failures}


def _risk_reasons(question: str, intent: str, sentiment: dict[str, Any]) -> list[str]:
    normalized = (question or "").lower()
    reasons = []
    if intent == "prompt_injection" or any(term in normalized for term in INJECTION_TERMS):
        reasons.append("prompt_injection")
    if SECRET_PATTERN.search(question or "") or CARD_PATTERN.search(question or ""):
        reasons.append("sensitive_data")
    if intent in LIVE_DATA_INTENTS:
        reasons.append("live_data_unavailable")
    if intent in PRIVILEGED_INTENTS:
        reasons.append("privileged_action")
    if intent in {"privacy", "refund", "cancellation"} and any(term in normalized for term in ("change", "execute", "do it", "delete")):
        reasons.append("sensitive_or_privileged")
    if intent in {"delivery_estimate", "refund", "cancellation"}:
        reasons.append("support_review_required")
    if _contains_any(normalized, DAMAGED_ITEM_TERMS):
        reasons.append("exception_requires_review")
    if sentiment["frustration_level"] == "high":
        reasons.append("high_frustration")
    if sentiment["urgency"] == "critical":
        reasons.append("high_risk")
    if intent == "unsupported":
        reasons.append("unsupported")
    return reasons


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    normalized = (value or "").lower()
    return any(term in normalized for term in terms)


def _supporting_record_requires_escalation(question: str, metadata: dict[str, Any]) -> bool:
    """Apply escalation metadata only when the supported policy calls for review."""

    if metadata.get("escalation_required") != "Yes":
        return False

    topic = str(metadata.get("topic", "")).lower()
    answer = str(metadata.get("answer", "")).lower()
    normalized_question = (question or "").lower()
    if topic in {"free shipping threshold", "non-returnable items", "exchange restrictions"}:
        return any(term in normalized_question for term in ("damaged", "incorrect", "wrong item", "exception"))

    return any(term in f"{topic} {answer}" for term in ("human", "support", "review", "escalat", "failed", "delayed", "complaint"))


def _documentation_question(question: str, intent: str) -> str:
    if SECRET_PATTERN.search(question or "") or CARD_PATTERN.search(question or ""):
        return f"{intent} request (sensitive details redacted)"
    return question