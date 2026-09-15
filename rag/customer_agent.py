"""Deterministic customer-support answer generation over the existing RAG index."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.documents import Document

from .knowledge_base import get_retriever


_STOP_WORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "if",
    "is", "me", "my", "of", "on", "should", "the", "to", "what", "when", "where",
    "with", "you", "your",
}
_MINIMUM_SUPPORT_SCORE = 2
_TOKEN_NORMALIZATION = {
    "shipping": "ship",
    "shipped": "ship",
    "delivery": "deliver",
    "delivered": "deliver",
    "returns": "return",
    "refunded": "refund",
    "refunds": "refund",
    "internationally": "international",
}


def _tokens(text: str) -> set[str]:
    return {
        _TOKEN_NORMALIZATION.get(token, token)
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in _STOP_WORDS and len(token) > 2
    }


def _answer_text(document: Document) -> str:
    match = re.search(r"^Answer:\s*(.+)$", document.page_content, re.MULTILINE)
    return match.group(1).strip() if match else document.page_content.strip()


def _rank_supported(question: str, documents: list[Document]) -> list[Document]:
    question_tokens = _tokens(question)
    ranked: list[tuple[int, int, Document]] = []
    for position, document in enumerate(documents):
        searchable = " ".join(
            [
                document.page_content,
                str(document.metadata.get("category", "")),
                str(document.metadata.get("topic", "")),
            ]
        )
        score = len(question_tokens & _tokens(searchable))
        ranked.append((score, -position, document))
    return [document for score, _, document in sorted(ranked, reverse=True, key=lambda item: (item[0], item[1])) if score >= _MINIMUM_SUPPORT_SCORE]


def _deterministic_answer(question: str, documents: list[Document]) -> str:
    answers = [_answer_text(document) for document in documents[:2]]
    response = " ".join(dict.fromkeys(answers))
    if any(document.metadata.get("escalation_required") == "Yes" for document in documents):
        response += " Human support is required for any live lookup, exception, or transactional action described here."
    return response


def _retrieval_query(question: str) -> str:
    normalized = question.lower()
    if "international" in normalized and any(term in normalized for term in ("ship", "delivery", "address")):
        return f"{question} shipping eligibility supported domestic addresses international shipping"
    return question


def answer_customer_question(
    question: str,
    retriever: Any | None = None,
    k: int = 40,
) -> dict[str, Any]:
    """Return a grounded customer answer using only retrieved knowledge records."""
    if not question.strip():
        raise ValueError("question must not be empty")

    active_retriever = retriever or get_retriever(k=k)
    retrieved = active_retriever.invoke(_retrieval_query(question))
    supported = _rank_supported(question, retrieved)
    if not supported:
        return {
            "customer_question": question,
            "retrieved_knowledge_ids": [],
            "answer": "This information is unavailable in the current knowledge base. Human support may need to review the request.",
            "supported": False,
            "generation_method": "deterministic_retrieved_knowledge",
        }

    return {
        "customer_question": question,
        "retrieved_knowledge_ids": [document.metadata["knowledge_id"] for document in supported],
        "answer": _deterministic_answer(question, supported),
        "supported": True,
        "generation_method": "deterministic_retrieved_knowledge",
    }