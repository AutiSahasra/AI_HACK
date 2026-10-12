import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional, Callable

from app.models.upload import UploadRecord, UploadStatus, LineError
from app.models.log_event import LogSourceMeta, SourceType, ParseStatus
from app.services.parsing import parsing_service
from app.repositories.upload_repo import upload_repo
from app.repositories.log_event_repo import log_event_repo

class IngestionService:
    def __init__(self):
        # Callback for detection hooks (configured in Phase 2)
        self._detection_hook: Optional[Callable[[List[Dict[str, Any]]], Any]] = None

    def register_detection_hook(self, hook: Callable[[List[Dict[str, Any]]], Any]):
        self._detection_hook = hook

    async def process_file_upload(
        self,
        file_bytes: bytes,
        file_name: str,
        content_type: str,
        user_name: str
    ) -> UploadRecord:
        upload_id = str(uuid.uuid4())
        
        # 1. Decode text content
        try:
            content_str = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content_str = file_bytes.decode('latin-1')
            except Exception as e:
                failed_record = UploadRecord(
                    _id=upload_id,
                    fileName=file_name,
                    fileSize=len(file_bytes),
                    contentType=content_type,
                    detectedFormat="unknown",
                    status=UploadStatus.FAILED,
                    parsedCount=0,
                    failedCount=1,
                    errors=[LineError(line=1, raw="", error=f"File encoding error: {str(e)}")],
                    uploadedBy=user_name,
                    createdAt=datetime.now(timezone.utc),
                    completedAt=datetime.now(timezone.utc)
                )
                await upload_repo.create(failed_record.model_dump(by_alias=True))
                return failed_record

        # 2. Sniff format
        detected_format = parsing_service.sniff_format(file_name, content_str)

        # 3. Initial record
        record_doc = {
            "_id": upload_id,
            "fileName": file_name,
            "fileSize": len(file_bytes),
            "contentType": content_type,
            "detectedFormat": detected_format,
            "status": UploadStatus.PROCESSING.value,
            "parsedCount": 0,
            "failedCount": 0,
            "errors": [],
            "uploadedBy": user_name,
            "createdAt": datetime.now(timezone.utc)
        }
        await upload_repo.create(record_doc)

        # 4. Parse content
        parsed_events, line_errors = parsing_service.parse_content(content_str, detected_format)

        # 5. Attach source metadata
        now = datetime.now(timezone.utc)
        for ev in parsed_events:
            ev["_id"] = str(uuid.uuid4())
            ev["ingestedAt"] = now
            ev["source"] = {
                "type": SourceType.MANUAL_UPLOAD.value,
                "sourceId": upload_id,
                "fileName": file_name,
                "uploadId": upload_id
            }

        # 6. Save events to database
        if parsed_events:
            await log_event_repo.insert_many(parsed_events)

        # 7. Update status
        if line_errors and not parsed_events:
            final_status = UploadStatus.FAILED
        elif line_errors:
            final_status = UploadStatus.COMPLETED_WITH_ERRORS
        else:
            final_status = UploadStatus.COMPLETED

        update_dict = {
            "status": final_status.value,
            "parsedCount": len(parsed_events),
            "failedCount": len(line_errors),
            "errors": [err.model_dump() for err in line_errors],
            "completedAt": datetime.now(timezone.utc)
        }
        await upload_repo.update(upload_id, update_dict)

        # 8. Trigger detection hook if registered
        if parsed_events and self._detection_hook:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self._detection_hook):
                    await self._detection_hook(parsed_events)
                else:
                    self._detection_hook(parsed_events)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error in detection hook: {e}")

        record_doc.update(update_dict)
        return UploadRecord(**record_doc)

    async def process_live_events(
        self,
        raw_events: List[Dict[str, Any]],
        source_id: str
    ) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        normalized_events: List[Dict[str, Any]] = []

        from app.services.normalization import normalization_service
        from app.services.redaction import redaction_service
        from app.services.fingerprint import fingerprint_service

        for raw in raw_events:
            raw_ts = raw.get("timestamp") or raw.get("time") or now
            raw_sev = raw.get("severity") or raw.get("level") or "INFO"
            raw_svc = raw.get("service") or raw.get("service_name") or "demo-app"
            raw_msg = raw.get("message") or raw.get("msg") or str(raw)

            ts = normalization_service.normalize_timestamp(raw_ts)
            sev = normalization_service.normalize_severity(raw_sev)
            svc = normalization_service.normalize_service_name(raw_svc)
            msg, was_redacted = redaction_service.redact(raw_msg)
            fp = fingerprint_service.generate(msg)

            ev = {
                "_id": str(uuid.uuid4()),
                "timestamp": ts,
                "ingestedAt": now,
                "service": svc,
                "severity": sev.value if hasattr(sev, "value") else sev,
                "message": msg,
                "source": {
                    "type": SourceType.LIVE.value,
                    "sourceId": source_id,
                    "fileName": None,
                    "uploadId": None
                },
                "traceId": raw.get("traceId") or raw.get("trace_id"),
                "requestId": raw.get("requestId") or raw.get("request_id"),
                "hostId": raw.get("hostId") or raw.get("host"),
                "attributes": {k: v for k, v in raw.items() if k not in {"timestamp", "time", "severity", "level", "service", "message", "msg", "traceId", "trace_id", "requestId", "request_id"}},
                "parseStatus": ParseStatus.OK.value,
                "parseError": None,
                "fingerprint": fp,
                "redacted": was_redacted
            }
            normalized_events.append(ev)

        if normalized_events:
            await log_event_repo.insert_many(normalized_events)

            # Trigger detection hook
            if self._detection_hook:
                try:
                    import asyncio
                    if asyncio.iscoroutinefunction(self._detection_hook):
                        await self._detection_hook(normalized_events)
                    else:
                        self._detection_hook(normalized_events)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Error in detection hook: {e}")

        return normalized_events

ingestion_service = IngestionService()
