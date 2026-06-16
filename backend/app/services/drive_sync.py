from __future__ import annotations

import io
import re
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document
from app.services.import_service import process_upload

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
PDF_MIME = "application/pdf"


def _get_drive_service():
    credentials_path = Path(settings.google_drive_credentials_json)
    if not credentials_path.is_file():
        raise FileNotFoundError(f"Google Drive credentials not found: {credentials_path}")
    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s.-]", "", name).strip()
    return cleaned.replace(" ", "_") or "unknown"


def _list_child_folders(service, parent_id: str) -> list[dict]:
    folders: list[dict] = []
    page_token = None
    query = (
        f"'{parent_id}' in parents and mimeType='{FOLDER_MIME}' and trashed=false"
    )
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,
                pageSize=100,
            )
            .execute()
        )
        folders.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return folders


def _list_folder_children(service, folder_id: str) -> list[dict]:
    files: list[dict] = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed=false"
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, md5Checksum)",
                pageToken=page_token,
                pageSize=100,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def _collect_pdfs_recursive(service, folder_id: str) -> list[dict]:
    pdfs: list[dict] = []
    for item in _list_folder_children(service, folder_id):
        if item.get("mimeType") == PDF_MIME:
            pdfs.append(item)
        elif item.get("mimeType") == FOLDER_MIME:
            pdfs.extend(_collect_pdfs_recursive(service, item["id"]))
    return pdfs


def _download_pdf(service, file_id: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id)
    buffer = io.FileIO(destination, "wb")
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.close()


def sync_google_drive(
    db: Session,
    folder_id: str | None = None,
    invoice_year: str | None = None,
) -> dict:
    root_id = folder_id or settings.google_drive_folder_id
    if not root_id:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID is not configured")

    year = invoice_year or settings.google_drive_invoice_year or None
    service = _get_drive_service()
    stats = {
        "invoice_year": year,
        "folder_id": root_id,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "suppliers": 0,
        "files": [],
    }

    upload_root = Path(settings.upload_dir) / "drive" / (year or "unsorted")
    supplier_folders = _list_child_folders(service, root_id)
    stats["suppliers"] = len(supplier_folders)

    for supplier_folder in supplier_folders:
        supplier_name = supplier_folder["name"].strip()
        supplier_id = supplier_folder["id"]
        for drive_file in _collect_pdfs_recursive(service, supplier_id):
            file_id = drive_file["id"]
            filename = drive_file["name"]

            existing = (
                db.query(Document)
                .filter(Document.drive_file_id == file_id)
                .first()
            )
            if existing:
                stats["skipped"] += 1
                stats["files"].append(
                    {"file": filename, "supplier": supplier_name, "status": "skipped"}
                )
                continue

            local_path = upload_root / _safe_name(supplier_name) / file_id / filename
            try:
                _download_pdf(service, file_id, local_path)
                doc = process_upload(
                    db,
                    str(local_path),
                    filename,
                    "invoice",
                    supplier_name=supplier_name,
                    drive_file_id=file_id,
                    invoice_year=year,
                )
                stats["processed"] += 1
                stats["files"].append(
                    {
                        "file": filename,
                        "supplier": supplier_name,
                        "status": doc.status,
                    }
                )
            except Exception as exc:
                db.rollback()
                stats["failed"] += 1
                stats["files"].append(
                    {
                        "file": filename,
                        "supplier": supplier_name,
                        "status": "failed",
                        "error": str(exc),
                    }
                )

    return stats
