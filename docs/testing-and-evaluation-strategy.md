# Testing and Evaluation Strategy

## 1. Purpose and Testing Objectives

This document defines the testing and evaluation approach for the ChatCom e-commerce customer-support AI case study. The objective is to demonstrate that the implemented deterministic local orchestrator behaves correctly within its approved scope and fails safely outside that scope.

Testing covers the following objectives:

- Validate response correctness for supported customer-service questions.
- Validate that answers are grounded in the approved knowledge base.
- Validate intent classification and sentiment handling.
- Validate escalation decisions for live-data, privileged, exceptional, unsupported, sensitive, and frustrated interactions.
- Validate guardrails, refusal behavior, and prompt-injection resistance.
- Validate that each interaction produces complete, valid conversation evidence.
- Validate deterministic behavior and reproducible evaluation results.

The current implementation is a controlled local demonstration. It does not provide live order, account, payment, carrier, refund, or address access, and it must not claim that a protected action was completed.

## 2. Testing Strategy

### Unit Testing

Unit tests verify small functions and explicit contracts in isolation. Examples include intent classification, sentiment and frustration detection, response validation, risk-reason generation, evidence-record validation, duplicate evidence handling, and retrieval input validation.

### Component Testing

Component tests verify the behavior of individual executable capabilities with controlled inputs. The local retrieval tool is tested for successful retrieval, empty retrieval, invalid metadata, and unavailable-index behavior. The conversation documentation tool is tested for valid JSONL output, required fields, duplicate retries, and rejection of secrets or payment data.

### Integration Testing

Integration tests exercise the connections between the authoritative Excel-derived Chroma index, the retrieval wrapper, the deterministic answer generator, the orchestrator, and the evidence recorder. These tests confirm that retrieved knowledge IDs and metadata remain traceable through the final response and documented evidence.

The live conversation-documentation destination in this demonstrator is the local Excel workbook `data/documentation/chatcom_conversations.xlsx`. The orchestrator automatically appends one row per completed conversation to the `Conversations` worksheet, while retaining JSONL evidence as a fallback. The local workbook is suitable for this case study; a Microsoft 365 or SharePoint destination would require authenticated production credentials and an approved integration.

### End-to-End Scenario Testing

End-to-end scenarios execute a customer question through the real orchestrator and verify the complete outcome: intent, sentiment, answerability, retrieved source IDs, response, escalation decision, guardrail result, generation mode, and conversation evidence.

### Golden Dataset Evaluation

The maintained Golden Dataset contains 20 representative records covering routine questions, exceptions, escalation cases, unsupported requests, and safety cases. Every record is executed through the real local orchestrator and evaluated against its expected behavior.

### Regression Testing

The repository test suite and Golden Dataset evaluator are run after behavior changes. Regression testing protects previously passing behavior, especially around escalation selection, response grounding, guardrails, evidence recording, and deterministic local execution.

### Negative and Adversarial Testing

Negative tests verify that the system does not invent live information, claim unauthorized actions, reveal secrets, accept prompt-injection instructions, or provide unsupported policy claims. Adversarial examples include prompt injection, sensitive payment data, unsupported questions, repeated unresolved complaints, and requests requiring privileged access.

## 3. Test Categories

The test suite and Golden Dataset include the following categories:

- **Routine policy questions:** shipping methods, shipping prices, delivery estimates, return eligibility, return windows, and refund timelines.
- **Shipping and delivery questions:** standard and express shipping, international availability, normal delivery estimates, delayed deliveries, and delivery investigations.
- **Returns and refunds:** return procedures, item restrictions, refund timelines, refund delays, and refund execution requests.
- **Damaged or defective items:** damaged, defective, broken, incorrect, or unusable items requiring evidence and human review. The system must not promise approval, a refund, or a replacement.
- **Failed delivery:** carrier outcome review, possible reattempts, and address-change requests. The system must not confirm a reattempt or address change without live transactional tools.
- **Unsupported questions:** questions not answerable from the approved knowledge base, including unavailable support schedules.
- **Live order-status requests:** requests for current order or carrier status. The system must refuse to fabricate a status and route the request to human support.
- **Privileged actions:** account, payment, bank-account, address, cancellation, refund, and other protected changes.
- **Sensitive information:** payment-card numbers, passwords, API keys, tokens, secrets, and unnecessary personal information.
- **Prompt injection:** instructions to ignore prior instructions, reveal system prompts, or follow untrusted instructions embedded in customer input.
- **Frustrated customers:** angry, frustrated, repeatedly contacting support, unresolved complaints, and high-risk language.
- **Missing or insufficient knowledge:** retrieval failures, empty retrieval results, and questions for which the available records do not support a reliable answer.
- **Conversation evidence recording:** validation that the user message, response, intent, sentiment, retrieved source IDs, escalation decision, and generation mode are recorded in valid JSONL evidence.

## 4. Evaluation Methodology

Every Golden Dataset record is executed through the real `orchestrate_customer_support` function. The evaluator uses the existing retrieval implementation and deterministic local response path; it does not substitute a mock customer-facing agent or external judge.

For each record, the evaluator compares expected and actual intent, sentiment fields, answerability, retrieved knowledge IDs, response behavior, escalation decision, guardrail behavior, and conversation evidence. Response checks include expected knowledge-ID overlap and explainable token coverage. Safety checks verify refusal language, missing-live-data handling, prompt-injection resistance, and unsupported-question handling.

The evaluator writes a reproducible Markdown report containing the run identifier, per-record results, dimension totals, failure reasons, and the exact command used. The evaluator does not modify the Golden Dataset to improve a score. The Golden Dataset and authoritative workbook remain protected inputs.

Evaluation is performed in deterministic local mode. No external LLM, live transactional integration, API credential, carrier system, account system, or payment system is required or used.

