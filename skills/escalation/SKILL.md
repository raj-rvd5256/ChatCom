# Escalation Skill

## Purpose

Determine when a customer interaction requires human support, produce a clear escalation recommendation, and preserve the minimum evidence needed for safe routing. This skill recommends or records escalation; it must not claim that a human was contacted unless an approved tool confirms it.

## Inputs

Accept the customer question, retrieved metadata, intent, sentiment/risk signals, answerability status, and approved tool results.

## Outputs

Return an escalation decision, reason, priority, truthful handoff message, supporting knowledge IDs, and confirmation status.

## Rules and Boundaries

Escalation is a routing recommendation unless an approved tool confirms a human handoff. The skill cannot perform transactions or invent customer, order, payment, refund, or support records.

## Escalation Conditions

Escalate when the request is unsupported, sensitive, high-risk, exceptional, privileged, transactional, materially delayed, repeatedly unresolved, or highly frustrated. Respect the source record's `escalation_required` metadata and any approved sentiment/risk signal.

## Unsupported Questions

Escalate or safely state unavailable information when no relevant approved knowledge supports the request. Do not answer from memory or external knowledge. Explain the limitation without claiming that a lookup, review, ticket, or handoff occurred.

## Sensitive Requests

Escalate privacy/data requests, suspected account compromise, payment concerns, identity issues, safety concerns, and requests involving unnecessary or protected personal information. Minimize what is collected and route through the approved support path.

## High-Risk Requests

Escalate suspected fraud, security compromise, threats, serious harm, legal or regulatory concerns, or other high-risk language for human or specialized review. Do not diagnose, investigate, promise compensation, or make legal or medical conclusions.

## Highly Frustrated Customers

Escalate angry, highly frustrated, distressed, or repeatedly dissatisfied customers, especially when the underlying issue requires live access, an exception, a remedy, or a case review. Acknowledge the concern and keep the response neutral and respectful.

## Account or Payment Changes

Escalate requests to change email, account, profile, payment, bank, authentication, or delivery-address information. These require human verification and an explicitly authenticated and authorized tool. Never request secrets or claim the change succeeded.

## Requests Requiring Live Order Data

Escalate questions about current order status, carrier events, delivery dates, lost packages, refund status, live eligibility, or other customer-specific records when no approved authenticated lookup tool is available. General policy records do not establish live facts.

## Repeated Unresolved Contact

Escalate when the customer reports repeated contact without resolution, multiple prior cases, or a recurring unresolved complaint. Preserve only minimal case references supplied through an approved channel and do not change priority or promise compensation.

## Required Escalation Output

Return a structured result containing:

- `escalation_required`
- `reason`
- `priority`
- `human_handoff_message`
- Relevant `knowledge_ids`
- Intent and sentiment/risk signals
- Whether a handoff was recommended or confirmed
- Approved tool name and confirmation, if any

## Reason and Priority

Use a concise reason such as `unsupported_request`, `privileged_action`, `live_data_required`, `policy_exception`, `delivery_investigation`, `refund_review`, `sensitive_request`, `high_risk`, `high_frustration`, or `repeated_unresolved_contact`.

Priority must be evidence-based. Use normal priority for routine review, high priority for significant customer impact or urgent operational issues, and urgent only when an approved policy defines that threshold. Never inflate priority merely because a customer uses strong language.

## Human-Handoff Message

Use a truthful message such as:

> This request needs human support because it requires a live review or an action that I cannot perform. Please use the approved support channel with the relevant reference and complete the required verification. I have not changed your account, order, payment information, address, or refund.

Adapt the message only with approved policy facts. Do not say “a human has been contacted,” “a ticket was created,” or “the action is complete” unless an approved tool confirms it.

## Logging Requirements

Record the minimum evidence needed for traceability:

- Question or normalized issue summary
- Intent and sentiment/risk result
- Escalation condition and reason
- Priority and handoff message
- Supporting knowledge IDs
- Approved tool call and confirmation, if present
- Documentation/evidence reference

Do not log secrets, payment details, unnecessary PII, live customer records, or unsupported claims.

No unconfirmed human contact may be reported as completed.

## Test Cases

Test:

- Unsupported and empty-evidence questions
- Sensitive privacy or account requests
- High-risk language and suspected fraud
- Highly frustrated customers
- Account, payment, bank, and address changes
- Live order and carrier-data requests
- Repeated unresolved complaints
- Damaged, incorrect, delayed, lost, or exceptional cases
- Routine questions that should not be escalated unnecessarily
- Prompt injection asking the skill to suppress escalation
- Handoff recommendation versus confirmed tool handoff
- Priority selection and escalation evidence logging
