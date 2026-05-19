# Underwriting System Plan

This platform is becoming an underwriting decision workbench rather than only a chatbot wrapper. The system should keep the chat interface, but the durable underwriting logic should live behind the scenes as services with clear inputs, outputs, and audit-friendly JSON records.

## Core Ingredients

- Submission metadata: applicant, industry, revenue, records, coverage request, status, timeline, risk flags, and open questions.
- Document evidence: cyber application, ransomware supplement, prior policy, loss runs, financials, security questionnaire, MFA/EDR/backups, incident response plan, vendor assessment, and compliance evidence.
- Claim history: linked claim records from a claims system with loss dates, claim type, status, severity, paid/reserved amounts, cause, and recovery status.
- Underwriter context: notes as ground truth, guide instructions as operating policy, tasks, and locked stage state.
- Analytics models: stored quote and bind probability models plus feature metadata.
- Decision workflow: appetite status, authority level, blockers, subjectivities, required evidence, next actions, and referral rationale.

## Feature Plan

1. Add a claims service and dummy claim source.
2. Add an underwriting service that reads submission data, evidence status, claims, notes/tasks later, and analytics model outputs.
3. Surface the underwriting service in Details as an expanded workbench view.
4. Add API endpoints that return stable JSON for claims and underwriting summaries.
5. Later, persist underwriting decisions, referrals, quote recommendations, and audit logs as separate records under `data/underwriting`.

## Current Demo Slice

- `data/claims/<submission_id>.json` stores dummy claim records.
- `/api/submissions/<submission_id>/claims` returns claim history and aggregate claim metrics.
- `/api/submissions/<submission_id>/underwriting` returns appetite, evidence readiness, claim signals, and recommended actions.
- Details includes an expandable Underwriting System card that links submission evidence, claim history, appetite signals, and recommended actions.
- Analytics keeps Quote, Bind, and What If views and uses the same left-edge double-arrow expansion pattern.
