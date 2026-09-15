# Validate Conversation Evidence Hook

## Purpose

Validate conversation documentation before it is saved. This hook ensures that evidence is complete enough for traceability and escalation while excluding secrets, payment data, unnecessary personal information, live customer records, and unverified claims.

## Trigger Point

Run before a conversation evidence record, escalation record, evaluation record, or documentation event is persisted to an approved output location. Run after redaction and normalization, and again before any external approved documentation integration receives the record.

## Inputs

- Proposed structured evidence record
- Conversation context or minimal question summary
- Agent response
- Intent and confidence
- Sentiment, frustration, urgency, and risk results
- Retrieved knowledge IDs and source metadata
- Escalation decision, reason, and priority
- Guardrail validation result
- Generation mode
- Evaluation metadata, when applicable
- Approved tool results, if any
- Destination identifier

## Required Evidence Fields

The record must contain, when applicable:

- `conversation_id`
- `timestamp`
- `customer_question` or minimal normalized summary
- `intent`
- `sentiment`
- `retrieved_knowledge_ids`
- `response`
- `escalation_decision`
- `escalation_reason` when escalation is required
- `guardrail_result`
- `generation_mode`

Evaluation records must additionally contain the evaluation run ID and test ID. Tool-related evidence must identify the approved tool and confirmed result without copying restricted data.

## Conversation ID

Require a stable non-sensitive ID. Reject IDs containing passwords, tokens, payment data, full identity data, or live order details. Do not use a secret or raw customer identifier as the conversation ID.

## Timestamp

Require a valid timestamp with a documented timezone or UTC convention. Reject missing, malformed, fabricated, or contradictory timestamps.

## Question or Minimal Summary

Require the customer question or a concise factual summary. Redact unnecessary PII, secrets, payment information, and prompt-injection instructions before saving. Do not store a full transcript unless an approved retention requirement explicitly requires it.

## Intent

Require the predicted intent, confidence when available, and an unknown or ambiguous value when classification is uncertain. Do not force a false intent to complete the record.

## Sentiment

Require the observable sentiment/frustration result when the capability ran. Store signals and confidence, not medical, legal, psychological, or personality diagnoses.

## Retrieved Knowledge IDs

Require valid source knowledge IDs when the response uses retrieved knowledge. Verify IDs against the approved source-derived index and retain only IDs that materially support the response or escalation.

## Response

Require the final customer-facing response and generation mode. Reject missing responses, unsupported claims, hidden prompts, secrets, unconfirmed transactions, and text that contradicts guardrail validation.

## Escalation Decision and Reason

Require a clear decision such as `not_required`, `recommended`, `required`, or `confirmed_by_tool`. If escalation is required, require a reason and priority. If status is `confirmed_by_tool`, require the approved tool name and confirmation evidence. Never store an unverified claim that a human was contacted.

## Guardrails Result

Require the response validation status, relevant failures or redactions, and the hook/version result. Missing guardrail results are invalid when the agent was expected to validate the response.

## Generation Mode

Record whether the answer came from deterministic local mode or a configured LLM mode. Do not label local output as a successful live LLM result.

## Evaluation Metadata When Applicable

For evaluation evidence, require:

- Evaluation run ID
- Golden Dataset test ID
- Expected and retrieved knowledge IDs, by reference
- Correctness, groundedness, intent, sentiment, escalation, and guardrail results
- Pass/fail status and failure reason

Do not modify the Golden Dataset while documenting results.

## Privacy Checks

Apply data minimization, redaction, approved retention, and destination controls. Reject unnecessary names, email addresses, phone numbers, physical addresses, identity documents, account identifiers, or full records. Keep synthetic demonstration evidence separate from production customer data.

## Secret Detection

Reject API keys, passwords, tokens, private keys, authentication codes, connection strings, system prompts, and other credentials in every field, including free text, metadata, IDs, and tool results.

## Payment-Data Detection

Reject card numbers, bank-account details, security codes, payment credentials, and full transaction details. Do not retain payment information merely because a customer mentioned it.

## Excessive Personal Data Detection

Reject unnecessary PII and live customer records. Retain only the minimum reference or redacted summary needed for traceability, support continuity, escalation, or evaluation.

## Output Schema Validation

Before saving, verify required fields, types, allowed enum values, timestamp format, valid knowledge IDs, escalation consistency, guardrail status, generation mode, and destination authorization. Return a structured validation result rather than silently dropping invalid fields.

## Failure Behavior

If validation fails:

- Do not save the evidence record.
- Return `evidence_valid: false` with failure codes and affected fields.
- Redact and retry only through an explicit safe-redaction path.
- Escalate if missing evidence prevents a safe handoff or audit.
- Never write to an arbitrary fallback location.

## Approved Output Locations

Save only to explicitly approved structured evaluation or evidence locations, such as `data/evaluation/` for evaluation artifacts or a future authenticated documentation integration. Do not write evidence into the authoritative Excel workbook, Chroma index, agent definitions, instruction files, skill files, or arbitrary temporary files.

Approved destinations must be explicitly authorized before evidence is saved. Unverified human contact claims are rejected.

## Audit Information

Record evidence ID, timestamp, hook version, destination, validation checks, redactions, failure codes, source/index version, and confirmation status. Audit metadata must itself pass secret, payment-data, PII, and unsupported-claim checks.

## Test Cases

Test:

- Complete valid evidence record
- Missing conversation ID or timestamp
- Missing question, response, intent, sentiment, source ID, or guardrail result
- Invalid or unknown knowledge IDs
- Invalid escalation decision, missing reason, or invalid priority
- Unverified human-contact claim
- API key, password, token, or credential in free text or metadata
- Payment-card, bank-account, or transaction data
- Excessive names, addresses, contact details, or live customer records
- Invalid generation mode or false LLM-success label
- Evaluation record missing test/run metadata
- Unauthorized output destination
- Redaction and retry behavior
- Prompt-injection text stored as data rather than executable instruction
