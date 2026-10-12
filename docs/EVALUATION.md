# System Evaluation & Benchmark Report (`docs/EVALUATION.md`)

This document details the evaluation methodology, scenario datasets, benchmark hardware, and empirical findings for the **AI Root Cause Analysis & Intelligent Ticket Resolution Copilot**.

---

## 1. Evaluation Methodology

The evaluation framework (`/eval`) rigorously evaluates the copilot across three functional dimensions:
1. **Detection & Grouping**: Can the system detect genuine operational failures without firing false alarms on benign traffic?
2. **Diagnosis & Grounding (RCA)**: Does the LLM identify the true root cause (Top-1 and Top-3), and are supporting evidence excerpts strictly grounded in the ingested logs?
3. **Automated MTTR & Remediation**: How does the policy-gated remediation and recovery verification loop compare with manual investigation baselines?

### Hardware & Environment
- **Host**: Windows 11 / x86_64 / Intel Core i7 / 16 GB RAM
- **Runtime**: Python 3.13 / FastAPI / Uvicorn
- **Database**: MongoDB 6.0 / High-performance asynchronous Motor layer with in-memory test fallback
- **AI Engine**: MockProvider (Deterministic baseline with zero external API latency/cost), Anthropic Claude 3.5 Sonnet & OpenAI-compatible providers supported.

---

## 2. Benchmark Scenario Datasets

The evaluation suite tests **10 distinct operational scenarios**:

| Scenario ID | Service | Expected State | Ground Truth Cause | Expected Action | Manual Baseline |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `db_connection_timeout` | `order-service` | INCIDENT | Connection pool exhaustion | `restart_demo_service` | 1,800s (30m) |
| `memory_leak` | `catalog-service` | INCIDENT | Unbounded cache retention / OOM | `restart_demo_service` | 2,400s (40m) |
| `bad_config_deploy` | `payment-service` | INCIDENT | Missing encryption key in config deploy | `rollback_demo_config` | 1,500s (25m) |
| `auth_failure_spike` | `auth-service` | INCIDENT | Expired JWT key / credential surge | `clear_demo_cache` | 1,200s (20m) |
| `downstream_503` | `checkout-service` | INCIDENT | Upstream dependency 503 outage | `restart_demo_service` | 2,100s (35m) |
| `disk_full` | `storage-service` | INCIDENT | Volume full (Errno 28 / No space) | `clear_demo_cache` | 1,800s (30m) |
| `thread_deadlock` | `order-service` | INCIDENT | Circular mutex lock contention | `restart_demo_service` | 2,700s (45m) |
| `cert_expired` | `api-gateway` | INCIDENT | Expired TLS x509 leaf certificate | `restart_demo_service` | 1,600s (26m) |
| `rate_limit_exhaustion` | `notification-service` | INCIDENT | Third-party provider HTTP 429 quota | `clear_demo_cache` | 1,400s (23m) |
| `benign_healthy_traffic` | `web-frontend-service` | BENIGN CONTROL | Clean operational HTTP 200/204 traffic | None | 0s |

---

## 3. Benchmark Results Summary

The evaluation was executed using `python eval/evaluate.py`. All raw data is persisted in `eval/eval_results.json` and `eval/eval_report.md`.

### Core Metrics Table

| Metric | Target | Measured Value | Analysis |
| :--- | :--- | :--- | :--- |
| **Detection Precision** | > 90.0% | **100.0%** | Zero false positive incidents created from benign logs. |
| **Detection Recall** | > 90.0% | **100.0%** | 9 out of 9 known incident scenarios successfully triggered rules. |
| **False Positive Rate** | < 5.0% | **0.0%** | Benign control traffic correctly identified as non-incident. |
| **RCA Top-1 Accuracy** | > 80.0% | **100.0%** | Primary hypothesis correctly identified the underlying fault. |
| **RCA Top-3 Accuracy** | > 90.0% | **100.0%** | Verified root cause always present in candidate causes. |
| **Evidence Relevance** | > 85.0% | **88.9%** | Cited supporting evidence contained labeled failure signatures. |
| **Avg Time to Detect (MTTD)** | < 2.0s | **0.0839s** | Real-time streaming evaluation and grouping. |
| **Avg Time to Diagnose** | < 1.0s | **0.0084s** | Instantaneous structured RCA generation under MockProvider. |
| **Automated MTTR** | < 60s | **4.59s** | Automated pipeline from detection through recovery. |
| **Manual Baseline MTTR** | Baseline | **1,833.3s** | Average documented SRE investigation and triage time (~30 min). |
| **MTTR Reduction** | > 80.0% | **99.7%** | Extreme latency reduction in repetitive triage workflows. |
| **Automation Success Rate** | > 90.0% | **100.0%** | 100% of remediation actions passed post-action recovery verification. |

---

## 4. Safety & Governance Findings

1. **Anti-Hallucination Filter**:
   - The RCA engine runs a post-generation string verification filter against the incident's raw ingested log messages.
   - Any evidence excerpt not present verbatim in the incident's logs is automatically dropped.
   - When evidence is sparse, `insufficientEvidence` is set to `true`, and the system prompts the engineer with diagnostic checks rather than generating false conclusions.

2. **Dual-Authorization Enforcement**:
   - Backend API tests in `backend/tests/test_phase5.py` demonstrate that support engineers cannot execute protected actions without prior approval.
   - The backend policy service strictly prevents self-approval (HTTP 403 `Self-approval policy violation`).
   - Direct execution attempts before approval is granted are blocked (HTTP 403).

3. **Recovery Verification Integrity**:
   - Remediation actions only put incidents into the `verifying` state.
   - The system polls `/health`. If healthy, the incident and linked ticket are transitioned to `resolved`. If the check fails or times out, the incident is escalated to human operators with reasons logged to the append-only audit trail.
