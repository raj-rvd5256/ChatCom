# Intent Classification Skill

## Purpose

Classify a customer message into one or more supported customer-service intents so retrieval, response generation, documentation, and escalation can be routed consistently. Classification identifies the request type; it does not authorize any action or provide live data.

## Input and Output Schema

### Inputs

- `customer_question`
- Optional approved conversation context
- Optional prior intent result

Do not use unverified customer records or secrets as classification input.

### Outputs

Return:

- `intent`
- `secondary_intents`, if applicable
- `confidence`
- `evidence_terms` or concise rationale
- `answerability_hint`
- `escalation_hint`
- `requires_live_data`
- `requires_privileged_action`

Keep classification separate from final answer generation.

## Rules and Boundaries

Classification routes product information and customer-service questions; it does not create policy, infer live records, or authorize transactions.

## Supported Intents

### Shipping

Questions about shipping methods, shipping cost, free-shipping thresholds, shipping eligibility, or shipping delays.

### Delivery

Questions about normal delivery estimates, failed delivery, lost delivery, carrier events, delayed delivery, and delivery escalation.

### Returns

Questions about return eligibility, return windows, return process, non-returnable items, damaged items, incorrect items, and return exceptions.

### Refunds

Questions about refund eligibility, refund process, refund timelines, delayed refunds, and refund execution requests.

### Cancellation

Questions about cancellation before shipment, after-shipment cancellation restrictions, and cancellation requests requiring live order access.

### Exchange

Questions about exchange eligibility, exchange process, availability, restrictions, and damaged or incorrect-item exchange exceptions.

### Order Status

Questions asking where an order is, whether it shipped, carrier status, delivery progress, or information required for a live order lookup.

### Account Changes

Requests to change email, account, profile, payment information, delivery address, or other protected customer information.

### General FAQ

Routine questions about product information, support routes, published promotions, general customer-service information, or privacy/data-request processes.

### Complaint or Escalation

Frustration, anger, repeated unresolved contact, high-risk interaction, policy exception, sensitive request, or explicit request for human support.

### Unknown or Unsupported Intent

Requests that do not map to an approved business intent, require unavailable live data, or lack sufficient context for safe classification.

## Multi-Intent Handling

Identify a primary intent and preserve secondary intents. Retrieve evidence for each material intent. Do not collapse a privileged action into a routine FAQ. If intents conflict or require different escalation paths, mark the ambiguity and escalate rather than choosing silently.

## Confidence Handling

Use high confidence only when the message clearly matches an approved intent. Use medium or low confidence when terms are ambiguous, multiple intents compete, or the request depends on missing context. Low-confidence classification must not produce a confident policy answer; it should trigger clarification, unavailable handling, or escalation.

## Live-Information Boundary

Never infer live order information, delivery status, refund completion, account state, payment state, or customer eligibility from general policy records. Mark `requires_live_data` when the customer asks about a specific current record and route to approved support or an authenticated tool.

## Test Cases

Test:

- One clear example for each supported intent
- Shipping versus delivery ambiguity
- Return versus refund ambiguity
- Cancellation before and after shipment
- Account, payment, and address changes
- Order-status questions requiring live data
- General FAQ and support-route questions
- Complaint, escalation, frustration, and repeated contact
- Unknown and unsupported questions
- Multi-intent questions
- Low-confidence or incomplete questions
- Prompt-injection text that attempts to alter classification
