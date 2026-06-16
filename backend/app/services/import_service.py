from __future__ import annotations
import json
from datetime import date, datetime

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.models import (
    Company,
    Document,
    DocumentSourceType,
    Interaction,
    InteractionType,
    Product,
    ProductCategory,
    ProductInterest,
    Purchase,
)
from app.parsers import parse_file
from app.services.linking import find_company_by_contact_name, find_or_create_company, find_or_create_contact
from app.services.product_detection import classify_company_form, detect_form_in_text
from app.utils.normalize import normalize_supplier_name


def process_upload(
    db: Session,
    filepath: str,
    filename: str,
    source_type: str,
    *,
    supplier_name: str | None = None,
    drive_file_id: str | None = None,
    invoice_year: str | None = None,
) -> Document:
    supplier_name = normalize_supplier_name(supplier_name)
    doc = Document(
        source_type=DocumentSourceType(source_type),
        filename=filename,
        filepath=filepath,
        supplier_name=supplier_name,
        invoice_year=invoice_year,
        drive_file_id=drive_file_id,
        status="processing",
    )
    db.add(doc)
    db.flush()

    try:
        result = parse_file(filepath, source_type)
        doc.extracted_data = json.dumps(result.to_dict())
        doc.status = "completed" if not result.errors else "completed_with_warnings"
        doc.processed_at = datetime.utcnow()

        _persist_extraction(db, result, doc.id, source_type, supplier_name=supplier_name)

    except Exception as exc:
        db.rollback()
        doc = Document(
            source_type=DocumentSourceType(source_type),
            filename=filename,
            filepath=filepath,
            supplier_name=supplier_name,
            invoice_year=invoice_year,
            drive_file_id=drive_file_id,
            status="failed",
            error_message=str(exc),
            processed_at=datetime.utcnow(),
        )
        db.add(doc)

    db.commit()
    db.refresh(doc)
    return doc


def import_directory(db: Session, directory: str) -> dict:
    from pathlib import Path

    from app.parsers import detect_source_type

    stats = {"processed": 0, "failed": 0, "files": []}
    root = Path(directory)

    for filepath in sorted(root.rglob("*")):
        if not filepath.is_file() or filepath.name.startswith("."):
            continue
        source_type = detect_source_type(filepath.name)
        if not source_type:
            if filepath.suffix.lower() == ".xlsx":
                source_type = "crm"
            else:
                continue
        try:
            doc = process_upload(db, str(filepath), filepath.name, source_type)
            stats["processed"] += 1
            stats["files"].append({"file": filepath.name, "status": doc.status})
        except Exception as exc:
            stats["failed"] += 1
            stats["files"].append({"file": filepath.name, "status": "failed", "error": str(exc)})

    return stats


def _persist_extraction(
    db: Session,
    result,
    document_id: int,
    source_type: str,
    *,
    supplier_name: str | None = None,
) -> None:
    companies_touched: list[Company] = []
    form_signals: set[str] = set()

    company = None
    if result.company_name:
        if source_type == "whatsapp":
            company = find_company_by_contact_name(db, result.company_name)
        if not company:
            company = find_or_create_company(db, result.company_name)
        companies_touched.append(company)

    for parsed_contact in result.contacts:
        if (
            source_type == "invoice"
            and parsed_contact.name.strip().lower() == "unknown"
            and not parsed_contact.email
        ):
            continue
        contact_company = company
        if parsed_contact.company_name:
            contact_company = find_or_create_company(db, parsed_contact.company_name)
            if contact_company not in companies_touched:
                companies_touched.append(contact_company)

        phones = parsed_contact.phones or ([parsed_contact.phone] if parsed_contact.phone else [None])
        for index, phone in enumerate(phones):
            find_or_create_contact(
                db,
                name=parsed_contact.name,
                email=parsed_contact.email if index == 0 else None,
                phone=phone,
                company_id=contact_company.id if contact_company else None,
            )

    for purchase_data in result.purchases:
        target = company
        if not target and companies_touched:
            target = companies_touched[0]
        if not target:
            continue

        product = _get_or_create_product(db, purchase_data.product_name)
        purchase = Purchase(
            company_id=target.id,
            product_id=product.id if product else None,
            product_name_raw=purchase_data.product_name,
            quantity=purchase_data.quantity,
            revenue=purchase_data.revenue,
            currency=purchase_data.currency or "EUR",
            purchase_date=_parse_date(purchase_data.purchase_date),
            supplier_name=supplier_name,
            document_id=document_id,
        )
        db.add(purchase)

        if purchase_data.product_name:
            form_signals |= detect_form_in_text(purchase_data.product_name)

    for interest in result.product_interests:
        target = company
        if not target and companies_touched:
            target = companies_touched[0]
        if not target:
            continue

        product = _get_or_create_product(db, interest.product_name)
        db.add(
            ProductInterest(
                company_id=target.id,
                product_id=product.id if product else None,
                product_name_raw=interest.product_name,
                source=interest.source or source_type,
            )
        )
        if interest.form and interest.form != "unknown":
            form_signals.add(interest.form)

    interaction_type_map = {
        "whatsapp": InteractionType.WHATSAPP,
        "email": InteractionType.EMAIL,
    }
    itype = interaction_type_map.get(source_type)
    if itype:
        for msg in result.messages:
            target = company or (companies_touched[0] if companies_touched else None)
            if not target:
                continue
            db.add(
                Interaction(
                    company_id=target.id,
                    interaction_type=itype,
                    content=(msg.content or "")[:5000],
                    interaction_date=_parse_datetime(msg.timestamp),
                    sender=msg.sender,
                    document_id=document_id,
                )
            )
            if msg.content:
                form_signals |= detect_form_in_text(msg.content)

    for comp in companies_touched:
        _update_company_category(comp, form_signals)
        _update_interaction_dates(comp, result)


def _get_or_create_product(db: Session, name: str | None) -> Product | None:
    if not name:
        return None
    existing = db.query(Product).filter(Product.name.ilike(name.strip())).first()
    if existing:
        return existing
    product = Product(name=name.strip()[:255])
    db.add(product)
    db.flush()
    return product


def _update_company_category(company: Company, signals: set[str]) -> None:
    if not signals:
        return
    label = classify_company_form(signals)
    mapping = {
        "Fresh": ProductCategory.FRESH,
        "Frozen": ProductCategory.FROZEN,
        "Both": ProductCategory.BOTH,
        "Unknown": ProductCategory.UNKNOWN,
    }
    new_cat = mapping[label]
    if company.product_category == ProductCategory.UNKNOWN:
        company.product_category = new_cat
    elif company.product_category != new_cat and new_cat != ProductCategory.UNKNOWN:
        if (
            (company.product_category == ProductCategory.FRESH and new_cat == ProductCategory.FROZEN)
            or (company.product_category == ProductCategory.FROZEN and new_cat == ProductCategory.FRESH)
        ):
            company.product_category = ProductCategory.BOTH


def _update_interaction_dates(company: Company, result) -> None:
    dates: list[date] = []
    for msg in result.messages:
        d = _parse_date(msg.timestamp)
        if d:
            dates.append(d)
    if not dates:
        return
    if not company.first_interaction_date or min(dates) < company.first_interaction_date:
        company.first_interaction_date = min(dates)
    if not company.last_interaction_date or max(dates) > company.last_interaction_date:
        company.last_interaction_date = max(dates)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date_parser.parse(value, dayfirst=True).date()
    except (ValueError, TypeError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return date_parser.parse(value, dayfirst=True)
    except (ValueError, TypeError):
        return None
