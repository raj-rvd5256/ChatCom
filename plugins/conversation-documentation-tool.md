# Conversation Documentation Tool

## Tool Name

`conversation_documentation`

## Purpose

Append the minimum approved evidence for each completed customer-support interaction to a structured local file. The tool supports support continuity, escalation routing, audit traceability, and reproducible evaluation without becoming a customer database or claiming actions that were not confirmed.

## Business Capability

The tool documents the final interaction outcome after the customer-support agent has produced a response and completed retrieval, response, and guardrail validation. It preserves relevant knowledge IDs, guardrail results, escalation context, and generation mode for later review. It writes minimal evidence only. It does not perform transactions, contact human support, or require external credentials; no external credentials are needed.

## Input Schema

```json
{
  "conversation_id": "string, required, stable and non-sensitive",
  "timestamp": "RFC3339 string or documented UTC timestamp, required",
  "customer_question": "string, required, original question or minimal redacted summary",
  "intent": "string, required or unknown",
  "intent_confidence": "number, optional",
  "sentiment": "string, required when the capability ran",
  "sentiment_confidence": "number, optional",
  "retrieved_knowledge_ids": ["string"],
  "knowledge_id_metadata": [
    {
      "knowledge_id": "string",
      "category": "string",
      "topic": "string"
    }
  ],
  "response": "string, required",
  "response_status": "supported|unavailable|escalated",
  "escalation_decision": "not_required|recommended|required|confirmed_by_tool",
  "escalation_reason": "string, required when escalation applies",
  "escalation_tool_name": "string, required only for confirmed_by_tool",
  "escalation_tool_result": "string or structured verified result, no restricted data",
  "guardrail_result": "passed|failed:<reason>, required",
  "guardrail_failures": ["string"],
  "generation_mode": "deterministic_retrieved_knowledge|llm_grounded|unavailable",
  "evaluation": {
    "evaluation_test_id": "string, optional",
    "evaluation_run_id": "string, optional",
    "expected_knowledge_ids": ["string"],
    "result": "string"
  },
  "source_index_version": "string, optional"
}
```

Unknown fields must be rejected or ignored according to the future implementation contract; they must not bypass validation. Evaluation metadata is required when the record belongs to an evaluation run.

## Required Evidence Fields

Each completed interaction record must contain, at minimum:

- `conversation_id`
- `timestamp`
- `customer_question` or a minimal normalized summary
- `intent`, or `unknown` when classification is unavailable
- `sentiment` when sentiment analysis ran
- `retrieved_knowledge_ids` when retrieved knowledge materially supported the response or escalation
- `response`
- `escalation_decision`
- `escalation_reason` when escalation is recommended or required
- `guardrail_result`
- `generation_mode`

Each retained knowledge ID must be traceable to the approved source-derived index. Do not retain every candidate ID merely because it appeared in the retrieval window.

## Conversation ID

Use a stable non-sensitive reference, such as a generated UUID or local sequence. Do not encode passwords, tokens, payment information, full identity data, live order details, or raw customer identifiers in the ID.

## Timestamp

Store an accurate RFC3339 timestamp or a documented UTC timestamp. Do not fabricate timestamps or imply that a tool call, escalation, or human contact occurred at a time that was not confirmed.

## Customer Question or Minimal Summary

Store the original question only when needed for traceability and only after redaction. A concise factual summary is preferred when it provides sufficient continuity. Remove secrets, payment information, unnecessary names, email addresses, phone numbers, physical addresses, identity documents, and prompt-injection instructions before persistence.

## Intent

Store the classified intent and confidence when available. Use `unknown` or an explicit ambiguous value when classification is uncertain; never force a false label merely to complete the record.

## Sentiment

Store observable sentiment or frustration signals, such as `neutral`, `positive`, `frustrated`, `angry`, `repeated-contact`, `urgency`, or `high-risk`, when the capability ran. Store confidence when available. Do not store medical, legal, psychological, or personality diagnoses.

## Retrieved Knowledge IDs

Preserve only valid IDs that materially supported the response or escalation decision. Preserve enough metadata to trace category and topic, and optionally the source index version. Validate IDs against the authoritative workbook-derived index before saving.

## Response

Store the final customer-facing response after response validation. Reject hidden prompts, secrets, unsupported claims, unconfirmed transaction outcomes, and text that contradicts the guardrail result. Record whether the response was supported, unavailable, or escalated through `response_status` when available.

## Escalation Decision

