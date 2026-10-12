# Architecture & Implementation Decisions Log (docs/DECISIONS.md)

This log records design decisions, trade-offs, and rationale made during the implementation of the AI Root Cause Analysis & Intelligent Ticket Resolution Copilot.

---

### DEC-001: Async Motor with Mongomock-Motor for Testing
- **Context**: MongoDB is the primary database. In local development or CI where Docker daemon might not be running or Mongo service isn't active yet, unit tests must still run fast, reliably, and without external network dependencies.
- **Decision**: Use `motor` (`AsyncIOMotorClient`) for production and integration runtime. For automated unit/integration tests without a live MongoDB instance, configure a lightweight mock repository layer or `mongomock-motor` fallback, ensuring 100% of the test suite runs and passes out of the box in standard Python environments.
- **Status**: Approved.

---

### DEC-002: Strict Multi-Format Parsing & Multi-Line Log Association
- **Context**: Real-world logs include CSV, structured JSON/JSONL, Syslog, standard Python logging `YYYY-MM-DD HH:MM:SS [LEVEL] [SERVICE] MESSAGE`, and stack traces that span multiple lines.
- **Decision**: The plain-text parser implements stateful multi-line buffering: lines that start without a timestamp or start with whitespace/exception markers (e.g. `Traceback (most recent call last):`, `Caused by:`, `\tat `) are appended to the preceding log record rather than creating broken standalone records.
- **Status**: Approved.

---

### DEC-003: Sensitive Information Redaction Engine
- **Context**: Logs may contain passwords, API tokens, bearer keys, JWTs, emails, IPs, and credit card numbers. These must never leak to external LLM providers or unredacted database storage without explicit flagging.
- **Decision**: Implement a deterministic regex-based redaction engine with patterns for bearer tokens (`Bearer [A-Za-z0-9_\-\.]+`), API keys, passwords in key-value and JSON formats (`(password|secret|token|api_key|access_token)\s*[:=]\s*["']?([^"' \s,]+)`), email addresses, and credit card / PAN sequences. Replace with standard masking tokens like `[REDACTED_SECRET]`, `[REDACTED_EMAIL]`, etc., and set `redacted: true`.
- **Status**: Approved.

---

### DEC-004: Deduplication & Fingerprinting Strategy
- **Context**: High-frequency errors create alert storms if each error creates a new incident.
- **Decision**: Normalize messages by stripping variable numbers, UUIDs, hex IDs, and timestamps, then compute a SHA-256 fingerprint hash. An open incident within a configurable time window (default 15 minutes) matching the same service and fingerprint will be updated (incrementing `eventCount`, updating `lastSeen`, appending event references) rather than creating duplicate incidents.
- **Status**: Approved.

---

### DEC-005: LLM Provider Abstraction & Anti-Hallucination Guard
- **Context**: The system must support Anthropic Claude, OpenAI-compatible APIs (including Ollama/vLLM), and an offline deterministic MockProvider. AI must not hallucinate evidence.
- **Decision**: 
  1. Build a unified `LLMProvider` abstract base class with a common `generate` interface.
  2. Implement `MockProvider` using deterministic rule-based heuristic extraction of error patterns, root causes, and runbook recommendations so that tests and local runs work offline with zero external API dependencies.
  3. Validate all LLM responses against strict Pydantic schemas. Every evidence snippet cited in `supportingEvidence` is verified against actual ingested incident event messages. Any hallucinated citation is pruned, and if evidence is weak, `insufficientEvidence` is flagged.
- **Status**: Approved.

---

### DEC-006: Hardened Remediation Action Allow-List and Backend Policy Enforcement
- **Context**: Automated remediation can be dangerous if arbitrary commands or dynamic code can be passed.
- **Decision**: Zero shell execution. Actions are strictly defined in an immutable allow-list dictionary (`restart_demo_service`, `clear_demo_cache`, `rollback_demo_config`). Each action maps to a hard-coded Python function calling demo-app endpoints. Backend API routes enforce role checks and approval states independently of the UI; direct API requests without valid approved states are rejected with HTTP 403/409.
- **Status**: Approved.

---

### DEC-007: Recovery Verification Before Incident Resolution
- **Context**: Simply executing an action does not guarantee service restoration.
- **Decision**: Execution of a remediation action moves an incident to `verifying` status, not `resolved`. A background verification loop probes the service `/health` endpoint and monitors log silence for error events. Only upon successful health verification does the incident and ticket transition to `resolved`. If verification times out or fails, it transitions to `escalated`.
- **Status**: Approved.
