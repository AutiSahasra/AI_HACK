import re
import io
import csv
import json
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional

from app.models.upload import LineError
from app.models.log_event import LogSeverity, ParseStatus
from app.services.normalization import normalization_service
from app.services.redaction import redaction_service
from app.services.fingerprint import fingerprint_service

class ParsingService:
    # Pattern for standard application log:
    # 2026-10-13 14:02:11,123 [ERROR] [order-service] Something failed
    # or 2026-10-13T14:02:11.123Z ERROR order-service: Something failed
    ISO_APP_REGEX = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
        r'(?:\[?(?P<severity>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL|TRACE)\]?\s+)?'
        r'(?:\[?(?P<service>[a-zA-Z0-9_\-\.]+)\]?\s*[:-]?\s*)?'
        r'(?P<message>.*)$',
        re.IGNORECASE
    )

    # Pattern for Syslog style:
    # Oct 13 14:02:11 host-01 auth-service[1234]: Invalid login
    SYSLOG_REGEX = re.compile(
        r'^(?:<\d+>)?(?P<timestamp>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<host>[a-zA-Z0-9_\-\.]+)\s+'
        r'(?P<service>[a-zA-Z0-9_\-\.]+)(?:\[\d+\])?:\s*'
        r'(?P<message>.*)$'
    )

    # Multi-line stack trace start indicator
    STACKTRACE_INDICATORS = (
        "traceback (most recent call last):",
        "caused by:",
        "exception in thread",
        "java.lang.",
        "at ",
        "\tat ",
    )

    @classmethod
    def sniff_format(cls, filename: str, content: str) -> str:
        lower_name = filename.lower()
        if lower_name.endswith('.csv'):
            return 'csv'
        if lower_name.endswith('.jsonl') or lower_name.endswith('.ndjson'):
            return 'jsonl'
        if lower_name.endswith('.json'):
            return 'json'

        # Content sniffing
        stripped = content.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            return 'json'
        
        # Check if first few lines are valid JSON objects
        first_lines = [l.strip() for l in stripped.splitlines() if l.strip()][:5]
        if first_lines and all(l.startswith('{') and l.endswith('}') for l in first_lines):
            try:
                for l in first_lines:
                    json.loads(l)
                return 'jsonl'
            except Exception:
                pass

        if stripped.startswith('{') and stripped.endswith('}'):
            return 'json'

        # Check for CSV header line
        if first_lines and (',' in first_lines[0] or '\t' in first_lines[0]):
            header_candidates = {'timestamp', 'time', 'level', 'severity', 'message', 'msg', 'service'}
            first_cols = {c.strip().lower() for c in re.split(r'[,;\t]', first_lines[0])}
            if len(first_cols.intersection(header_candidates)) >= 2:
                return 'csv'

        return 'text'

    @classmethod
    def parse_content(
        cls,
        content: str,
        detected_format: str,
        default_service: str = "unknown-service"
    ) -> Tuple[List[Dict[str, Any]], List[LineError]]:
        if detected_format == 'csv':
            return cls._parse_csv(content, default_service)
        elif detected_format == 'json':
            return cls._parse_json(content, default_service)
        elif detected_format == 'jsonl':
            return cls._parse_jsonl(content, default_service)
        else:
            return cls._parse_text(content, default_service)

    @classmethod
    def _parse_csv(cls, content: str, default_service: str) -> Tuple[List[Dict[str, Any]], List[LineError]]:
        events = []
        errors = []
        f = io.StringIO(content)
        
        try:
            sample = content[:4096]
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample) if ',' in sample or '\t' in sample or ';' in sample else csv.excel
        except Exception:
            dialect = csv.excel

        reader = csv.reader(f, dialect)
        rows = list(reader)
        if not rows:
            return events, errors

        header = [h.strip().lower() for h in rows[0]]
        
        # Map known columns
        col_map = {}
        for idx, col in enumerate(header):
            if col in ('timestamp', 'time', 'datetime', 'date', 'ts', '@timestamp'):
                col_map['timestamp'] = idx
            elif col in ('severity', 'level', 'loglevel', 'log_level', 'status'):
                col_map['severity'] = idx
            elif col in ('service', 'service_name', 'app', 'application', 'component'):
                col_map['service'] = idx
            elif col in ('message', 'msg', 'log', 'text', 'description', 'payload'):
                col_map['message'] = idx
            elif col in ('trace_id', 'traceid', 'trace'):
                col_map['traceId'] = idx
            elif col in ('request_id', 'requestid', 'req_id'):
                col_map['requestId'] = idx
            elif col in ('host_id', 'host', 'hostname'):
                col_map['hostId'] = idx

        for line_num, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == '' for c in row):
                continue
            try:
                raw_ts = row[col_map['timestamp']] if 'timestamp' in col_map and col_map['timestamp'] < len(row) else datetime.now(timezone.utc)
                raw_sev = row[col_map['severity']] if 'severity' in col_map and col_map['severity'] < len(row) else 'INFO'
                raw_svc = row[col_map['service']] if 'service' in col_map and col_map['service'] < len(row) else default_service
                raw_msg = row[col_map['message']] if 'message' in col_map and col_map['message'] < len(row) else " ".join(row)

                attributes = {}
                for idx, val in enumerate(row):
                    if idx < len(header) and idx not in col_map.values():
                        attributes[header[idx]] = val

                ts = normalization_service.normalize_timestamp(raw_ts)
                sev = normalization_service.normalize_severity(raw_sev)
                svc = normalization_service.normalize_service_name(raw_svc, default_service)
                msg, was_redacted = redaction_service.redact(raw_msg)
                fp = fingerprint_service.generate(msg)

                events.append({
                    "timestamp": ts,
                    "service": svc,
                    "severity": sev,
                    "message": msg,
                    "traceId": row[col_map['traceId']] if 'traceId' in col_map and col_map['traceId'] < len(row) else None,
                    "requestId": row[col_map['requestId']] if 'requestId' in col_map and col_map['requestId'] < len(row) else None,
                    "hostId": row[col_map['hostId']] if 'hostId' in col_map and col_map['hostId'] < len(row) else None,
                    "attributes": attributes,
                    "parseStatus": ParseStatus.OK,
                    "fingerprint": fp,
                    "redacted": was_redacted
                })
            except Exception as e:
                errors.append(LineError(line=line_num, raw=",".join(row), error=str(e)))

        return events, errors

    @classmethod
    def _parse_json(cls, content: str, default_service: str) -> Tuple[List[Dict[str, Any]], List[LineError]]:
        events = []
        errors = []
        try:
            data = json.loads(content)
        except Exception as e:
            # Fallback to jsonl
            return cls._parse_jsonl(content, default_service)

        items = data if isinstance(data, list) else [data]
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                errors.append(LineError(line=idx, raw=str(item), error="Item is not a JSON object"))
                continue
            parsed, err = cls._dict_to_event(item, idx, default_service)
            if parsed:
                events.append(parsed)
            if err:
                errors.append(err)
        return events, errors

    @classmethod
    def _parse_jsonl(cls, content: str, default_service: str) -> Tuple[List[Dict[str, Any]], List[LineError]]:
        events = []
        errors = []
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
                if not isinstance(item, dict):
                    errors.append(LineError(line=idx, raw=stripped, error="Line is not a JSON object"))
                    continue
                parsed, err = cls._dict_to_event(item, idx, default_service)
                if parsed:
                    events.append(parsed)
                if err:
                    errors.append(err)
            except Exception as e:
                errors.append(LineError(line=idx, raw=stripped, error=str(e)))
        return events, errors

    @classmethod
    def _dict_to_event(cls, item: Dict[str, Any], line_num: int, default_service: str) -> Tuple[Optional[Dict[str, Any]], Optional[LineError]]:
        try:
            raw_ts = item.get("timestamp") or item.get("time") or item.get("@timestamp") or item.get("ts") or datetime.now(timezone.utc)
            raw_sev = item.get("severity") or item.get("level") or item.get("loglevel") or "INFO"
            raw_svc = item.get("service") or item.get("service_name") or item.get("app") or default_service
            raw_msg = item.get("message") or item.get("msg") or item.get("log") or json.dumps(item)

            ts = normalization_service.normalize_timestamp(raw_ts)
            sev = normalization_service.normalize_severity(raw_sev)
            svc = normalization_service.normalize_service_name(raw_svc, default_service)
            msg, was_redacted = redaction_service.redact(str(raw_msg))
            fp = fingerprint_service.generate(msg)

            # Exclude known top-level keys into attributes
            known_keys = {"timestamp", "time", "@timestamp", "ts", "severity", "level", "loglevel",
                          "service", "service_name", "app", "message", "msg", "log", "traceId", "trace_id",
                          "requestId", "request_id", "hostId", "host"}
            attrs = {k: v for k, v in item.items() if k not in known_keys}

            return {
                "timestamp": ts,
                "service": svc,
                "severity": sev,
                "message": msg,
                "traceId": item.get("traceId") or item.get("trace_id"),
                "requestId": item.get("requestId") or item.get("request_id"),
                "hostId": item.get("hostId") or item.get("host"),
                "attributes": attrs,
                "parseStatus": ParseStatus.OK,
                "fingerprint": fp,
                "redacted": was_redacted
            }, None
        except Exception as e:
            return None, LineError(line=line_num, raw=json.dumps(item), error=str(e))

    @classmethod
    def _parse_text(cls, content: str, default_service: str) -> Tuple[List[Dict[str, Any]], List[LineError]]:
        events = []
        errors = []
        lines = content.splitlines()
        
        current_event: Optional[Dict[str, Any]] = None

        for line_num, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            is_continuation = (
                line.startswith((' ', '\t')) or
                any(line.strip().lower().startswith(ind) for ind in cls.STACKTRACE_INDICATORS)
            )

            if is_continuation and current_event is not None:
                # Attach to preceding event's message
                current_event["message"] += "\n" + line
                continue

            # Try match ISO application log
            match = cls.ISO_APP_REGEX.match(line)
            if match:
                if current_event:
                    cls._finalize_event(current_event)
                    events.append(current_event)

                d = match.groupdict()
                raw_ts = d.get('timestamp')
                raw_sev = d.get('severity') or 'INFO'
                raw_svc = d.get('service') or default_service
                raw_msg = d.get('message') or ''

                current_event = {
                    "raw_timestamp": raw_ts,
                    "raw_severity": raw_sev,
                    "raw_service": raw_svc,
                    "message": raw_msg,
                    "line_num": line_num,
                    "attributes": {}
                }
                continue

            # Try Syslog regex
            syslog_match = cls.SYSLOG_REGEX.match(line)
            if syslog_match:
                if current_event:
                    cls._finalize_event(current_event)
                    events.append(current_event)

                d = syslog_match.groupdict()
                current_event = {
                    "raw_timestamp": d.get('timestamp'),
                    "raw_severity": 'INFO',
                    "raw_service": d.get('service') or default_service,
                    "message": d.get('message') or '',
                    "hostId": d.get('host'),
                    "line_num": line_num,
                    "attributes": {}
                }
                continue

            # If no regex matched, check if it looks like a continuation or a fallback event
            if current_event and not re.match(r'^\d{4}-\d{2}-\d{2}', line):
                current_event["message"] += "\n" + line
            else:
                if current_event:
                    cls._finalize_event(current_event)
                    events.append(current_event)

                # Fallback heuristic: check if line contains an error keyword
                sev_found = 'INFO'
                for s in ['CRITICAL', 'FATAL', 'ERROR', 'WARN', 'WARNING', 'DEBUG']:
                    if f' {s} ' in f' {line} ' or f'[{s}]' in line:
                        sev_found = s
                        break

                current_event = {
                    "raw_timestamp": datetime.now(timezone.utc),
                    "raw_severity": sev_found,
                    "raw_service": default_service,
                    "message": line,
                    "line_num": line_num,
                    "attributes": {}
                }

        if current_event:
            cls._finalize_event(current_event)
            events.append(current_event)

        return events, errors

    @classmethod
    def _finalize_event(cls, event_dict: Dict[str, Any]):
        msg, was_redacted = redaction_service.redact(event_dict["message"])
        event_dict["message"] = msg
        event_dict["redacted"] = was_redacted
        event_dict["timestamp"] = normalization_service.normalize_timestamp(event_dict.pop("raw_timestamp", None))
        event_dict["severity"] = normalization_service.normalize_severity(event_dict.pop("raw_severity", None))
        event_dict["service"] = normalization_service.normalize_service_name(event_dict.pop("raw_service", None))
        event_dict["fingerprint"] = fingerprint_service.generate(msg)
        event_dict["parseStatus"] = ParseStatus.OK
        event_dict.pop("line_num", None)

parsing_service = ParsingService()
