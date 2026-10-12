import re
from typing import List, Dict, Any, Type
from pydantic import BaseModel
from app.services.llm.base import LLMProvider
from app.models.rca import RCAResult
from app.models.incident import ProbableCause, DiagnosticCheck, EvidenceItem

class MockProvider(LLMProvider):
    async def generate(
        self,
        messages: List[Dict[str, str]],
        response_schema: Type[BaseModel],
        temperature: float = 0.1,
        timeout: float = 30.0
    ) -> BaseModel:
        # Concatenate prompt text
        prompt_text = " ".join([m.get("content", "") for m in messages])
        
        evidence_block = ""
        if "REDACTED LOG EVIDENCE:" in prompt_text:
            after_marker = prompt_text.split("REDACTED LOG EVIDENCE:", 1)[1]
            if "SIMILAR HISTORICAL INCIDENTS:" in after_marker:
                evidence_block = after_marker.split("SIMILAR HISTORICAL INCIDENTS:", 1)[0]
            else:
                evidence_block = after_marker
        else:
            evidence_block = prompt_text

        log_lines = []
        for line in evidence_block.splitlines():
            line_str = line.strip()
            if any(k in line_str for k in ["ERROR", "CRITICAL", "WARN", "Exception", "timeout", "failed", "Traceback", "pool", "OSError", "Deadlock", "SSLError", "429"]):
                log_lines.append(line_str)
        if not log_lines:
            log_lines = [l.strip() for l in evidence_block.splitlines() if len(l.strip()) > 10]
        if not log_lines:
            log_lines = ["No error messages detected in prompt log stream"]

        primary_excerpt = log_lines[0][:150]

        # Deterministic pattern matching on prompt content
        lower_prompt = prompt_text.lower()

        if "database" in lower_prompt or "timeout" in lower_prompt or "pool" in lower_prompt:
            cause_desc = "Database connection pool exhaustion and transaction lock timeout on replica node"
            runbook_ids = ["rb-db-recovery"]
            diag_checks = [
                DiagnosticCheck(step="Check DB replica connection pool utilization metrics", rationale="Determine if active connections reached the max pool capacity of 20"),
                DiagnosticCheck(step="Inspect pg_stat_activity for lingering idle in transaction queries", rationale="Identify long-running transactions holding pool connections")
            ]
            facts = [
                "Connection timeout observed connecting to database replica",
                "Connection pool capacity limit reached for order-service worker threads"
            ]
            inferences = [
                "Burst traffic or an unclosed transaction block is causing socket leakage",
                "Service cannot fulfill checkout mutations until pool connections are recycled"
            ]
            confidence = 0.92
            tier = "high"

        elif "memory" in lower_prompt or "oom" in lower_prompt or "heap" in lower_prompt:
            cause_desc = "Unbounded cache retention causing memory limit saturation and OutOfMemoryError"
            runbook_ids = ["rb-mem-leak"]
            diag_checks = [
                DiagnosticCheck(step="Check JVM/Process resident memory usage and garbage collection frequency", rationale="Verify whether heap allocation has plateaued near 100%"),
                DiagnosticCheck(step="Inspect cache eviction policy for auth tokens", rationale="Determine if expired cache entries are being properly evicted")
            ]
            facts = [
                "Process killed or saturated by out of memory exception",
                "High resident memory usage observed leading up to crash"
            ]
            inferences = [
                "Application cache lacks TTL or LRU eviction, leading to memory exhaustion",
                "Immediate cache purge and container restart will restore memory headroom"
            ]
            confidence = 0.88
            tier = "high"

        elif "config" in lower_prompt or "yaml" in lower_prompt or "missing" in lower_prompt:
            cause_desc = "Invalid configuration syntax or missing mandatory environment variable deployed"
            runbook_ids = ["rb-config-rollback"]
            diag_checks = [
                DiagnosticCheck(step="Review recent CI/CD deployment diffs for configuration maps", rationale="Identify malformed keys or missing environment parameters"),
                DiagnosticCheck(step="Validate application startup environment variable schema", rationale="Ensure all required connection variables are populated")
            ]
            facts = [
                "Application failed configuration parsing during startup/initialization",
                "Config error identified in log stack trace"
            ]
            inferences = [
                "Recent deployment pushed an untested configuration revision",
                "Rolling back to the previous stable configuration revision will resolve startup failures"
            ]
            confidence = 0.95
            tier = "high"

        elif "unauthorized" in lower_prompt or "auth" in lower_prompt or "401" in lower_prompt:
            cause_desc = "Spike in client credential validation failures or token signing key rotation mismatch"
            runbook_ids = []
            diag_checks = [
                DiagnosticCheck(step="Verify JWT signing key synchronization across auth replicas", rationale="Check if expired signing key is rejecting valid client tokens"),
                DiagnosticCheck(step="Check client IP distribution for credential stuffing attack", rationale="Determine if surge is distributed or isolated to specific clients")
            ]
            facts = ["High volume of 401/403 authorization failures within 5 minute window"]
            inferences = ["Possible token verification failure or unauthorized brute force attempt"]
            confidence = 0.75
            tier = "medium"

        elif "503" in lower_prompt or "downstream" in lower_prompt or "gateway" in lower_prompt:
            cause_desc = "Upstream connection failure due to downstream dependency 503 unavailability"
            runbook_ids = []
            diag_checks = [
                DiagnosticCheck(step="Verify health of downstream service endpoints", rationale="Ascertain whether downstream service is degraded or offline")
            ]
            facts = ["Downstream 503 Service Unavailable received at API gateway"]
            inferences = ["Downstream dependency is overloaded or undergoing deployment"]
            confidence = 0.70
            tier = "medium"

        elif "disk" in lower_prompt or "space" in lower_prompt or "errno 28" in lower_prompt:
            cause_desc = "Filesystem disk space exhaustion preventing transactional write operations"
            runbook_ids = ["rb-mem-leak"]
            diag_checks = [
                DiagnosticCheck(step="Run df -h to verify partition utilization across mount points", rationale="Identify which volume is at 100% capacity"),
                DiagnosticCheck(step="Purge stale temporary files and logs in /var/data", rationale="Restore immediate disk space headroom")
            ]
            facts = ["OSError: [Errno 28] No space left on device encountered"]
            inferences = ["Disk volume storage is completely full, halting persistent writes"]
            confidence = 0.90
            tier = "high"

        elif "deadlock" in lower_prompt or "lock" in lower_prompt:
            cause_desc = "Thread lock contention and circular deadlock between concurrent worker threads"
            runbook_ids = ["rb-db-recovery"]
            diag_checks = [
                DiagnosticCheck(step="Generate thread dump to analyze lock acquisition graph", rationale="Find threads blocked on circular mutexes"),
                DiagnosticCheck(step="Review transaction isolation levels and lock ordering", rationale="Prevent future lock inversion")
            ]
            facts = ["Deadlock detected between concurrent worker threads"]
            inferences = ["Circular lock ordering between inventory and reservation operations"]
            confidence = 0.85
            tier = "high"

        elif "ssl" in lower_prompt or "cert" in lower_prompt or "expired" in lower_prompt:
            cause_desc = "Expired SSL/TLS leaf certificate causing upstream handshake rejection"
            runbook_ids = ["rb-config-rollback"]
            diag_checks = [
                DiagnosticCheck(step="Verify certificate validity and expiration date via openssl s_client", rationale="Confirm certificate expiration timestamp"),
                DiagnosticCheck(step="Rotate and deploy renewed TLS certificates", rationale="Restore secure communication")
            ]
            facts = ["SSLError: Certificate has expired encountered during TLS negotiation"]
            inferences = ["Upstream TLS certificate renewal was missed or delayed"]
            confidence = 0.94
            tier = "high"

        elif "rate limit" in lower_prompt or "429" in lower_prompt or "quota" in lower_prompt:
            cause_desc = "Third-party service provider rate limit quota exhaustion returning HTTP 429"
            runbook_ids = []
            diag_checks = [
                DiagnosticCheck(step="Inspect request volume against provider tier limits", rationale="Determine if traffic exceeds contracted TPS"),
                DiagnosticCheck(step="Verify backoff and retry jitter configuration", rationale="Ensure exponential backoff prevents thundering herd")
            ]
            facts = ["HTTP 429 Too Many Requests received from notification provider"]
            inferences = ["Outbound notification volume exceeded provider rate limits"]
            confidence = 0.82
            tier = "high"

        else:
            cause_desc = "Transient application error detected in service log stream"
            runbook_ids = []
            diag_checks = [DiagnosticCheck(step="Review preceding debug logs for unexpected exceptions", rationale="Isolate initial failure trigger")]
            facts = ["Application emitted error-level log events"]
            inferences = ["Possible internal unhandled exception"]
            confidence = 0.50
            tier = "low"

        res = RCAResult(
            probableCauses=[
                ProbableCause(
                    rank=1,
                    description=cause_desc,
                    confidence=confidence,
                    confidenceTier=tier,
                    supportingEvidence=[
                        EvidenceItem(excerpt=primary_excerpt)
                    ],
                    alternativeExplanations="Network jitter or momentary disk I/O bottleneck.",
                    assumptions="Log events reflect the true state of service dependencies.",
                    verified=False
                )
            ],
            observedFacts=facts,
            aiInferences=inferences,
            diagnosticChecks=diag_checks,
            recommendedRunbookIds=runbook_ids,
            overallUncertainty="Low uncertainty based on clear log signatures." if confidence > 0.8 else "Moderate uncertainty; review diagnostic checks.",
            insufficientEvidence=(confidence < 0.6)
        )

        return res
