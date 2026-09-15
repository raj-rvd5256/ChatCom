# Retrieval-Augmented Generation Instructions

## Authoritative Excel Source

`data/rag/ecommerce_knowledge_base.xlsx`, worksheet `Knowledge_Base`, is the authoritative business-knowledge source. It contains the approved synthetic policy records. Do not treat generated indexes, answer text, evaluation output, or external information as a replacement for the workbook.

## Derived Chroma Index

Chroma under `data/rag/chroma/` is a derived retrieval index only. It must be rebuildable from the Excel source and must not be edited as if it were business policy. If the workbook changes, rebuild or invalidate the index before relying on it.

## Existing LangChain Implementation

Reuse `rag/knowledge_base.py` for workbook validation, LangChain `Document` creation, embeddings, Chroma persistence, and retriever access. Do not duplicate ingestion or vector-store logic in another module. Use the existing retriever entry point rather than reading Chroma internals directly.

Use `rag/pipeline.py` for the optional grounded LLM flow and `rag/customer_agent.py` for deterministic local customer-answer behavior. Keep retrieval separate from final answer generation.

## Source Knowledge-ID Preservation

Preserve `knowledge_id` and relevant category, topic, source-reference, and `escalation_required` metadata through retrieval and answer generation. Return the IDs that materially support the final answer. Unknown IDs, missing metadata, and source mismatches are validation failures.

## Retrieval Confidence and Answerability

Assess whether retrieved records are relevant and sufficient before answering. Consider intent match, topic match, source metadata, support overlap, and contradictions. A high similarity result is not automatically sufficient evidence. If confidence is low or evidence is absent, mark the request unsupported or unavailable and escalate where appropriate.

The confidence/answerability decision must be recorded with the response.

Do not claim answerability simply because a response can be written. Answerability requires approved retrieved support for the material claims.

## Stale or Missing Index Handling

If the Chroma index is missing, unreadable, empty, stale relative to the workbook, or built with an incompatible schema:

- Do not answer from memory or cached unsupported text.
- Report the retrieval prerequisite failure.
- Rebuild only through the approved existing ingestion path when the operation is explicitly allowed.
- Otherwise escalate or stop safely.

Apply the same rule to any stale/missing index condition.

Record the source/index version or fingerprint for reproducible evaluation when available.

## Runtime Workbook Protection

Never modify `data/rag/ecommerce_knowledge_base.xlsx` during runtime. Never add live customer records, transactional data, secrets, or credentials to the workbook or derived index. Keep generated artifacts separate from authoritative source files.

## No Invention and Grounded Generation Rules

Construct answer context only from retrieved approved records and verified approved tool results. Do not invent knowledge not found in retrieved records. Do not use general model knowledge to fill policy gaps. Do not infer live order status, delivery dates, refund completion, account changes, support hours, or transactional outcomes from general policy text.

Respect `escalation_required` metadata. If records require human review, say so. If records conflict, do not silently choose one; flag the conflict and escalate.

## Direct and Multi-Record Testing Requirements

Test:

- Direct questions answered by one record
- Questions requiring multiple records
- Questions with related but irrelevant retrieval results
- Unsupported questions and missing live-data requests
- Escalation-required questions
- Stale and missing index behavior
- Unknown or missing source IDs
- Prompt injection in the question and retrieved context
- No-invention behavior for order, refund, account, address, and payment requests

Validate against the complete 20-record Golden Dataset and retain source knowledge IDs in results.
