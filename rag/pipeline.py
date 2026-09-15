"""End-to-end grounded question answering over the e-commerce knowledge base."""

from __future__ import annotations

import os
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .knowledge_base import get_retriever


SYSTEM_PROMPT = """You are a customer-service assistant for the fictional e-commerce business.
Answer the customer's question using only the retrieved knowledge below.

Rules:
- Do not invent business policies, timelines, fees, or order-specific information.
- If the retrieved knowledge is insufficient, say that the information is unavailable.
- Respect escalation_required in the retrieved knowledge and tell the customer when human support is required.
- Never claim to have looked up or changed a live order, account, payment detail, address, or refund.
- Keep the answer concise and cite the applicable knowledge_id values in parentheses.

Retrieved knowledge:
{context}
"""


def _context(documents: list[Document]) -> str:
    return "\n\n".join(
        f"[{document.metadata.get('knowledge_id')}] "
        f"Category: {document.metadata.get('category')} | "
        f"Topic: {document.metadata.get('topic')} | "
        f"Escalation required: {document.metadata.get('escalation_required')}\n"
        f"{document.page_content}"
        for document in documents
    )


def _default_model() -> ChatOpenAI:
    if os.getenv("LLM_PROVIDER", "openai").lower() != "openai":
        raise RuntimeError("Only the configured OpenAI LangChain provider is supported.")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured; live grounded answer generation is unavailable."
        )
    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


def answer_question(
    question: str,
    retriever: Any | None = None,
    model: Any | None = None,
    k: int = 4,
) -> dict[str, Any]:
    """Retrieve knowledge and generate one grounded answer using the configured chat model."""
    active_retriever = retriever or get_retriever(k=k)
    documents = active_retriever.invoke(question)
    retrieved_knowledge = [document.metadata for document in documents]
    active_model = model or _default_model()
    response = active_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT.format(context=_context(documents))),
            HumanMessage(content=question),
        ]
    )
    return {
        "customer_question": question,
        "retrieved_knowledge": retrieved_knowledge,
        "final_grounded_answer": response.content,
    }