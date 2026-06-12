import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Document, DocumentSourceType
from app.parsers import parse_file
from app.services.linking import find_or_create_company, find_or_create_contact


def process_upload(db: Session, filepath: str, filename: str, source_type: str) -> Document:
    doc = Document(
        source_type=DocumentSourceType(source_type),
        filename=filename,
        filepath=filepath,
        status="processing",
    )
    db.add(doc)
    db.flush()

    try:
        result = parse_file(filepath, source_type)
        doc.extracted_data = json.dumps(result.to_dict())
        doc.status = "completed" if not result.errors else "completed_with_warnings"
        doc.processed_at = datetime.utcnow()

        _persist_extraction(db, result, doc.id)

    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)
        doc.processed_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)
    return doc


def _persist_extraction(db: Session, result, document_id: int) -> None:
    company = None
    if result.company_name:
        company = find_or_create_company(db, result.company_name)

    for parsed_contact in result.contacts:
        find_or_create_contact(
            db,
            name=parsed_contact.name,
            email=parsed_contact.email,
            phone=parsed_contact.phone,
            company_id=company.id if company else None,
        )

    # Purchase and interaction persistence will be expanded in Milestone 2/3
