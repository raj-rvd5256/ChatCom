"""Local, source-traceable knowledge retrieval tool."""

from pathlib import Path
from typing import Any, Iterable, Optional

from rag.knowledge_base import (
    DEFAULT_INDEX,
    DEFAULT_WORKBOOK,
    get_retriever,
)

REQUIRED_METADATA = (
    "knowledge_id",
    "category",
    "topic",
    "source_reference",
    "escalation_required",
)
APPROVED_WORKSHEET = "Knowledge_Base"
VALID_ESCALATION_VALUES = {"Yes", "No"}


def retrieve_knowledge(
    customer_question: str,
    retrieval_config: Optional[dict[str, Any]] = None,
    retriever: Any = None,
) -> dict[str, Any]:
    """Retrieve validated knowledge without modifying the source workbook."""

    config = retrieval_config or {}
    if not isinstance(customer_question, str) or not customer_question.strip():
        return _failure(
            customer_question,
            "invalid_query",
            "customer_question must be a non-empty string",
        )

    index_path = Path(config.get("persist_directory", DEFAULT_INDEX))
    workbook_path = Path(config.get("workbook_path", DEFAULT_WORKBOOK))
    if workbook_path != Path(DEFAULT_WORKBOOK) or config.get("workbook_path"):
        return _failure(
            customer_question,
            "unauthorized_source",
            "retrieval is restricted to the approved Excel workbook",
        )
    if not workbook_path.is_file():
        return _failure(customer_question, "source_unavailable", "approved workbook is unavailable")
    if not index_path.is_dir():
        return _failure(customer_question, "index_missing", "derived Chroma index is unavailable")

    try:
        active_retriever = retriever or get_retriever(
            persist_directory=index_path,
            k=_bounded_k(config.get("k", 4)),
        )
        documents = active_retriever.invoke(customer_question)
    except Exception as exc:
        return _failure(customer_question, "index_unavailable", str(exc))

    if not documents:
        return _failure(
            customer_question,
            "empty_retrieval",
            "no approved knowledge supports this question",
            retrieval_status="empty",
            answerable=False,
        )

    invalid_metadata = []
    retrieved_content = []
    knowledge_ids = []
    source_metadata = []
    for document in documents:
        metadata = getattr(document, "metadata", {}) or {}
        missing = [field for field in REQUIRED_METADATA if not _nonempty_string(metadata.get(field))]
        if metadata.get("escalation_required") not in VALID_ESCALATION_VALUES:
            missing.append("escalation_required")
        if missing:
            invalid_metadata.append({"missing": sorted(set(missing)), "metadata": metadata})
            continue
        knowledge_id = metadata["knowledge_id"]
        knowledge_ids.append(knowledge_id)
        source_metadata.append({field: metadata[field] for field in REQUIRED_METADATA})
        retrieved_content.append(getattr(document, "page_content", ""))

    if invalid_metadata:
        return _failure(
            customer_question,
            "invalid_metadata",
            "retrieved documents contain missing or invalid source metadata",
            retrieval_status="invalid",
            details={"invalid_documents": invalid_metadata},
        )

    unique_ids = list(dict.fromkeys(knowledge_ids))
    return {
        "original_query": customer_question,
        "retrieved_content": retrieved_content,
        "knowledge_ids": unique_ids,
        "source_metadata": source_metadata,
        "answerable": bool(unique_ids),
        "retrieval_status": "success",
        "limitation_or_error": None,
        "source": {
            "workbook": str(workbook_path),
            "worksheet": APPROVED_WORKSHEET,
            "index": str(index_path),
        },
    }


def _bounded_k(value: Any) -> int:
    try:
        k = int(value)
    except (TypeError, ValueError):
        return 4
    return min(max(k, 1), 40)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _failure(
    query: str,
    code: str,
    message: str,
    retrieval_status: str = "error",
    answerable: bool = False,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "original_query": query,
        "retrieved_content": [],
        "knowledge_ids": [],
        "source_metadata": [],
        "answerable": answerable,
        "retrieval_status": retrieval_status,
        "limitation_or_error": {"code": code, "message": message, "details": details or {}},
        "source": {
            "workbook": str(DEFAULT_WORKBOOK),
            "worksheet": APPROVED_WORKSHEET,
            "index": str(DEFAULT_INDEX),
        },
    }