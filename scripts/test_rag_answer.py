"""Run representative retrieval and grounded-answer checks against the RAG pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.knowledge_base import get_retriever  # noqa: E402
from rag.pipeline import answer_question  # noqa: E402


QUESTIONS = [
    "What does standard shipping cost?",
    "How long does standard delivery normally take?",
    "What should I do if my delivery is delayed?",
    "Can I return an item?",
    "How long does a refund normally take?",
    "I want to change my bank account details.",
]


def _unsupported_request_is_safe(answer: str) -> bool:
    text = answer.lower()
    safety_terms = ("unavailable", "cannot", "can't", "human support", "escalat", "not able")
    return any(term in text for term in safety_terms)


def main() -> int:
    retriever = get_retriever(k=3)
    model_error = None
    model = None
    try:
        from rag.pipeline import _default_model

        model = _default_model()
    except RuntimeError as error:
        model_error = str(error)

    for question in QUESTIONS:
        documents = retriever.invoke(question)
        print(f"\nQUESTION: {question}")
        for document in documents:
            print(
                "RETRIEVED: "
                f"{document.metadata.get('knowledge_id')} | "
                f"{document.metadata.get('category')} | "
                f"{document.metadata.get('topic')} | "
                f"escalation_required={document.metadata.get('escalation_required')}"
            )

        if model is None:
            print(f"ANSWER: NOT GENERATED ({model_error})")
            continue

        result = answer_question(question, retriever=retriever, model=model)
        answer = str(result["final_grounded_answer"])
        print(f"ANSWER: {answer}")
        if question == QUESTIONS[-1]:
            print(f"NO-MATCH SAFETY CHECK: {'PASS' if _unsupported_request_is_safe(answer) else 'FAIL'}")
        else:
            print(f"GROUNDED CONTEXT PRESENT: {'PASS' if documents else 'FAIL'}")

    if model_error:
        print(f"\nLLM CALL: NOT ATTEMPTED - {model_error}")
    else:
        print("\nLLM CALL: attempted for all questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())