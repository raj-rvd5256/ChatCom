import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rag.conversation_documentation import record_conversation_evidence
from rag.knowledge_retrieval_tool import retrieve_knowledge


class FakeRetriever:
    def __init__(self, documents):
        self.documents = documents

    def invoke(self, question):
        return self.documents


def document(content="Approved answer"):
    return SimpleNamespace(
        page_content=content,
        metadata={
            "knowledge_id": "NK-001",
            "category": "Shipping",
            "topic": "Standard shipping",
            "source_reference": "Knowledge_Base!A2:K2",
            "escalation_required": "No",
        },
    )


class KnowledgeRetrievalToolTests(unittest.TestCase):
    def test_success_preserves_knowledge_id_and_metadata(self):
        result = retrieve_knowledge("How long does shipping take?", retriever=FakeRetriever([document()]))
        self.assertTrue(result["answerable"])
        self.assertEqual(result["retrieval_status"], "success")
        self.assertEqual(result["knowledge_ids"], ["NK-001"])
        self.assertEqual(result["source_metadata"][0]["category"], "Shipping")

    def test_empty_retrieval_is_explicitly_unsupported(self):
        result = retrieve_knowledge("Unknown question", retriever=FakeRetriever([]))
        self.assertFalse(result["answerable"])
        self.assertEqual(result["retrieval_status"], "empty")
        self.assertEqual(result["limitation_or_error"]["code"], "empty_retrieval")

    def test_invalid_metadata_is_rejected(self):
        invalid = document()
        invalid.metadata.pop("knowledge_id")
        result = retrieve_knowledge("Shipping question", retriever=FakeRetriever([invalid]))
        self.assertEqual(result["retrieval_status"], "invalid")
        self.assertEqual(result["limitation_or_error"]["code"], "invalid_metadata")

    def test_index_unavailable_is_explicit(self):
        with patch("rag.knowledge_retrieval_tool.get_retriever", side_effect=RuntimeError("stale index")):
            result = retrieve_knowledge("Shipping question")
        self.assertEqual(result["retrieval_status"], "error")
        self.assertEqual(result["limitation_or_error"]["code"], "index_unavailable")


class ConversationDocumentationToolTests(unittest.TestCase):
    def evidence(self, destination):
        return record_conversation_evidence(
            conversation_id="conversation-001",
            timestamp="2026-09-15T12:00:00Z",
            customer_question="How long does shipping take?",
            intent="Delivery estimate",
            sentiment="neutral",
            retrieved_knowledge_ids=["NK-001"],
            response="The approved policy provides the shipping timeframe.",
            escalation_decision="not_required",
            guardrail_result="passed",
            generation_mode="deterministic_retrieved_knowledge",
            destination=destination,
        )

    def test_successful_record_and_deterministic_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            result = self.evidence(path)
            self.assertTrue(result["success"])
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["retrieved_knowledge_ids"], ["NK-001"])
            self.assertEqual(record["generation_mode"], "deterministic_retrieved_knowledge")

    def test_missing_required_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            result = record_conversation_evidence(
                conversation_id="conversation-002",
                timestamp="2026-09-15T12:00:00Z",
                customer_question="Question",
                intent=None,
                sentiment="neutral",
                retrieved_knowledge_ids=[],
                response="Response",
                escalation_decision="not_required",
                guardrail_result="passed",
                generation_mode="deterministic_retrieved_knowledge",
                destination=Path(directory) / "evidence.jsonl",
            )
            self.assertFalse(result["success"])

    def test_secret_and_payment_data_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evidence.jsonl"
            secret_result = self.evidence_with_response(destination, "Use api_key=secret-value")
            payment_result = self.evidence_with_response(destination, "Card 4111 1111 1111 1111")
            self.assertIn("secret_detected", secret_result["error"]["failures"])
            self.assertIn("payment_data_detected", payment_result["error"]["failures"])

    def test_append_and_duplicate_retry_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            first = self.evidence(path)
            retry = self.evidence(path)
            self.assertFalse(first["duplicate"])
            self.assertTrue(retry["duplicate"])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 1)

    def evidence_with_response(self, destination, response):
        return record_conversation_evidence(
            conversation_id="conversation-sensitive",
            timestamp="2026-09-15T12:00:00Z",
            customer_question="Question",
            intent="unknown",
            sentiment="neutral",
            retrieved_knowledge_ids=[],
            response=response,
            escalation_decision="not_required",
            guardrail_result="passed",
            generation_mode="deterministic_retrieved_knowledge",
            destination=destination,
        )


if __name__ == "__main__":
    unittest.main()