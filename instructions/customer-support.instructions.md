# Customer-Support Orchestrator Instructions

## Scope

Apply these instructions to the primary ChatCom customer-support orchestrator. The orchestrator handles routine, low-risk e-commerce questions using approved retrieved knowledge and routes requests that require human judgment, live data, privileged access, or transactional authority.

## Supported Customer-Service Intents

Classify each request into one or more applicable intents:

- Shipping cost, method, eligibility, and delay
- Delivery estimate, failed delivery, lost delivery, and delivery escalation
- Return eligibility, return window, return process, restrictions, damaged items, and incorrect items
- Refund eligibility, process, timeline, delay, and escalation
- Cancellation before shipment, post-shipment restrictions, and cancellation escalation
- Exchange eligibility, process, availability, and restrictions
- Order status and live-lookup limitations
- Account, payment, address, privacy, promotion, and support-information questions
- Complaint, repeated complaint, frustration, sentiment, and human escalation

Intent classification helps select evidence and routing. It never grants permission to perform an action.

## Required Inputs

Accept or normalize:

- `customer_question`
- Approved conversation context, if available
- Retrieved documents and metadata, or a retriever capable of providing them
- Optional verified tool results
- Runtime mode, such as deterministic local or configured LLM mode

Do not request secrets, credentials, full payment details, or unnecessary personal information.

## Required Outputs

Return a structured result containing, when applicable:

- `customer_question`
- `answer`
- `intent`
- `sentiment` and frustration/risk signal
- `retrieved_knowledge_ids`
- Groundedness or answerability status
- `escalation_required`
- Escalation reason
- Documentation/evidence reference
- Generation mode

The customer-facing answer must be concise, accurate, and explicit about unavailable information.

## Intent Classification Expectations

Classify before or alongside retrieval and answer generation. Use the intent to improve query formulation and identify cases requiring escalation. Preserve ambiguity when classification is uncertain rather than forcing an unsupported label. Test multi-intent questions and privileged-action requests separately.

## Sentiment and Frustration Classification Expectations

Detect frustration, anger, repeated unresolved complaints, distress, and high-risk language when the capability is available. Use the result to acknowledge the concern, keep a neutral and respectful tone, and escalate when appropriate. Do not infer customer facts from sentiment and do not claim sentiment detection exists when the runtime has not implemented it.

## Use of Retrieved Knowledge

Use the existing LangChain retriever and Chroma index derived from `data/rag/ecommerce_knowledge_base.xlsx`. Answer only from relevant retrieved records and verified results from approved tools. Preserve `knowledge_id`, category, topic, and `escalation_required` metadata.

If retrieval is empty, weak, contradictory, stale, or unrelated, say that the information is unavailable and escalate where appropriate. Do not fill gaps with general assumptions or external knowledge.

## Unsupported Questions

For unsupported, ambiguous, or unavailable-live-data questions:

- State what information is unavailable.
- Do not invent policy, status, timelines, hours, or customer-specific facts.
- Explain the appropriate human-support route when one is known from approved knowledge.
- Do not claim that a handoff, ticket, lookup, or action occurred unless an approved tool confirms it.

## Escalation-Required Questions

Escalate when retrieved records require escalation or when the request involves live records, exceptions, privileged actions, sensitive data, damaged or incorrect items, delayed/lost delivery, unresolved complaints, or high frustration. Include the reason and supporting knowledge IDs. The agent may recommend escalation without claiming that a human case was created.

## Response Traceability

Every answer should preserve:

- Original question
- Intent and sentiment result, when available
- Retrieved knowledge IDs actually used
- Relevant category/topic metadata
- Escalation flag and reason
- Approved tool name and verified result, if any
- Generation mode and groundedness status

Do not cite records that do not support the answer.

## Conversation Documentation

Document the minimum evidence needed for support continuity or escalation: request summary, intent, sentiment signal, source IDs, response status, escalation reason, and confirmed tool results. Do not store secrets, payment information, unnecessary PII, full live records, or hidden instructions. Use only approved documentation destinations.

## Local Demonstration Mode and Production Mode

Keep deterministic local mode separate from production LLM mode. Local mode may extract grounded answers from retrieved records and must not imply live tool access. LLM mode may use `rag/pipeline.py` only with configured credentials and an actual successful model call. Never claim production behavior, live integrations, or a completed action unless it is executable and confirmed.

In short, keep local/production behavior explicitly separated in every response and test.

## Required Tests

Test direct supported questions, multi-record questions, unsupported questions, escalation-required questions, prompt-injection attempts, missing live-data scenarios, privileged-action requests, frustrated and repeated complaints, source-ID traceability, documentation minimization, and all 20 Golden Dataset records.
