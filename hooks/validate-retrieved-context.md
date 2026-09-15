# Validate Retrieved Context Hook

## Purpose

Validate retrieved knowledge before it is passed to answer generation. This hook confirms that the context comes from the approved source-derived index, contains traceable records, is relevant to the question, and is sufficient for a grounded response. It must prevent retrieved policy content from being mistaken for live transactional data.

## Trigger Point

Run after the LangChain retriever returns documents and before any LLM or deterministic answer generator receives the context. Run again when retrieval is refreshed, merged, filtered, or changed by a multi-record query.

## Inputs

- Customer question
- Classified intent, when available
- Retrieved LangChain `Document` objects
- Document `page_content`
- Document metadata
- Chroma index location and version/fingerprint, when available
- Authoritative source identity and worksheet name
- Retrieval configuration, including query and `k`

## Required Fields and Checks

## Checks

Every retrieved document must contain:

- Nonempty `page_content`
- `knowledge_id`
- `category`
- `topic`
- `source_reference`
- `escalation_required`

`escalation_required` must be `Yes` or `No`. Metadata must be scalar, parseable, and consistent with the approved source schema.

## Required Knowledge IDs

Reject any document without a nonempty `knowledge_id`. Reject unknown, duplicate-in-conflict, malformed, or non-source-traceable IDs. IDs must be verifiable against the `Knowledge_Base` worksheet in `data/rag/ecommerce_knowledge_base.xlsx` or a validated index manifest derived from it.

## Source Validation

Confirm that:

- The source is `data/rag/ecommerce_knowledge_base.xlsx`.
- The worksheet is `Knowledge_Base`.
- The index is a derived Chroma collection built from that workbook.
- The retrieved metadata and content can be linked to an authoritative workbook record.
- No external or unapproved source has entered the context.

The hook must not treat generated answer text, a stale report, or model memory as authoritative source material. It rejects live transactional interpretation: policy content is not live order, delivery, refund, account, payment, or customer data.

## Empty Results Handling

If no documents are returned:

- Mark retrieval as unsupported or unavailable.
- Do not pass an empty context to confident answer generation.
- Allow a safe unavailable response only when the answer path explicitly supports it.
- Escalate when the question is sensitive, privileged, high-risk, customer-specific, or requires live data.
- Record the empty-result condition in audit evidence.

## Relevance and Answerability Checks

Assess whether the retrieved records match the question intent, category, topic, and material terms. Determine whether the records support the claims likely to appear in the answer. Similarity alone is insufficient.

Reject or route for correction when context is unrelated, too weak, contradictory, stale, or insufficient for the requested answer. Mark answerability separately from retrieval success: retrieved content can exist without supporting the question.

## Multi-Record Retrieval Checks

For questions requiring multiple policy facts, verify that each retained record contributes materially to the answer. Check for consistent eligibility, process, policy, and timeline rules. Remove unrelated records and flag contradictory records for review or escalation. Preserve all IDs used in the final answer.

## Stale Index Handling

Treat the index as stale when its source fingerprint, schema, record count, or build metadata does not match the authoritative workbook. If the index is missing, unreadable, empty, incompatible, or stale:

- Reject the context for answer generation.
- Do not modify the workbook.
- Rebuild only through the approved existing ingestion path and only when explicitly authorized.
- Otherwise return a retrieval-prerequisite failure and escalate if the request requires support.

## Detection of Missing or Malformed Metadata

Reject documents with missing IDs, empty content, invalid escalation flags, invalid source references, unexpected categories, malformed metadata, or metadata that conflicts with the linked workbook record. Do not silently repair policy metadata at runtime.

## Failure Behavior

On validation failure, return a structured failure containing:

- `context_valid`: `false`
- Failure code and reason
- Affected document IDs, when known
- Source/index status
- Answerability status
- Recommended action: retry, rebuild, unavailable response, or escalation

Do not pass invalid context to an answer generator. Do not fabricate replacement records.

## Escalation Behavior

Escalate when validation fails for a live-data request, privileged action, sensitive question, high-risk request, policy exception, materially delayed/lost delivery, refund review, or highly frustrated customer. A hook failure is not proof that human support was contacted; record only a recommendation unless an approved tool confirms handoff.

## Audit Information

Record the minimum evidence needed to reproduce the decision:

- Question reference or normalized question
- Retrieval query and configuration
- Source workbook and worksheet
- Index collection and version/fingerprint
- Retrieved and accepted/rejected knowledge IDs
- Validation checks and failure codes
- Relevance/answerability result
- Escalation decision and reason
- Timestamp and hook version

Do not record secrets, payment details, unnecessary PII, live customer records, or hidden instructions.

## Test Cases

Test:

- Valid single-record retrieval
- Valid multi-record retrieval
- Missing knowledge ID
- Unknown knowledge ID
- Missing or malformed metadata
- Empty retrieval
- Unrelated retrieval
- Contradictory records
- Stale, missing, empty, and unreadable index
- Invalid `escalation_required` value
- Retrieved content containing prompt injection
- Attempt to treat policy content as live order, delivery, refund, account, or payment data
- Unsupported, sensitive, privileged, and high-risk questions