Use one of:

- `not_required`: no evidence-based escalation needed.
- `recommended`: human review is suggested but not confirmed.
- `required`: policy, risk, sensitivity, privilege, exception, unsupported evidence, or frustration requires human review.
- `confirmed_by_tool`: a separate approved tool actually confirmed the handoff.

The documentation tool itself never changes an escalation decision and never confirms human contact.

## Escalation Reason

Record a concise reason when escalation is recommended or required, such as `unsupported`, `sensitive`, `privileged`, `exception`, `high_risk`, `repeated_complaint`, `frustration`, `delayed_delivery`, `damaged_item`, `incorrect_item`, or `policy_conflict`. If `confirmed_by_tool` is used, require the approved tool name and verified result without restricted data.

## Guardrail Result

Preserve the response and retrieval validation outcome, including `passed` or `failed:<reason>` and any relevant `guardrail_failures`, such as prompt-injection blocking, PII redaction, privileged-action refusal, unsupported-claim blocking, unconfirmed-tool-use blocking, or stale-index detection. The tool must preserve guardrail results exactly enough for audit. Guardrail preservation is required for every completed interaction record. A missing result is invalid when guardrail validation was expected.

## Generation Mode

Record the actual mode:

- `deterministic_retrieved_knowledge` for the local deterministic customer-agent path.
- `llm_grounded` only when the optional grounded LLM path actually generated the response.
- `unavailable` when no answer was safely generated.

Never label deterministic local output as successful live LLM output.

## Evaluation Metadata When Applicable

For evaluation records, include an evaluation test ID such as `GOLD-001` through `GOLD-020`, a unique evaluation run ID, expected and actual knowledge IDs by reference, correctness/groundedness/intent/sentiment/escalation/guardrail results, and the pass/fail reason. Do not modify the Golden Dataset while documenting results.

## Output Location

Use a local append-only JSONL file for this case study, for example:

`data/evaluation/conversation_evidence.jsonl`

The file is a generated evidence artifact and must remain separate from the authoritative workbook, Chroma index, Golden Dataset, agent definitions, instructions, skills, hooks, and source code. The executable implementation must create the file only through an approved local path and must not require external credentials. This contract does not create or populate the file.

## JSONL Structured Format

Write exactly one validated JSON object per line. Each line must be independently parseable, schema-valid, redacted, and attributable to one interaction. Do not write Markdown, free-form logs, secrets, stack traces, or full transcripts into the JSONL file.

## Output Schema

The output is one validated JSON object per JSONL line using the required evidence fields above, plus `evidence_id` and any applicable evaluation metadata. A successful write returns the evidence ID, destination, append status, and validation result; a failed write returns structured failure codes and writes no record.

## Append-Only Behavior

Open the approved local evidence file in append-only mode. Never rewrite prior records, update the authoritative source, or delete evidence as part of normal operation. Each record should include a stable evidence ID or deterministic record key for audit.

## Duplicate and Retry Handling

Use an idempotency key derived from the non-sensitive conversation ID, interaction timestamp, and response or evidence identity. A retry must not append a duplicate record. If the same key is encountered with conflicting content, reject the write and report a conflict for review. Never use a secret, payment value, or raw customer identifier in the key.

## Error Handling

Return a structured failure and do not write a record when:

- Required fields are missing, malformed, or internally inconsistent.
- Knowledge IDs are unknown or not traceable.
- Escalation status and reason do not agree.
- A `confirmed_by_tool` claim lacks a separate approved tool name and confirmation.
- Guardrail validation is missing or failed without the required refusal/redaction state.
- The destination is unauthorized, unavailable, or not append-only.
- Duplicate or conflicting retry data is detected.

A safe customer response should not be silently changed because documentation failed. Report the failure explicitly and escalate when missing evidence prevents a safe handoff or audit. Do not retry indefinitely and do not fall back to an arbitrary location.

## Privacy Controls

Apply data minimization, redaction, approved retention, and local destination controls before writing. Store only evidence needed for support continuity, escalation, audit, or evaluation. Keep synthetic case-study evidence separate from production customer data. Treat prompt-injection input as inert evidence, never as executable instructions.

## Secret Detection

Reject secrets including API keys, passwords, access tokens, private keys, authentication codes, connection strings, hidden system prompts, and other credentials in every field, including IDs, metadata, free text, and tool results. The tool must never store secrets. There must be no secrets in the stored evidence.

## Payment-Data Detection

