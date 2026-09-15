"""LangChain retrieval setup for the e-commerce knowledge base."""

from .knowledge_base import build_vector_store, get_retriever
from .customer_agent import answer_customer_question

__all__ = ["answer_customer_question", "build_vector_store", "get_retriever"]