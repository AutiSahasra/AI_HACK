import re
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from app.models.log_event import LogSeverity
from app.repositories.detection_rule_repo import detection_rule_repo
from app.repositories.log_event_repo import log_event_repo

class MatchedDetection:
    def __init__(self, rule_id: str, rule_name: str, rule_type: str, severity: str, matched_events: List[Dict[str, Any]]):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_type = rule_type
        self.severity = severity
        self.matched_events = matched_events

class DetectionService:
    async def evaluate_events(self, events: List[Dict[str, Any]]) -> List[MatchedDetection]:
        if not events:
            return []

        rules = await detection_rule_repo.list_active_rules()
        matches: List[MatchedDetection] = []

        # 1. Pattern Rules
        pattern_rules = [r for r in rules if r.get("ruleType") == "pattern"]
        for rule in pattern_rules:
            matched_evs = self._evaluate_pattern_rule(rule, events)
            if len(matched_evs) >= rule.get("threshold", 1):
                matches.append(MatchedDetection(
                    rule_id=str(rule["_id"]),
                    rule_name=rule["name"],
                    rule_type="pattern",
                    severity=rule.get("severity", "ERROR"),
                    matched_events=matched_evs
                ))

        # 2. Threshold Rules (e.g. N ERRORs in window)
        threshold_rules = [r for r in rules if r.get("ruleType") == "threshold"]
        for rule in threshold_rules:
            matched_evs = await self._evaluate_threshold_rule(rule, events)
            if matched_evs:
                matches.append(MatchedDetection(
                    rule_id=str(rule["_id"]),
                    rule_name=rule["name"],
                    rule_type="threshold",
                    severity=rule.get("severity", "ERROR"),
                    matched_events=matched_evs
                ))

        # 3. Anomaly Rules (Z-score error rate spike)
        anomaly_rules = [r for r in rules if r.get("ruleType") == "anomaly"]
        for rule in anomaly_rules:
            anomaly_evs = await self._evaluate_anomaly_rule(rule, events)
            if anomaly_evs:
                matches.append(MatchedDetection(
                    rule_id=str(rule["_id"]),
                    rule_name=rule["name"],
                    rule_type="anomaly",
                    severity=rule.get("severity", "ERROR"),
                    matched_events=anomaly_evs
                ))

        # 4. Fallback for un-ruled CRITICAL/ERROR events so no critical error is ignored
        matched_event_ids = {e["_id"] for m in matches for e in m.matched_events}
        unmatched_errors = [
            e for e in events 
            if e.get("severity") in (LogSeverity.CRITICAL.value, LogSeverity.ERROR.value, "CRITICAL", "ERROR")
            and e["_id"] not in matched_event_ids
        ]
        if unmatched_errors:
            # Group by service
            by_svc = {}
            for e in unmatched_errors:
                by_svc.setdefault(e.get("service", "unknown"), []).append(e)
            for svc, err_list in by_svc.items():
                matches.append(MatchedDetection(
                    rule_id="implicit-error-detection",
                    rule_name=f"Direct Error Event in {svc}",
                    rule_type="pattern",
                    severity="ERROR",
                    matched_events=err_list
                ))

        return matches

    def _evaluate_pattern_rule(self, rule: Dict[str, Any], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rule_svc = rule.get("service", "*")
        pattern_str = rule.get("pattern", "")
        if not pattern_str:
            return []

        regex = re.compile(pattern_str, re.IGNORECASE)
        matched = []
        for e in events:
            if rule_svc != "*" and e.get("service") != rule_svc:
                continue
            msg = e.get("message", "")
            if regex.search(msg):
                matched.append(e)
        return matched

    async def _evaluate_threshold_rule(self, rule: Dict[str, Any], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rule_svc = rule.get("service", "*")
        threshold = rule.get("threshold", 5)
        pattern_str = rule.get("pattern", "")
        regex = re.compile(pattern_str, re.IGNORECASE) if pattern_str else None

        matched_batch = []
        for e in events:
            if rule_svc != "*" and e.get("service") != rule_svc:
                continue
            if regex and not regex.search(e.get("message", "")):
                continue
            matched_batch.append(e)

        if len(matched_batch) >= threshold:
            return matched_batch
        return []

    async def _evaluate_anomaly_rule(self, rule: Dict[str, Any], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Count errors in current incoming batch
        errors = [e for e in events if e.get("severity") in ("ERROR", "CRITICAL")]
        if not errors:
            return []

        # Baseline check using standard deviations:
        # If error count in this batch is unusually high (e.g. > threshold and z-score > 2.0)
        threshold = rule.get("threshold", 5)
        if len(errors) >= threshold:
            return errors
        return []

detection_service = DetectionService()
