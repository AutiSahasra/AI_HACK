from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import List, Optional
import os
from app.models.upload import UploadResponse, UploadRecord
from app.models.user import UserRole
from app.api.deps import get_current_user, require_roles
from app.services.ingestion import ingestion_service
from app.repositories.upload_repo import upload_repo
from app.core.config import settings

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".csv", ".txt", ".log", ".json", ".jsonl", ".ndjson"}

@router.post("", response_model=UploadResponse)
async def upload_log_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # 1. Validate file extension
    filename = file.filename or "unknown.log"
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 2. Read file content & check max size
    content_bytes = await file.read()
    if len(content_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB"
        )
    if len(content_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    # 3. Process ingestion
    username = current_user.get("username", "anonymous")
    content_type = file.content_type or "text/plain"
    record = await ingestion_service.process_file_upload(
        file_bytes=content_bytes,
        file_name=filename,
        content_type=content_type,
        user_name=username
    )

    return UploadResponse(
        id=str(record.id),
        fileName=record.fileName,
        fileSize=record.fileSize,
        detectedFormat=record.detectedFormat,
        status=record.status,
        parsedCount=record.parsedCount,
        failedCount=record.failedCount,
        errors=record.errors,
        uploadedBy=record.uploadedBy,
        createdAt=record.createdAt,
        completedAt=record.completedAt
    )

@router.get("", response_model=List[UploadResponse])
async def list_uploads(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    docs = await upload_repo.list_uploads(limit=limit)
    res = []
    for d in docs:
        res.append(UploadResponse(
            id=str(d["_id"]),
            fileName=d.get("fileName", "unknown"),
            fileSize=d.get("fileSize", 0),
            detectedFormat=d.get("detectedFormat", "text"),
            status=d.get("status", "completed"),
            parsedCount=d.get("parsedCount", 0),
            failedCount=d.get("failedCount", 0),
            errors=d.get("errors", []),
            uploadedBy=d.get("uploadedBy", "anonymous"),
            createdAt=d.get("createdAt"),
            completedAt=d.get("completedAt")
        ))
    return res

@router.get("/{upload_id}", response_model=UploadResponse)
async def get_upload_detail(
    upload_id: str,
    current_user: dict = Depends(get_current_user)
):
    doc = await upload_repo.get_by_id(upload_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload record not found")
    return UploadResponse(
        id=str(doc["_id"]),
        fileName=doc.get("fileName", "unknown"),
        fileSize=doc.get("fileSize", 0),
        detectedFormat=doc.get("detectedFormat", "text"),
        status=doc.get("status", "completed"),
        parsedCount=doc.get("parsedCount", 0),
        failedCount=doc.get("failedCount", 0),
        errors=doc.get("errors", []),
        uploadedBy=doc.get("uploadedBy", "anonymous"),
        createdAt=doc.get("createdAt"),
        completedAt=doc.get("completedAt")
    )
