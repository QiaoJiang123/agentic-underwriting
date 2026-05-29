# Agentic Underwriting Platform Requirements And Readiness

## Product Definition

This project is a local-first commercial cyber underwriting operating system. It combines:

- a conversational underwriting assistant;
- permission-aware agent skills;
- submission intake and document management;
- broker, claim, SOP, task, note, guide, and workflow data;
- embedded analytics and model interpretation;
- local audit logs and agent traces.

The intended user is an underwriter who wants to ask natural-language questions and have the system retrieve only the authorized data needed to answer. The underwriter remains the decision owner. AI and models provide decision support, citations, workflow navigation, and drafting help.

## Comprehensive Requirements

### 1. Authorized Data Access

The platform must know who the user is, which role they have, which submissions they can access, and which skills or APIs they can use.

Current local implementation:

- `data/security/auth_policy.json` stores demo users, roles, permissions, and submission scopes.
- `data/security/auth.db` stores local login users and session rows. The seeded demo admin login is username `admin`, password `AU-Admin-2026!`.
- `/login.html` provides the local login page and sets an HTTP-only session cookie through `/api/auth/login`.
- FastAPI middleware authorizes `/api/*` calls before route logic runs.
- Submission-scoped endpoints are checked against the user's allowed submission list.
- The chat endpoint also checks the submission id in the request body.
- Access events are written to `data/audit/access_audit.jsonl`.
- `/api/auth/context` shows the current demo user, policy summary, and recent audit rows for users with `audit:read`.

Production extension:

- Replace the local policy file with enterprise identity provider claims.
- Replace JSONL audit with an immutable audit store.
- Add row-level authorization in the production database.

### 2. Agent Skills

The agent should not directly answer every prompt from memory. It should plan, retrieve, cite, and answer.

Required agent flow:

1. Prompt intake.
2. Multi-step planner.
3. Permission filter.
4. Tool execution loop.
5. Confidence check.
6. Retry expansion when coverage is weak.
7. Context assembly with citations.
8. GPT response.
9. Trace persistence.

Current implementation:

- `backend/services/agent_orchestration_service.py` runs planner, tool loop, confidence checks, retry expansion, and trace persistence.
- `backend/services/data_retrieval_service.py` selects and executes retrieval skills.
- `backend/services/agent_tool_registry.py` defines the formal tool contracts used by the central agent: input schema, output schema, required permission, scope, read/write type, citation policy, and MCP exposure metadata.
- `data/agent_skills/underwriting_assistant.json` documents skill intent and permission groups.
- Skill plans now include required permissions and denied-skill records.

### 3. Underwriting System

The platform should support the underwriter's actual work, not only Q&A.

Required underwriting surfaces:

- submission intake;
- document evidence review;
- missing document analysis;
- broker profile;
- claim history;
- control baseline;
- underwriting appetite;
- clearance;
- rating and quote;
- referral;
- quote approval;
- bind readiness;
- tasks and calendar;
- notes and guides;
- stage lock and audit trail.

Current implementation:

- The expanded Details panel functions as the underwriting workbench.
- Decision workflow gates cover quote readiness, referral, quote approval, and bind readiness.
- Decision packages assemble account, broker, evidence, claims, rating, workflow, model governance, controls, and citations for quote/referral/bind/review.
- Tasks, notes, guides, submission updates, and stage locks are persisted locally.
- SOP metadata supports procedural recommendations.

### 4. Embedded Analytics

Analytics should be visible inside the underwriting flow and callable by the agent.

Current implementation:

- Quote probability and bind probability models.
- Supplemental GLMs for cyber attack, ransomware, data breach, business interruption, and claim severity.
- What If controls.
- Waterfall-style model explanations.
- Portfolio dashboard.
- Model governance registry for approval status, intended use, limitations, monitoring metrics, required controls, and override policy.
- Two-table SQLite analytics mart:
  - `underwriting_submission_analytics`
  - `claim_analytics`
  - joined by `company_id`
  - claim primary key `CLM_CLMT_ID`

Required next maturity:

- model approval status;
- feature lineage;
- model monitoring;
- override reason capture;
- periodic validation reports.

### 5. Data Platform

The demo uses JSON for most operational records and SQLite for the analytics mart.

Current local stores:

- `data/submissions`
- `data/claims`
- `data/brokers`
- `data/task`
- `data/states`
- `data/note`
- `data/guide`
- `data/decision_workflow`
- `data/security`
- `data/audit`
- `data/analytics`
- `model`
- `model/governance.json`

Production-ready local path without cloud:

- keep FastAPI;
- use SQLite with migrations as the local durable DB;
- move JSON records into normalized tables;
- keep files on local disk under controlled paths;
- add backup and restore commands;
- keep access and agent traces as append-only local records.

### 6. Governance

The system must make clear that underwriting decisions remain human-owned.

Controls already present or added:

- source citations from retrieval context;
- agent traces;
- access audit;
- workflow gates;
- quote/referral/bind/review decision package assembly;
- stage submit lock;
- model explanations;
- model governance registry;
- local authorization;
- human confirmation for intake finalization and stage submission.

Additional recommended controls:

- required reason for quote approval overrides;
- required reason for model override;
- manager approval route for referral decisions;
- immutable decision history;
- automated evidence completeness checks at bind.

## Revised Readiness Scores

These scores are for a local production-shaped demo, not a hosted enterprise deployment.

| Area | Previous | Current | Why |
| --- | ---: | ---: | --- |
| Demo readiness | 8.0 | 9.0 | End-to-end search, chat, intake, workbench, analytics, Dev console, and business page are present. |
| Product architecture direction | 7.0 | 8.5 | FastAPI, service layer, agent orchestration, local data stores, analytics mart, and auth/audit scaffolding are now explicit. |
| Agentic workflow foundation | 7.0 | 8.5 | Planner, tool loop, confidence, retry, trace persistence, skill permissions, and retrieval tests are in place. |
| Underwriting workflow depth | 7.0 | 8.5 | Intake, evidence, broker, claims, SOP, decision gates, tasks, notes, guides, and rating/quote are connected. |
| Analytics embedding | 7.0 | 8.5 | Stored model artifacts, waterfalls, What If, supplemental models, portfolio metrics, and SQL mart are available. |
| Local production readiness | 3.0 | 8.0 | Cloud is not required; local policy, middleware, audit, tests, schema validation, and SQLite analytics provide a credible local deployment shape. |
| Authorization/compliance readiness | 2.0 | 8.0 | Local users, roles, permissions, submission scopes, access audit, and agent skill filtering now exist. |

## What Still Separates This From Enterprise Production

- No enterprise login or SSO.
- No encrypted database or secrets vault.
- No immutable external audit store.
- No production OCR pipeline.
- No real carrier policy admin, claims, broker management, or rating system integrations.
- No formal model validation package.
- Most workflow data still lives in JSON rather than normalized operational tables.

These are integration and governance tasks, not blockers for a strong local demo.

## Suggested Next Milestones

1. Move notes, guides, tasks, stages, decisions, broker links, claims, and submissions into SQLite tables.
2. Add database migrations and a local backup/restore command.
3. Add model override workflow with required reason and manager approval.
4. Add downloadable decision package export formats such as PDF, Markdown, and JSON.
5. Add role switcher UI for demoing authorization.
6. Split large frontend files into smaller modules by workbench surface.
7. Add end-to-end browser tests for the main underwriting workflows.
