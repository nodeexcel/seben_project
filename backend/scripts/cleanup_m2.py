#!/usr/bin/env python3
"""M2 data quality cleanup: suppliers, contacts, companies, product names, supporting-doc purchases."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Company, Contact, Document, ProductInterest, Purchase
from app.parsers.invoice import _clean_product_name, classify_invoice_document
from app.services.company_merge import merge_fuzzy_duplicate_companies
from app.utils.normalize import normalize_supplier_name


def normalize_suppliers(db) -> int:
    updated = 0
    for purchase in db.query(Purchase).filter(Purchase.supplier_name.isnot(None)).all():
        normalized = normalize_supplier_name(purchase.supplier_name)
        if normalized and normalized != purchase.supplier_name:
            purchase.supplier_name = normalized
            updated += 1
    for doc in db.query(Document).filter(Document.supplier_name.isnot(None)).all():
        normalized = normalize_supplier_name(doc.supplier_name)
        if normalized and normalized != doc.supplier_name:
            doc.supplier_name = normalized
            updated += 1
    return updated


def remove_unknown_contacts(db) -> int:
    count = (
        db.query(Contact)
        .filter(Contact.name.ilike("unknown"), Contact.email.is_(None))
        .delete(synchronize_session=False)
    )
    return count


def remove_supporting_doc_purchases(db) -> int:
    removed = 0
    docs = db.query(Document).filter(Document.source_type == "invoice").all()
    for doc in docs:
        if classify_invoice_document(doc.filename) != "supporting":
            continue
        deleted = (
            db.query(Purchase)
            .filter(Purchase.document_id == doc.id)
            .delete(synchronize_session=False)
        )
        removed += deleted
    return removed


def clean_product_names(db) -> int:
    updated = 0
    for purchase in db.query(Purchase).filter(Purchase.product_name_raw.isnot(None)).all():
        cleaned = _clean_product_name(purchase.product_name_raw)
        if cleaned and cleaned != purchase.product_name_raw:
            purchase.product_name_raw = cleaned
            updated += 1
    return updated


def print_stats(db) -> None:
    print("\n--- Database summary ---")
    print(f"Companies:  {db.query(Company).count()}")
    print(f"Contacts:   {db.query(Contact).count()}")
    print(f"Purchases:  {db.query(Purchase).count()}")
    print(f"Drive docs: {db.query(Document).filter(Document.drive_file_id.isnot(None)).count()}")
    suppliers = (
        db.query(Purchase.supplier_name, func.count())
        .filter(Purchase.supplier_name.isnot(None))
        .group_by(Purchase.supplier_name)
        .order_by(func.count().desc())
        .limit(8)
        .all()
    )
    print(f"Top suppliers: {suppliers}")
    unknown = db.query(Contact).filter(Contact.name.ilike("unknown")).count()
    print(f"Unknown contacts remaining: {unknown}")


def main():
    dry_run = "--dry-run" in sys.argv
    db = SessionLocal()
    try:
        print("M2 cleanup starting...")
        print_stats(db)

        if dry_run:
            print("\nDry run — no changes committed.")
            return

        suppliers = normalize_suppliers(db)
        print(f"Supplier names normalized: {suppliers}")

        contacts = remove_unknown_contacts(db)
        print(f"Unknown contacts removed: {contacts}")

        purchases = remove_supporting_doc_purchases(db)
        print(f"Purchases from supporting docs removed: {purchases}")

        products = clean_product_names(db)
        print(f"Product names cleaned: {products}")

        merged = merge_fuzzy_duplicate_companies(db)
        print(f"Duplicate companies merged: {merged}")

        db.commit()
        print("\nCleanup committed.")
        print_stats(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
