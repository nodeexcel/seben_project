#!/usr/bin/env python3
"""Re-sync contacts from the phone vCard export and merge obvious duplicate companies."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Company, Contact, Interaction, ProductInterest, Purchase
from app.parsers.contacts import parse_contacts
from app.services.linking import find_or_create_company, find_or_create_contact
from app.utils.matching import contact_name_match_score

NAME_MATCH_THRESHOLD = 90.0


def merge_duplicate_person_companies(db) -> int:
    """Move interactions from orphan companies named after a known contact."""
    merged = 0
    companies = db.query(Company).all()
    contacts = db.query(Contact).all()

    for orphan in companies:
        if not orphan.name.strip():
            continue
        matches = [
            c
            for c in contacts
            if c.company_id
            and c.company_id != orphan.id
            and contact_name_match_score(c.name, orphan.name) >= NAME_MATCH_THRESHOLD
            and (c.phone or c.email)
        ]
        if not matches:
            continue

        target_company_id = matches[0].company_id
        if orphan.id == target_company_id:
            continue

        db.query(Interaction).filter(Interaction.company_id == orphan.id).update(
            {"company_id": target_company_id}
        )
        db.query(Purchase).filter(Purchase.company_id == orphan.id).update(
            {"company_id": target_company_id}
        )
        db.query(ProductInterest).filter(ProductInterest.company_id == orphan.id).update(
            {"company_id": target_company_id}
        )

        orphan_contacts = db.query(Contact).filter(Contact.company_id == orphan.id).all()
        for contact in orphan_contacts:
            existing = next(
                (
                    c
                    for c in contacts
                    if c.company_id == target_company_id
                    and contact_name_match_score(c.name, contact.name) >= NAME_MATCH_THRESHOLD
                ),
                None,
            )
            if existing:
                if contact.phone and not existing.phone:
                    existing.phone = contact.phone
                if contact.email and not existing.email:
                    existing.email = contact.email
                db.delete(contact)
            else:
                contact.company_id = target_company_id

        db.delete(orphan)
        merged += 1

    return merged


def main():
    vcf_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "samples",
        "Phone contacts list",
        "All Contacts.vcf",
    )
    if len(sys.argv) > 1:
        vcf_path = sys.argv[1]

    print(f"Re-syncing contacts from: {vcf_path}")
    result = parse_contacts(vcf_path)
    if result.errors:
        print("Parse warnings:", result.errors)

    db = SessionLocal()
    try:
        synced = 0
        for parsed in result.contacts:
            company = None
            if parsed.company_name:
                company = find_or_create_company(db, parsed.company_name)

            phones = parsed.phones or ([parsed.phone] if parsed.phone else [None])
            for index, phone in enumerate(phones):
                find_or_create_contact(
                    db,
                    name=parsed.name,
                    email=parsed.email if index == 0 else None,
                    phone=phone,
                    company_id=company.id if company else None,
                )
                synced += 1

        merged = merge_duplicate_person_companies(db)
        db.commit()
        print(f"Synced contact phone entries: {synced}")
        print(f"Merged duplicate person-companies: {merged}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
