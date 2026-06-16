#!/usr/bin/env python3
"""Sync invoice PDFs from all configured Google Drive year folders."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import SessionLocal, engine
from app.services.drive_sync import sync_google_drive

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config",
    "drive_folders.json",
)


def ensure_schema() -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255)"
        )
        conn.exec_driver_sql(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR(255)"
        )
        conn.exec_driver_sql(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS invoice_year VARCHAR(10)"
        )
        conn.exec_driver_sql(
            "ALTER TABLE purchases ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(255)"
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_documents_drive_file_id
            ON documents (drive_file_id)
            WHERE drive_file_id IS NOT NULL
            """
        )


def load_folders() -> dict[str, str]:
    if not os.path.isfile(CONFIG_PATH):
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {str(year): folder_id for year, folder_id in sorted(data.items())}


def main():
    if not settings.google_drive_credentials_json:
        print("Set GOOGLE_DRIVE_CREDENTIALS_JSON in .env")
        sys.exit(1)

    ensure_schema()
    folders = load_folders()
    years = sys.argv[1:] or list(folders.keys())

    db = SessionLocal()
    totals = {"processed": 0, "skipped": 0, "failed": 0}
    try:
        for year in years:
            folder_id = folders.get(year)
            if not folder_id:
                print(f"Year {year} not in {CONFIG_PATH}")
                continue
            print(f"\n=== Syncing {year} ({folder_id}) ===")
            stats = sync_google_drive(db, folder_id=folder_id, invoice_year=year)
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
            totals["processed"] += stats["processed"]
            totals["skipped"] += stats["skipped"]
            totals["failed"] += stats["failed"]
    finally:
        db.close()

    print(
        f"\nTOTAL | Processed: {totals['processed']} | "
        f"Skipped: {totals['skipped']} | Failed: {totals['failed']}"
    )


if __name__ == "__main__":
    main()
