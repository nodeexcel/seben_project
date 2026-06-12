from __future__ import annotations
from sqlalchemy.orm import Session

from app.models import Company, Contact
from app.utils.matching import company_match_score, is_likely_same_contact
from app.utils.normalize import normalize_company_name, normalize_email, normalize_phone


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

    query = db.query(Contact)
    for contact in query.all():
        if is_likely_same_contact(contact.email, contact.phone, email, phone):
            if company_id and not contact.company_id:
                contact.company_id = company_id
            return contact

    contact = Contact(
        name=name.strip(),
        email=norm_email,
        phone=norm_phone,
        company_id=company_id,
    )
    db.add(contact)
    db.flush()
    return contact
