#!/usr/bin/env python3
"""Import WhatsApp and email samples; optionally resync by removing prior sample imports."""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, Document, DocumentSourceType, Interaction, ProductInterest, Purchase
from app.services.import_service import import_directory


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sample_comm_paths(root: str) -> list[str]:
    return [
        os.path.join(root, "samples", "Whatsapp Conversations"),
        os.path.join(root, "samples", "Email examples"),
    ]


def delete_sample_communications(db: Session) -> dict:
    """Remove prior WhatsApp/email documents imported from samples/ folders."""
    stats = {"documents": 0, "interactions": 0, "product_interests": 0}
    docs = (
        db.query(Document)
        .filter(
            Document.source_type.in_(
                [DocumentSourceType.WHATSAPP, DocumentSourceType.EMAIL]
            ),
            Document.filepath.like("%/samples/%"),
        )
        .all()
    )
    company_ids: set[int] = set()
    for doc in docs:
        for interaction in db.query(Interaction).filter(Interaction.document_id == doc.id).all():
            company_ids.add(interaction.company_id)
            stats["interactions"] += 1
        db.query(Interaction).filter(Interaction.document_id == doc.id).delete()
        db.delete(doc)
        stats["documents"] += 1

    for company_id in company_ids:
        deleted = (
            db.query(ProductInterest)
            .filter(
                ProductInterest.company_id == company_id,
                ProductInterest.source.in_(["whatsapp", "email"]),
            )
            .delete(synchronize_session=False)
        )
        stats["product_interests"] += deleted

    db.commit()
    return stats


def cleanup_junk_email_companies(db: Session) -> int:
    """Remove orphan companies created from bad reply-subject email parsing."""
    junk_pattern = re.compile(r"^(re|r|fw|fwd):", re.I)
    removed = 0
    for company in db.query(Company).all():
        if not junk_pattern.match(company.name or ""):
            continue
        has_purchases = db.query(Purchase).filter(Purchase.company_id == company.id).count() > 0
        if has_purchases:
            continue
        db.query(ProductInterest).filter(ProductInterest.company_id == company.id).delete()
        db.query(Interaction).filter(Interaction.company_id == company.id).delete()
        db.delete(company)
        removed += 1
    if removed:
        db.commit()
    return removed


def import_communications(db: Session, directories: list[str]) -> dict:
    stats = {"processed": 0, "failed": 0, "files": []}
    for directory in directories:
        if not os.path.isdir(directory):
            print(f"Skipping missing directory: {directory}")
            continue
        print(f"Importing: {directory}")
        result = import_directory(db, directory)
        stats["processed"] += result["processed"]
        stats["failed"] += result["failed"]
        stats["files"].extend(result["files"])
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Import WhatsApp and email communication samples")
    parser.add_argument(
        "--resync",
        action="store_true",
        help="Delete prior sample WhatsApp/email imports before reimporting",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        help="Directories to import (default: samples/Whatsapp Conversations + samples/Email examples)",
    )
    args = parser.parse_args()

    root = _project_root()
    directories = args.directories or _sample_comm_paths(root)

    db = SessionLocal()
    try:
        if args.resync:
            removed = delete_sample_communications(db)
            print(
                f"Resync: removed {removed['documents']} documents, "
                f"{removed['interactions']} interactions, "
                f"{removed['product_interests']} product interests"
            )
            junk = cleanup_junk_email_companies(db)
            if junk:
                print(f"Resync: removed {junk} junk email-only companies")

        stats = import_communications(db, directories)
        print(f"Processed: {stats['processed']}, Failed: {stats['failed']}")
        for entry in stats["files"]:
            line = f"  {entry['file']}: {entry['status']}"
            if entry.get("error"):
                line += f" ({entry['error']})"
            print(line)
    finally:
        db.close()


if __name__ == "__main__":
    main()
