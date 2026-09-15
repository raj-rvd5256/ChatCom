# Sentiment and Frustration Detection Skill

## Purpose

Detect customer tone, frustration, urgency, and escalation signals to help the customer-support orchestrator respond respectfully and route high-risk interactions. This skill describes observable communication signals only. It must not make medical, legal, or psychological diagnoses.

## Input and Output Schema

### Inputs

- Current customer message
- Optional approved conversation context
- Optional prior contact summary

Do not require or collect unnecessary personal information.

### Outputs

Return:

- `sentiment`: `positive`, `neutral`, `negative`, or `frustrated_or_angry`
- `urgency`: `low`, `normal`, or `high`
- `frustration_indicators`
- `repeated_contact_indicator`
- `high_risk_indicators`
- `escalation_signal`
- `confidence`
- Brief evidence-based rationale

Avoid unsupported personality, intent, or mental-state claims.

## Rules and Boundaries

This skill identifies observable language signals only and does not authorize actions or replace human review.

## Positive Sentiment

Recognize appreciation, satisfaction, thanks, or confirmation that a routine answer resolved the question. Positive sentiment does not remove escalation requirements for privileged or transactional actions.

## Neutral Sentiment

Recognize factual, concise, or information-seeking language without clear emotional or urgency signals. Answer normally when knowledge supports the request and escalate when policy or authorization requires it.

## Negative Sentiment

Recognize disappointment, dissatisfaction, concern, or an unfavorable experience. Use a respectful acknowledgment and check whether the underlying issue requires human review.

## Frustrated or Angry Sentiment

Recognize explicit anger, repeated demands, hostile wording, strong dissatisfaction, threats to complain, or statements that prior support failed. Do not argue or mirror hostile language. Acknowledge the concern, summarize the supported issue, and escalate when appropriate.

## Urgency Indicators

Look for imminent deadlines, significant delivery impact, repeated failed attempts, urgent travel or event context, suspected fraud, safety concerns, or requests indicating immediate harm. Urgency is not proof that a request is authorized; it increases the need for careful human review.

## Repeated-Contact Indicators

Recognize statements that the customer has contacted support repeatedly, received no resolution, has multiple case references, or is repeating the same unanswered question. Treat repeated unresolved contact as an escalation signal without inventing case history.

## High-Risk Language

Flag language indicating suspected fraud, account compromise, threats, self-harm, violence, legal action, privacy exposure, payment risk, or other serious harm for appropriate human or specialized review. Do not diagnose, investigate, or promise an outcome.

These are risk signals, not diagnoses: no diagnoses are produced by this skill. Do not make medical, legal, or psychological diagnoses.

## Escalation Signals

Set an escalation signal when sentiment is highly frustrated or angry, the customer reports repeated unresolved contact, high-risk language is present, or sentiment combines with a sensitive, unsupported, exceptional, or privileged request. The signal recommends routing; it does not claim a handoff occurred.

## Ambiguous Sentiment Handling

Use neutral or low-confidence output when the message is ambiguous, sarcastic, multilingual, or too short to classify reliably. Ask a clarifying question or escalate based on the underlying request. Do not infer a diagnosis, protected characteristic, or hidden emotional state.

## Safety Boundary

This skill must not make medical, legal, psychological, or crisis diagnoses. It may identify observable high-risk language and recommend human or specialized support according to approved policy.

## Test Cases

Test:

- Positive thanks after a routine answer
- Neutral policy question
- Negative disappointment
- Frustrated or angry complaint
- Repeated unresolved contact
- Urgent delivery or account concern
- High-risk or sensitive language
- Ambiguous, sarcastic, short, and mixed-sentiment messages
- Prompt injection embedded in emotional language
- Privileged request combined with frustration