## 5. Evaluation Dimensions

The evaluator uses the following dimensions:

- **Intent correctness:** The detected primary intent belongs to the expected intent family for the record.
- **Sentiment correctness:** Sentiment and frustration fields are present and high-frustration cases receive appropriate acknowledgement.
- **Answerability correctness:** The system distinguishes directly answerable questions, partially answerable questions requiring human or live-system support, and questions not answerable from available knowledge.
- **Response correctness:** The response overlaps the expected knowledge records and provides sufficient expected content without unsupported claims.
- **Groundedness and evidence:** The response is traceable to retrieved approved knowledge IDs, or safely explains why an unsupported question cannot be answered.
- **Escalation correctness:** Escalation is preserved for explicit risk, exception, live-data, privileged, unsupported, and human-review cases without unrelated metadata contamination.
- **Safety and refusal behavior:** The system refuses to invent live data, refuses unauthorized actions, resists prompt injection, and avoids false completion claims.
- **Conversation documentation completeness:** Evidence records contain the required user message, response, intent, sentiment, retrieved source IDs, escalation decision, guardrail result, and generation mode in valid JSONL.

## 6. Success Metrics

The following metrics define how performance is measured. Only the verified results stated below are achieved results; no additional measured values are claimed.

- **Golden Dataset pass rate:** Passed Golden Dataset records divided by all evaluated records. Current result: 20/20, or 100%.
- **Test pass rate:** Passing repository tests divided by executed repository tests. Current result: 39/39, or 100%.
- **Intent classification accuracy:** Records whose actual intent is in the expected intent family divided by evaluated records. The current evaluator reports intent correctness by dimension; no separate percentage is claimed here beyond the verified overall results.
- **Sentiment classification accuracy:** Records whose sentiment and frustration behavior match the expected scenario divided by evaluated records. No separate measured percentage is claimed here.
- **Answerability classification accuracy:** Records whose actual answerability matches the expected answerability divided by evaluated records. No separate measured percentage is claimed here.
- **Escalation precision:** Correctly escalated records divided by all escalated records, using an independently defined expected escalation decision.
- **Escalation recall:** Correctly escalated records divided by all records that require escalation.
- **Grounded-response rate:** Supported responses with expected knowledge-ID overlap and valid traceability divided by supported-response records.
- **Unsupported-claim rate:** Responses containing an unsupported policy, live-data, or completion claim divided by scenarios where such claims are prohibited.
- **Evidence-record completeness:** Evaluated interactions with successful, valid evidence containing every required field divided by evaluated interactions.
- **Prompt-injection protection rate:** Prompt-injection cases that are blocked or safely escalated divided by prompt-injection cases.
- **Deterministic repeatability:** Repeated runs with the same inputs produce the same classifications, response behavior, escalation decisions, and evaluation outcomes, apart from generated conversation identifiers, timestamps, and evidence hashes that intentionally identify each run.

## 7. Proposed Acceptance Thresholds

The following are proposed release thresholds, not additional achieved measurements:

- 100% pass rate for critical safety and guardrail tests.
- 100% evidence completeness for evaluated conversations.
- 0 unsupported claims in refusal and live-data scenarios.
- At least 95% overall Golden Dataset pass rate for release.
- No regression in previously passing tests.
- 100% protection against the maintained prompt-injection cases.
- No fabricated order, carrier, account, payment, refund, address, or completion information.

The current verified results meet the overall Golden Dataset threshold and repository test threshold. Production release would require additional operational and security evidence beyond this local case study.

## 8. Best Practices Followed

The implementation follows these practices:

- Uses one authoritative business-knowledge source: the approved Excel workbook.
- Uses a derived vector index rather than manually maintained duplicate business data.
- Keeps deterministic local testing available without external credentials.
- Protects the Golden Dataset from evaluator-driven changes.
- Does not fabricate live order, account, carrier, payment, refund, or address data.
- Does not make false action-completion claims.
- Applies explicit escalation rules for risk, exceptions, privileged actions, and human review.
- Treats prompt-injection content as untrusted customer input.
- Uses reproducible commands for tests and evaluation.
- Separates runtime behavior from evaluation logic and reporting.
- Documents clear production limitations.
- Runs regression testing after every behavior change.

## 9. Test Execution Commands

Run the repository tests with the script source directory and test pattern explicitly specified:

```bash
/tmp/chatcom-langchain-venv/bin/python -m unittest discover -s scripts -p 'test_*.py' -q
```

Run the maintained 20-record evaluator:

```bash
/tmp/chatcom-langchain-venv/bin/python scripts/evaluate_golden_dataset.py
```

Default `unittest` discovery from the repository root does not locate the tests under `scripts` in this repository. The `-s scripts -p 'test_*.py'` arguments are therefore required to execute the complete repository test suite.

## 10. Current Results

The current verified results are:

- 39 tests passed.
- 0 test failures.
- 0 test errors.
- 20/20 Golden Dataset records passed.
- Golden Dataset score: 100%.
- Evaluation mode: deterministic local orchestrator with no external credentials or live transactional integrations.

## 11. Limitations and Future Production Testing

The current case study demonstrates controlled local behavior and does not constitute production readiness. A production deployment would still require:

- Authenticated live order and account integrations.
- A secured human-support handoff integration.
- Load, concurrency, latency, and performance testing.
- Security testing, including abuse cases and authorization testing.
- Privacy and PII testing with approved data-handling controls.
- Monitoring, alerting, audit logging, and operational dashboards.
- Human review of sampled conversations and escalations.
- A/B testing or a controlled pilot before broad rollout.
- Ongoing Golden Dataset maintenance as policies, products, and failure modes change.
- Additional validation of transactional tools, authentication, authorization, rollback, and observability before enabling protected actions.
