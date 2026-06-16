#!/usr/bin/env python3
"""Sync invoice PDFs from Google Drive (one folder per supplier)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import SessionLocal, engine
from app.services.drive_sync import sync_google_drive


def ensure_schema() -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255)"
        )
        conn.exec_driver_sql(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR(255)"
        )
        conn.exec_driver_sql(
            "ALTER TABLE purchases ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255)"
        )
        conn.exec_driver_sql(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS invoice_year VARCHAR(10)"
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_drive_file_id
            ON documents (drive_file_id)
            WHERE drive_file_id IS NOT NULL
            """
        )


def main():
    if not settings.drive_enabled:
        print("Configure GOOGLE_DRIVE_FOLDER_ID and GOOGLE_DRIVE_CREDENTIALS_JSON in .env")
        sys.exit(1)

    ensure_schema()
    folder_id = None
    invoice_year = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--year" and i + 1 < len(args):
            invoice_year = args[i + 1]
            i += 2
        elif not folder_id:
            folder_id = args[i]
            i += 1
        else:
            i += 1

    db = SessionLocal()
    try:
        stats = sync_google_drive(db, folder_id=folder_id, invoice_year=invoice_year)
        year_label = stats.get("invoice_year") or "not set"
        print(f"Invoice year: {year_label}")
        print(
            f"Suppliers: {stats['suppliers']} | "
            f"Processed: {stats['processed']} | "
            f"Skipped: {stats['skipped']} | "
            f"Failed: {stats['failed']}"
        )
        for item in stats["files"]:
            line = f"  [{item['supplier']}] {item['file']}: {item['status']}"
            if item.get("error"):
                line += f" ({item['error']})"
            print(line)
    finally:
        db.close()


if __name__ == "__main__":
    main()
