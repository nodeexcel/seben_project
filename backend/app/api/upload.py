from __future__ import annotations
import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DocumentSourceType
from app.parsers import detect_source_type, parse_file
from app.schemas import ExtractionResult, UploadResponse
from app.services.import_service import process_upload

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {"whatsapp", "contact", "email", "invoice"}


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    source_type: str | None = Form(None),
    persist: bool = Form(False),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    detected = source_type or detect_source_type(file.filename)
    if detected not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4()}_{file.filename}"
    filepath = upload_dir / safe_name

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    with open(filepath, "wb") as f:
        f.write(content)

    if persist:
        doc = process_upload(db, str(filepath), file.filename, detected)
        extraction = None
        if doc.extracted_data:
            data = json.loads(doc.extracted_data)
            extraction = ExtractionResult(
                source_type=DocumentSourceType(detected),
                filename=file.filename,
                status=doc.status,
                extracted=data,
                errors=data.get("errors", []),
            )
        return UploadResponse(
            document_id=doc.id,
            filename=file.filename,
            source_type=DocumentSourceType(detected),
            status=doc.status,
            extraction=extraction,
        )

    result = parse_file(str(filepath), detected)
    extraction = ExtractionResult(
        source_type=DocumentSourceType(detected),
        filename=file.filename,
        status="preview",
        extracted=result.to_dict(),
        errors=result.errors,
    )
    return UploadResponse(
        document_id=0,
        filename=file.filename,
        source_type=DocumentSourceType(detected),
        status="preview",
        extraction=extraction,
    )


@router.get("/supported-types")
def supported_types():
    return {
        "types": [
            {"id": "whatsapp", "label": "WhatsApp Export", "extensions": [".txt"]},
            {"id": "contact", "label": "Contacts", "extensions": [".vcf", ".csv"]},
            {"id": "email", "label": "Email", "extensions": [".eml", ".mbox"]},
            {"id": "invoice", "label": "Invoice", "extensions": [".pdf"]},
        ]
    }
