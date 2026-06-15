from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
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
