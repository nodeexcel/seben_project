from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.drive_sync import sync_google_drive
from app.services.import_service import import_directory

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/samples")
def import_samples(
    directory: str | None = Query(None, description="Path to samples directory"),
    db: Session = Depends(get_db),
):
    samples_dir = directory or str(Path(settings.upload_dir).parent / "samples")
    if not Path(samples_dir).exists():
        return {"error": f"Directory not found: {samples_dir}"}
    stats = import_directory(db, samples_dir)
    return stats


@router.post("/drive")
def import_drive(
    folder_id: str | None = Query(None, description="Google Drive root folder ID for this year"),
    invoice_year: str | None = Query(None, description="Label for this import, e.g. 2025"),
    db: Session = Depends(get_db),
):
    if not settings.drive_enabled and not folder_id:
        return {
            "error": "Google Drive is not configured. Set GOOGLE_DRIVE_FOLDER_ID and GOOGLE_DRIVE_CREDENTIALS_JSON."
        }
    try:
        return sync_google_drive(
            db,
            folder_id=folder_id or settings.google_drive_folder_id,
            invoice_year=invoice_year or settings.google_drive_invoice_year or None,
        )
    except FileNotFoundError as exc:
        return {"error": str(exc)}
    except ValueError as exc:
        return {"error": str(exc)}
