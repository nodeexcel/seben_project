from __future__ import annotations
from sqlalchemy.orm import Session

from app.models import Company, Contact
from app.utils.matching import company_match_score, contact_name_match_score
from app.utils.normalize import normalize_company_name, normalize_email, normalize_phone

NAME_MATCH_THRESHOLD = 90.0
COMPANY_MATCH_THRESHOLD = 85.0


def find_company_by_name(db: Session, name: str, threshold: float = COMPANY_MATCH_THRESHOLD) -> Company | None:
    best_company: Company | None = None
    best_score = 0.0
    for company in db.query(Company).all():
        score = company_match_score(company.name, name)
        if score >= threshold and score > best_score:
            best_score = score
            best_company = company
    return best_company


def resolve_company(db: Session, name: str, *, source_type: str | None = None) -> Company:
    """Match an extracted name to an existing company, or create one."""
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("Company name is required")

    if source_type == "whatsapp":
        by_contact = find_company_by_contact_name(db, cleaned)
        if by_contact:
            return by_contact

    by_name = find_company_by_name(db, cleaned)
    if by_name:
        return by_name

    return find_or_create_company(db, cleaned)


def find_company_by_contact_name(db: Session, name: str) -> Company | None:
    """Resolve a WhatsApp/chat display name to an existing company via known contacts."""
    best_company: Company | None = None
    best_score = 0.0
    for contact in db.query(Contact).filter(Contact.company_id.isnot(None)).all():
        score = contact_name_match_score(contact.name, name)
        if score >= NAME_MATCH_THRESHOLD and score > best_score:
            best_score = score
            best_company = db.query(Company).filter(Company.id == contact.company_id).first()
    return best_company


def find_or_create_company(db: Session, name: str, country: str | None = None) -> Company:
    normalized = normalize_company_name(name)
    if normalized:
        existing = db.query(Company).all()
        for company in existing:
            if company_match_score(company.name, name) >= 85.0:
                return company

    company = Company(name=name.strip(), country=country)
    db.add(company)
    db.flush()
    return company


def find_or_create_contact(
    db: Session,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    company_id: int | None = None,
) -> Contact:
    norm_email = normalize_email(email)
    norm_phone = normalize_phone(phone)
    name = name.strip()

    if norm_email:
        for contact in db.query(Contact).filter(Contact.email == norm_email).all():
            if _merge_contact_fields(contact, name, norm_email, norm_phone, company_id):
                return contact

    if norm_phone:
        for contact in db.query(Contact).filter(Contact.phone == norm_phone).all():
            if _merge_contact_fields(contact, name, norm_email, norm_phone, company_id):
                return contact

    if company_id:
        for contact in db.query(Contact).filter(Contact.company_id == company_id).all():
            if contact_name_match_score(contact.name, name) >= NAME_MATCH_THRESHOLD:
                if norm_phone and contact.phone and contact.phone != norm_phone:
                    continue
                if _merge_contact_fields(contact, name, norm_email, norm_phone, company_id):
                    return contact

    if name:
        for contact in db.query(Contact).all():
            if contact_name_match_score(contact.name, name) < NAME_MATCH_THRESHOLD:
                continue
            if company_id and contact.company_id and contact.company_id != company_id:
                continue
            if norm_phone and contact.phone and contact.phone != norm_phone:
                continue
            target_company_id = company_id or contact.company_id
            if _merge_contact_fields(contact, name, norm_email, norm_phone, target_company_id):
                return contact

    contact = Contact(
        name=name,
        email=norm_email,
        phone=norm_phone,
        company_id=company_id,
    )
    db.add(contact)
    db.flush()
    return contact


def _merge_contact_fields(
    contact: Contact,
    name: str,
    email: str | None,
    phone: str | None,
    company_id: int | None,
) -> bool:
    if email and not contact.email:
        contact.email = email
    if phone and not contact.phone:
        contact.phone = phone
    elif phone and contact.phone and contact.phone != phone:
        return False
    if company_id and not contact.company_id:
        contact.company_id = company_id
    if name and contact.name != name and contact_name_match_score(contact.name, name) >= NAME_MATCH_THRESHOLD:
        contact.name = name
    return True