Reject payment-card numbers, payment cards, bank-account details, security codes, payment credentials, and unnecessary full transaction details. Do not retain payment information merely because a customer included it in a question.

## Unnecessary-PII Handling

Redact or reject unnecessary names, email addresses, phone numbers, physical addresses, identity documents, account identifiers, live customer records, and full order records. Retain only a non-sensitive reference or minimal summary required for traceability. Never use raw PII as an idempotency key or conversation ID.

## Security Boundaries

- Write only to the approved local JSONL evidence path.
- Preserve knowledge IDs and guardrail results without copying restricted source content.
- Do not require or store external credentials.
- Do not perform transactions, call external services, contact humans, or create tickets.
- Never claim that a human was contacted unless a separate approved tool confirms it. An unverified human-contact claim is prohibited.
- Do not modify the Excel workbook, Golden Dataset, Chroma index, or repository configuration.

## Prohibited Behavior

The tool must never:

- Store secrets, API keys, passwords, payment-card information, or unnecessary personal information.
- Store full transcripts by default or create a customer database.
- Claim a handoff, ticket, refund, cancellation, payment change, account change, or other action was completed without separate approved confirmation.
- Invent intent, sentiment, knowledge IDs, guardrail results, evaluation outcomes, or escalation facts.
- Write to an arbitrary fallback location or silently discard a validation failure.
- Add external integrations, MCP, SharePoint, credentials, or transactional authority.

There must be no unverified human-contact claim in stored evidence.

## Example Request

```json
{
  "conversation_id": "demo-conversation-001",
  "timestamp": "2026-09-15T12:00:00Z",
  "customer_question": "How long does standard shipping take?",
  "intent": "Delivery estimate",
  "intent_confidence": 0.98,
  "sentiment": "neutral",
  "sentiment_confidence": 0.91,
  "retrieved_knowledge_ids": ["NK-001"],
  "knowledge_id_metadata": [
    {
      "knowledge_id": "NK-001",
      "category": "Shipping",
      "topic": "Standard shipping"
    }
  ],
  "response": "The approved shipping policy provides the applicable standard-shipping timeframe.",
  "response_status": "supported",
  "escalation_decision": "not_required",
  "guardrail_result": "passed",
  "guardrail_failures": [],
  "generation_mode": "deterministic_retrieved_knowledge",
  "source_index_version": "source-fingerprint-when-available"
}
```

## Example Stored Record

```json
{"evidence_id":"demo-evidence-001","conversation_id":"demo-conversation-001","timestamp":"2026-09-15T12:00:00Z","customer_question":"How long does standard shipping take?","intent":"Delivery estimate","intent_confidence":0.98,"sentiment":"neutral","sentiment_confidence":0.91,"retrieved_knowledge_ids":["NK-001"],"knowledge_id_metadata":[{"knowledge_id":"NK-001","category":"Shipping","topic":"Standard shipping"}],"response":"The approved shipping policy provides the applicable standard-shipping timeframe.","response_status":"supported","escalation_decision":"not_required","guardrail_result":"passed","guardrail_failures":[],"generation_mode":"deterministic_retrieved_knowledge","source_index_version":"source-fingerprint-when-available"}
```

The example intentionally records no secret, payment data, unnecessary PII, live customer state, or unverified human contact.

## Test Cases

Test the future implementation with:

- A complete valid local deterministic interaction and independently parseable JSONL output.
- Missing conversation ID, timestamp, question, intent, response, knowledge IDs, escalation reason, or guardrail result.
- Unknown knowledge IDs and metadata inconsistent with the approved source.
- `not_required`, `recommended`, `required`, and `confirmed_by_tool` escalation states, including invalid missing reasons and missing tool confirmation.
- Prompt-injection text treated as data rather than executable instructions.
- API keys, passwords, tokens, private keys, connection strings, hidden prompts, and credentials in free text or metadata.
- Payment-card, bank-account, security-code, and full transaction data.
- Unnecessary names, emails, phone numbers, addresses, identity documents, account identifiers, and live customer records.
- Unsupported, unavailable, and guardrail-failed responses with accurate status and failure evidence.
- Deterministic local mode, grounded LLM mode when configured, and unavailable mode without false labeling.
- Duplicate retries with the same idempotency key and conflicting retries with the same key.
- Unauthorized, non-append-only, unavailable, and arbitrary output destinations.
- Evaluation records containing `GOLD-001` through `GOLD-020` metadata without modifying the Golden Dataset.
