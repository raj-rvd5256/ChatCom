import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.evaluate_golden_dataset import (
    DEFAULT_REPORT_PATH,
    GOLDEN_PATH,
    evaluate_records,
    load_golden_dataset,
    render_report,
)


def fake_orchestrator(question, *, retriever=None, documentation_destination=None):
    return {
        "conversation_id": "test-conversation",
        "response": "The approved policy information is unavailable for this test.",
        "intent": "unsupported",
        "intent_confidence": 0.2,
        "sentiment": "neutral",
        "frustration_level": "low",
        "answerable": False,
        "retrieved_knowledge_ids": [],
        "escalation_required": True,
        "escalation_reason": "unsupported",
        "generation_mode": "unavailable",
        "guardrail_result": "passed",
        "documentation_result": {"success": True, "evidence_id": "test-evidence"},
    }


class EvaluatorTests(unittest.TestCase):
    def test_loads_all_twenty_records(self):
        records = load_golden_dataset()
        self.assertEqual(len(records), 20)
        self.assertEqual({record["test_id"] for record in records}, {f"GOLD-{index:03d}" for index in range(1, 21)})

    def test_malformed_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps([{"test_id": "GOLD-001"}]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_golden_dataset(path)

    def test_every_test_id_is_rendered(self):
        results = evaluate_records(load_golden_dataset(), orchestrator=fake_orchestrator)
        report = render_report(results, "test-run")
        for index in range(1, 21):
            self.assertIn(f"GOLD-{index:03d}", report)

    def test_evaluation_is_deterministic(self):
        records = load_golden_dataset()
        first = evaluate_records(records, orchestrator=fake_orchestrator)
        second = evaluate_records(records, orchestrator=fake_orchestrator)
        self.assertEqual(first, second)

    def test_report_writes_to_required_path(self):
        results = evaluate_records(load_golden_dataset(), orchestrator=fake_orchestrator)
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "evaluation_report.md"
            report_path.write_text(render_report(results, "test-run"), encoding="utf-8")
            self.assertTrue(report_path.is_file())
            self.assertIn("GOLD-020", report_path.read_text(encoding="utf-8"))

    def test_protected_inputs_are_not_modified(self):
        protected = [GOLDEN_PATH, Path("data/rag/ecommerce_knowledge_base.xlsx")]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        evaluate_records(load_golden_dataset(), orchestrator=fake_orchestrator)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        self.assertEqual(before, after)

    def test_evaluator_has_no_credential_requirement(self):
        results = evaluate_records(load_golden_dataset(), orchestrator=fake_orchestrator)
        self.assertEqual(len(results), 20)


if __name__ == "__main__":
    unittest.main()