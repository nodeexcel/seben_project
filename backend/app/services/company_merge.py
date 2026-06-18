from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, Contact, Interaction, ProductInterest, Purchase
from app.utils.matching import company_match_score, contact_name_match_score

NAME_MATCH_THRESHOLD = 90.0
COMPANY_MATCH_THRESHOLD = 92.0


def merge_company_into(db: Session, source_id: int, target_id: int) -> None:
    if source_id == target_id:
        return

    db.query(Interaction).filter(Interaction.company_id == source_id).update(
        {"company_id": target_id}
    )
    db.query(Purchase).filter(Purchase.company_id == source_id).update(
        {"company_id": target_id}
    )
    db.query(ProductInterest).filter(ProductInterest.company_id == source_id).update(
        {"company_id": target_id}
    )

    target_contacts = db.query(Contact).filter(Contact.company_id == target_id).all()
    for contact in db.query(Contact).filter(Contact.company_id == source_id).all():
        existing = next(
            (
                c
                for c in target_contacts
                if contact_name_match_score(c.name, contact.name) >= NAME_MATCH_THRESHOLD
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
            contact.company_id = target_id

    source = db.query(Company).filter(Company.id == source_id).first()
    survivor = db.query(Company).filter(Company.id == target_id).first()
    if source and survivor and source.notes and not survivor.notes:
        survivor.notes = source.notes

    if source:
        db.delete(source)


def find_merge_candidates(
    db: Session,
    company_id: int,
    *,
    threshold: float = 85.0,
    limit: int = 10,
) -> list[dict]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return []

    purchase_counts = dict(
        db.query(Purchase.company_id, func.count(Purchase.id)).group_by(Purchase.company_id).all()
    )
    contact_counts = dict(
        db.query(Contact.company_id, func.count(Contact.id)).group_by(Contact.company_id).all()
    )

    candidates: list[dict] = []
    for other in db.query(Company).filter(Company.id != company_id).all():
        score = company_match_score(company.name, other.name)
        if score < threshold:
            continue
        candidates.append(
            {
                "id": other.id,
                "name": other.name,
                "score": round(score, 1),
                "contact_count": contact_counts.get(other.id, 0),
                "purchase_count": purchase_counts.get(other.id, 0),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:limit]


def merge_fuzzy_duplicate_companies(db: Session, threshold: float = COMPANY_MATCH_THRESHOLD) -> int:
    companies = db.query(Company).order_by(Company.id).all()
    purchase_counts = dict(
        db.query(Purchase.company_id, func.count(Purchase.id)).group_by(Purchase.company_id).all()
    )

    merged = 0
    removed: set[int] = set()

    for i, company_a in enumerate(companies):
        if company_a.id in removed:
            continue
        for company_b in companies[i + 1 :]:
            if company_b.id in removed:
                continue
            if company_match_score(company_a.name, company_b.name) < threshold:
                continue

            count_a = purchase_counts.get(company_a.id, 0)
            count_b = purchase_counts.get(company_b.id, 0)
            if count_a >= count_b:
                survivor, duplicate = company_a, company_b
            else:
                survivor, duplicate = company_b, company_a

            merge_company_into(db, duplicate.id, survivor.id)
            removed.add(duplicate.id)
            purchase_counts[survivor.id] = purchase_counts.get(survivor.id, 0) + purchase_counts.get(
                duplicate.id, 0
            )
            merged += 1

            if duplicate is company_a:
                break

    return merged
