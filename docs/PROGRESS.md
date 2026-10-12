# Project Progress Checklist & Tracking

## Phase 1: Foundations, Upload, Parsing, Storage, Basic Dashboard
- [x] Requirements and dependencies definition (`backend/requirements.txt`, `demo-app/requirements.txt`, `collector/requirements.txt`, `frontend/package.json`)
- [x] Backend core setup: FastAPI app, Config (Pydantic settings), structured JSON logging, JWT auth & RBAC dependencies
- [x] Database layer: MongoDB client & connection lifecycle (async Motor with mockable fallback for testing)
- [x] Seed data scripts: Users (support_engineer, approver, admin), runbooks, remediation actions, historical incidents, detection rules
- [x] Log Parsers: CSV (header detection), JSON/JSONL, plain text / log (ISO, syslog, Python log format, stack trace grouping)
- [x] Schema Normalization (`logEvents` schema) & Redaction service (credentials, tokens, secrets, emails, card numbers)
- [x] Ingestion API: `POST /api/uploads` (multi-format validation, content sniffing, max size check, partial-error reporting)
- [x] Log Explorer & Retrieval API: `GET /api/logs` with multi-filter support (service, severity, source, time range, text search)
- [x] Frontend setup: React + Vite + TypeScript + Tailwind CSS / component library
- [x] Frontend pages: Login, Dashboard shell, Upload page (drag-and-drop, parsing status, error inspection), Log Explorer
- [x] Phase 1 Tests & Smoke check: Parser unit tests, upload integration tests, auth tests, commit Phase 1

## Phase 2: Detection, Grouping, Deduplication, Incidents
- [x] Detection rules engine: Regex/pattern rules, severity threshold rules, rolling window z-score anomaly checks
- [x] Incident Grouping & Deduplication: fingerprint + service + time window correlation; event count incrementing
- [x] Incident lifecycle state machine (`new` -> `analyzing` -> `analyzed` -> `awaiting_approval` -> `remediating` -> `verifying` -> `resolved` | `escalated` | `failed_analysis`)
- [x] Reopen/repeat detection for recently resolved incidents
- [x] Incident API endpoints: `GET /api/incidents`, `GET /api/incidents/{id}`, related events timeline
- [x] Frontend: Incident List page with filters, Incident Detail view with event timeline and matched rules
- [x] Phase 2 Tests & Smoke check: detection rules tests, grouping & dedup tests, commit Phase 2

## Phase 3: Retrieval and AI Root-Cause Analysis
- [ ] Provider-independent LLM service interface: `AnthropicProvider`, `OpenAICompatibleProvider`, `MockProvider`
- [ ] Retrieval service: MongoDB text index search over historical incidents and runbooks
- [ ] RCA async workflow: collect evidence, redact, retrieve top-k similar incidents + runbooks, generate strict JSON schema
- [ ] Evidence Grounding & Anti-Hallucination verification: drop/flag unverified citations, separate observed facts vs AI inferences
- [ ] Recommendations generator: diagnostic checks & runbook steps with relevance rationale
- [ ] Feedback API: `POST /api/incidents/{id}/feedback` (useful / not useful)
- [ ] Frontend: Analysis view in Incident Detail with confidence badges, evidence citations, facts vs inferences, similar cases, runbooks, feedback button
- [ ] Phase 3 Tests & Smoke check: RCA schema validation tests, anti-hallucination tests, retrieval tests, commit Phase 3

## Phase 4: Live Ingestion with Demo App & Collector
- [ ] Demo app: FastAPI service with normal traffic log emission, fault injection endpoints (`/faults/db_connection_timeout`, `/faults/memory_leak`, `/faults/bad_config_deploy`, `/faults/auth_failure_spike`, `/faults/downstream_503`), `/health` endpoint, and remediation endpoints (`/admin/restart`, `/admin/clear-cache`, `/admin/rollback-config`)
- [ ] Collector: lightweight log tailer daemon with offset tracking, batch POSTs to `/api/ingest` with API key header and backoff
- [ ] Log sources API & MongoDB collection: API key authentication and status tracking
- [ ] `/api/ingest` shared pipeline verification (exact same parse -> normalize -> redact -> persist -> detect path)
- [ ] Frontend: Live Sources status panel, auto-refreshing incident updates
- [ ] Phase 4 Tests & Smoke check: live ingest pipeline tests, fault triggering & collector forwarding, commit Phase 4

## Phase 5: Tickets, Approvals, Remediation, Recovery Verification, Audit
- [ ] Ticket lifecycle management: auto-creation per incident, P1-P4 priority, assignment, comments, state transitions
- [ ] Remediation action allow-list (strictly compiled code paths, no shell commands)
- [ ] Approval workflow & backend policy enforcer: dual-role check, self-approval prevention, expiration
- [ ] Recovery verification service: post-action HTTP `/health` poll + log error silence verification; auto-resolve or escalate
- [ ] Auto-escalation engine: low confidence, insufficient evidence, repeated incident, verification failure
- [ ] Append-only audit logging: immutable audit trails for all actions, state transitions, approvals, logins
- [ ] Save resolved incidents to `historicalIncidents`
- [ ] Frontend: Ticket board/list & detail, Approval queue, Action request & execution status modal, Audit log viewer, Admin settings (users, sources, rules, runbooks, allow-list)
- [ ] Phase 5 Tests & Smoke check: RBAC policy bypass denial tests, verification success/failure tests, commit Phase 5

## Phase 6: Evaluation, Hardening, Documentation & E2E Validation
- [ ] `/eval` synthetic dataset generator: 8+ incident scenarios + negative/benign scenarios
- [ ] Evaluation runner script: metrics report (JSON + Markdown) for precision, recall, false-positive rate, RCA top-1/top-3 accuracy, evidence relevance, MTTR
- [ ] Monitoring dashboard metrics & statistics endpoints
- [ ] Data retention policy & cleanup service
- [ ] Security hardening: rate limiting, CORS, input sanitization, security headers, upload size enforcement
- [ ] Docker Compose orchestration: `mongo`, `backend`, `frontend`, `demo-app`, `collector`
- [ ] Makefile and `.env.example`
- [ ] Comprehensive documentation: `README.md`, `docs/API.md`, `docs/EVALUATION.md`, `docs/LIMITATIONS.md`
- [ ] Full test suite execution & E2E smoke test verification
- [ ] Final commit & delivery summary
