# REST API Reference Documentation (`docs/API.md`)

This document provides a comprehensive specification of the HTTP REST API exposed by the **AI Root Cause Analysis & Intelligent Ticket Resolution Copilot**.

All endpoints are versioned under the prefix `/api`. Authentication is performed via standard Bearer tokens (`Authorization: Bearer <jwt_token>`).

---

## 1. Authentication & Users (`/api/auth`)

### `POST /api/auth/login`
Authenticates a user and returns a signed JWT access token.
- **Request Body**:
  ```json
  {
    "username": "support",
    "password": "supportpassword123"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer",
    "role": "support_engineer",
    "username": "support"
  }
  ```

### `GET /api/auth/me`
Returns the profile and role of the currently authenticated user.
- **Headers**: `Authorization: Bearer <token>`
- **Response `200 OK`**:
  ```json
  {
    "id": "user-support",
    "username": "support",
    "email": "support@example.com",
    "role": "support_engineer",
    "isActive": true
  }
  ```

---

## 2. Log Uploads & Parsing (`/api/uploads`)

### `POST /api/uploads`
Accepts multipart file upload (CSV, TXT, LOG, JSON, JSONL) with content sniffing, format detection, and per-line error tracking.
- **Form Data**: `file: <binary_data>`
- **Response `200 OK`**:
  ```json
  {
    "id": "e43b1234-abcd...",
    "fileName": "service_logs.log",
    "fileSize": 18452,
    "contentType": "text/plain",
    "detectedFormat": "plain_text",
    "status": "completed",
    "parsedCount": 142,
    "failedCount": 0,
    "errors": [],
    "uploadedBy": "support",
    "createdAt": "2026-10-13T00:15:00Z",
    "completedAt": "2026-10-13T00:15:01Z"
  }
  ```

### `GET /api/uploads`
Lists historical upload records with pagination.
- **Query Params**: `skip` (default 0), `limit` (default 50)
- **Response `200 OK`**: List of `UploadRecord` objects.

---

## 3. Log Explorer & Live Ingestion (`/api/logs` & `/api/ingest`)

### `GET /api/logs`
Filterable log explorer with full-text search, service filter, severity filter, and date ranges.
- **Query Params**:
  - `service` (string)
  - `severity` (DEBUG, INFO, WARN, ERROR, CRITICAL)
  - `sourceType` (manual_upload, live)
  - `search` (text search in message)
  - `startTime`, `endTime` (ISO timestamps)
  - `skip`, `limit`
- **Response `200 OK`**:
  ```json
  {
    "total": 1250,
    "items": [
      {
        "id": "ev-881",
        "timestamp": "2026-10-13T00:12:00Z",
        "service": "order-service",
        "severity": "ERROR",
        "message": "ConnectionPoolTimeout: Timeout waiting for connection from pool after 30000ms",
        "source": { "type": "live", "sourceId": "live_demo_app" },
        "fingerprint": "a93bf81...",
        "redacted": false
      }
    ]
  }
  ```

### `POST /api/ingest`
Shared live streaming ingestion endpoint used by collectors and log forwarders.
- **Headers**: `X-API-Key: <configured_source_key>`
- **Request Body**:
  ```json
  {
    "sourceId": "live_demo_app",
    "events": [
      {
        "timestamp": "2026-10-13T00:12:00Z",
        "service": "order-service",
        "severity": "ERROR",
        "message": "ConnectionPoolTimeout: Timeout waiting for connection from pool",
        "traceId": "tr-998"
      }
    ]
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "status": "ok",
    "ingestedCount": 1
  }
  ```

---

## 4. Incidents & AI Root Cause Analysis (`/api/incidents`)

### `GET /api/incidents`
Lists correlated incidents with search and multi-faceted filtering.
- **Query Params**: `status`, `severity`, `service`, `source`, `skip`, `limit`
- **Response `200 OK`**: Paginated list of `Incident` objects.

