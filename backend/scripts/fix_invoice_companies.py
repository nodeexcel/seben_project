#!/usr/bin/env python3
"""Re-parse invoice PDFs and reassign purchases to the correct client company."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Company, Document, DocumentSourceType, Interaction, ProductInterest, Purchase
from app.parsers.invoice import is_plausible_company_name, parse_invoice
from app.services.linking import resolve_company

JUNK_NAME_MARKERS = (
    "zona de produccion",
    "pais de origen",
    "octopus vulgaris",
    "dicentrarchus labrax",
    "sparus aurata",
    "#sayi/",
)


def _is_junk_company(name: str) -> bool:
    lower = (name or "").lower()
    return any(marker in lower for marker in JUNK_NAME_MARKERS) or not is_plausible_company_name(
        name, allow_short=True
    )


def _can_delete_company(db, company_id: int) -> bool:
    purchase_count = db.query(func.count(Purchase.id)).filter(Purchase.company_id == company_id).scalar() or 0
    if purchase_count > 0:
        return False
    interaction_count = (
        db.query(func.count(Interaction.id)).filter(Interaction.company_id == company_id).scalar() or 0
    )
    return interaction_count == 0


def purge_orphan_junk_companies(db, *, dry_run: bool = False) -> int:
    removed = 0
    for company in db.query(Company).all():
        if is_plausible_company_name(company.name):
            continue
        purchase_count = db.query(Purchase).filter(Purchase.company_id == company.id).count()
        interaction_count = db.query(Interaction).filter(Interaction.company_id == company.id).count()
        if purchase_count or interaction_count:
            continue
        if not dry_run:
            db.query(ProductInterest).filter(ProductInterest.company_id == company.id).delete()
            db.delete(company)
        removed += 1
    if not dry_run and removed:
        db.commit()
    return removed


def fix_invoice_companies(db, *, supplier: str | None = None, dry_run: bool = False) -> dict:
    stats = {
        "documents_checked": 0,
        "documents_updated": 0,
        "purchases_moved": 0,
        "companies_deleted": 0,
    }
    orphaned_company_ids: set[int] = set()

    query = db.query(Document).filter(Document.source_type == DocumentSourceType.INVOICE)
    if supplier:
        query = query.filter(Document.supplier_name.ilike(f"%{supplier}%"))

    for doc in query.order_by(Document.id):
        if not doc.filepath or not Path(doc.filepath).is_file():
            continue

        purchases = db.query(Purchase).filter(Purchase.document_id == doc.id).all()
        if not purchases:
            continue

        stats["documents_checked"] += 1
        result = parse_invoice(doc.filepath)
        if not result.company_name or not is_plausible_company_name(result.company_name, allow_short=True):
            continue

        target = resolve_company(db, result.company_name, source_type="invoice")
        moved = 0
        for purchase in purchases:
            if purchase.company_id != target.id:
                orphaned_company_ids.add(purchase.company_id)
                if not dry_run:
                    purchase.company_id = target.id
                moved += 1

        if moved:
            stats["documents_updated"] += 1
            stats["purchases_moved"] += moved

    if not dry_run:
        db.commit()

        for company_id in orphaned_company_ids:
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company or not _is_junk_company(company.name):
                continue
            if not _can_delete_company(db, company_id):
                continue
            db.query(ProductInterest).filter(ProductInterest.company_id == company_id).delete()
            db.delete(company)
            stats["companies_deleted"] += 1

        if stats["companies_deleted"]:
            db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix mislinked invoice client companies")
    parser.add_argument("--supplier", help="Only reprocess invoices from this supplier (e.g. Avramar)")
    parser.add_argument("--purge-orphans", action="store_true", help="Delete junk companies with no purchases")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without saving")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = {"documents_checked": 0, "documents_updated": 0, "purchases_moved": 0, "companies_deleted": 0}
        if args.purge_orphans and not args.supplier:
            stats["companies_deleted"] = purge_orphan_junk_companies(db, dry_run=args.dry_run)
        else:
            stats = fix_invoice_companies(db, supplier=args.supplier, dry_run=args.dry_run)
            if args.purge_orphans:
                stats["companies_deleted"] += purge_orphan_junk_companies(db, dry_run=args.dry_run)
        mode = "Dry run" if args.dry_run else "Done"
        print(
            f"{mode}: checked {stats['documents_checked']} invoice documents, "
            f"updated {stats['documents_updated']}, "
            f"moved {stats['purchases_moved']} purchases, "
            f"deleted {stats['companies_deleted']} junk companies"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