### `GET /api/incidents/{id}`
Retrieves full incident details, including evidence event references, matched detection rules, AI probable causes, diagnostic checks, and recommended runbooks.
- **Response `200 OK`**:
  ```json
  {
    "id": "inc-4421",
    "title": "order-service: Database Connection Pool Exhaustion",
    "severity": "CRITICAL",
    "service": "order-service",
    "status": "awaiting_approval",
    "eventCount": 24,
    "firstSeen": "2026-10-13T00:10:00Z",
    "lastSeen": "2026-10-13T00:14:00Z",
    "matchedRules": ["Order Service DB Connection Timeout"],
    "probableCauses": [
      {
        "rank": 1,
        "description": "Database connection pool exhaustion and transaction lock timeout on replica node",
        "confidence": 0.92,
        "confidenceTier": "high",
        "supportingEvidence": [
          { "excerpt": "ConnectionPoolTimeout: Timeout waiting for connection from pool after 30000ms" }
        ],
        "alternativeExplanations": "Network jitter or momentary disk I/O bottleneck.",
        "assumptions": "Log events reflect the true state of service dependencies.",
        "verified": false
      }
    ],
    "observedFacts": [
      "Connection timeout observed connecting to database replica"
    ],
    "aiInferences": [
      "Burst traffic or unclosed transaction block is causing socket leakage"
    ],
    "diagnosticChecks": [
      { "step": "Check DB replica connection pool utilization metrics", "rationale": "Determine if active connections reached pool capacity" }
    ],
    "recommendedRunbookIds": ["rb-db-recovery"],
    "ticketId": "tkt-901"
  }
  ```

### `POST /api/incidents/{id}/analyze`
Manually triggers or refreshes AI root cause analysis for an incident.
- **Response `200 OK`**: Updated `Incident` with new `probableCauses`.

### `POST /api/incidents/{id}/feedback`
Records engineer feedback on diagnosis and recommendation quality.
- **Request Body**:
  ```json
  {
    "isUseful": true,
    "comments": "Accurate hypothesis and evidence citations."
  }
  ```

---

## 5. Tickets Lifecycle (`/api/tickets`)

### `GET /api/tickets`
Lists incident tickets.
- **Query Params**: `status`, `priority`, `assignee`, `skip`, `limit`

### `POST /api/tickets/{id}/transition`
Enforces valid ticket state machine transitions (`open` -> `in_progress` -> `pending_approval` -> `verifying` -> `resolved` -> `closed`).
- **Request Body**:
  ```json
  {
    "status": "in_progress",
    "comment": "Beginning investigation."
  }
  ```

### `POST /api/tickets/{id}/comments`
Appends comments/notes to a ticket.

---

## 6. Remediation Actions & Approval Policy (`/api/remediation`)

### `GET /api/remediation/actions`
Lists allow-listed actions (`restart_demo_service`, `clear_demo_cache`, `rollback_demo_config`).

### `POST /api/remediation/request`
Requests execution of a protected remediation action for an incident.
- **Request Body**:
  ```json
  {
    "incidentId": "inc-4421",
    "actionName": "restart_demo_service"
  }
  ```
- **Response `200 OK`**: `ActionApprovalRecord` with status `pending`.

### `GET /api/remediation/approvals`
Lists pending or decided approval records for senior approver review.
- **Query Params**: `status` (pending, approved, rejected, executed)

### `POST /api/remediation/approvals/{id}/decision`
Approver or Admin decision. **Enforces dual-role check: the requester cannot approve their own request!**
- **Request Body**:
  ```json
  {
    "decision": "approved",
    "reason": "Confirmed DB pool saturation in log evidence"
  }
  ```

### `POST /api/remediation/execute/{id}`
Executes the approved remediation action via safe internal code paths and initiates recovery verification.
- **Response `200 OK`**:
  ```json
  {
    "status": "executing_recovery_verification",
    "message": "Action 'restart_demo_service' ran successfully. Verifying recovery health checks...",
    "verified": false
  }
  ```

---

## 7. Append-Only Audit Logging (`/api/audit`)

### `GET /api/audit/logs`
Queries immutable audit events.
- **Query Params**: `entityType`, `actor`, `limit`
- **Response `200 OK`**:
  ```json
  {
    "items": [
      {
        "id": "aud-109",
        "action": "APPROVAL_DECISION_APPROVED",
        "actor": "approver",
        "role": "approver",
        "entityType": "actionApproval",
        "entityId": "appr-331",
        "details": { "decision": "approved" },
        "timestamp": "2026-10-13T00:15:30Z"
      }
    ]
  }
  ```

---

## 8. Admin Management (`/api/admin`)

- `GET /api/admin/users`: List users and roles.
- `GET /api/admin/sources`: List live log sources and status.
- `GET /api/admin/rules`: List configured detection rules.
- `POST /api/admin/rules`: Create or update detection rules.
- `GET /api/admin/runbooks`: List approved runbooks.
- `POST /api/admin/runbooks`: Create or update runbooks.
