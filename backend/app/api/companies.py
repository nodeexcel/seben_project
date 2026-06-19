from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Company, Contact, Interaction, Product, ProductCategory, ProductInterest, Purchase
from app.schemas import (
    CompanyCreate,
    CompanyDetail,
    CompanyListItem,
    CompanyMergeRequest,
    CompanyUpdate,
    ContactCreate,
    ContactUpdate,
    InteractionBrief,
    MergeCandidate,
    PurchaseCreate,
    PurchaseResponse,
)
from app.services.company_merge import find_merge_candidates, merge_company_into
from app.utils.normalize import normalize_email, normalize_phone

router = APIRouter(prefix="/companies", tags=["companies"])

PURCHASE_LIMIT = 100


def _build_company_detail(db: Session, company_id: int) -> CompanyDetail:
    company = (
        db.query(Company)
        .options(
            joinedload(Company.contacts),
            joinedload(Company.product_interests),
        )
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    purchases = (
        db.query(Purchase)
        .filter(Purchase.company_id == company_id)
        .order_by(Purchase.purchase_date.desc().nullslast(), Purchase.id.desc())
        .limit(PURCHASE_LIMIT)
        .all()
    )
    purchase_count = (
        db.query(func.count(Purchase.id)).filter(Purchase.company_id == company_id).scalar() or 0
    )

    return CompanyDetail(
        id=company.id,
        name=company.name,
        country=company.country,
        product_category=company.product_category,
        notes=company.notes,
        first_interaction_date=company.first_interaction_date,
        last_interaction_date=company.last_interaction_date,
        ai_summary=company.ai_summary,
        contacts=company.contacts,
        purchases=purchases,
        purchase_count=purchase_count,
        product_interests=company.product_interests,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def _get_contact_for_company(db: Session, company_id: int, contact_id: int) -> Contact:
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.company_id == company_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.get("/", response_model=list[CompanyListItem])
def list_companies(
    q: str | None = Query(None),
    product: str | None = Query(None),
    country: str | None = Query(None),
    category: ProductCategory | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Company)

    if q:
        query = query.filter(
            or_(
                Company.name.ilike(f"%{q}%"),
                Company.id.in_(
                    db.query(Contact.company_id).filter(Contact.name.ilike(f"%{q}%"))
                ),
            )
        )
    if country:
        query = query.filter(Company.country.ilike(f"%{country}%"))
    if category:
        query = query.filter(Company.product_category == category)
    if product:
        purchase_ids = db.query(Purchase.company_id).filter(
            Purchase.product_name_raw.ilike(f"%{product}%")
        )
        interest_ids = db.query(ProductInterest.company_id).filter(
            ProductInterest.product_name_raw.ilike(f"%{product}%")
        )
        query = query.filter(
            or_(Company.id.in_(purchase_ids), Company.id.in_(interest_ids))
        )

    companies = query.order_by(Company.name).all()
    results: list[CompanyListItem] = []

    for company in companies:
        contact_count = db.query(func.count(Contact.id)).filter(
            Contact.company_id == company.id
        ).scalar() or 0
        totals = db.query(
            func.coalesce(func.sum(Purchase.revenue), 0),
            func.coalesce(func.sum(Purchase.quantity), 0),
        ).filter(Purchase.company_id == company.id).one()

        results.append(
            CompanyListItem(
                id=company.id,
                name=company.name,
                country=company.country,
                product_category=company.product_category,
                first_interaction_date=company.first_interaction_date,
                last_interaction_date=company.last_interaction_date,
                contact_count=contact_count,
                total_revenue=float(totals[0]),
                total_quantity=float(totals[1]),
            )
        )

    return results


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(company_id: int, db: Session = Depends(get_db)):
    return _build_company_detail(db, company_id)


@router.get("/{company_id}/interactions", response_model=list[InteractionBrief])
def list_company_interactions(
    company_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _build_company_detail(db, company_id)
    return (
        db.query(Interaction)
        .filter(Interaction.company_id == company_id)
        .order_by(Interaction.interaction_date.desc().nullslast(), Interaction.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/{company_id}/merge-candidates", response_model=list[MergeCandidate])
def merge_candidates(company_id: int, db: Session = Depends(get_db)):
    _build_company_detail(db, company_id)
    return find_merge_candidates(db, company_id)


@router.post("/{company_id}/merge", response_model=CompanyDetail)
def merge_company(
    company_id: int,
    payload: CompanyMergeRequest,
    db: Session = Depends(get_db),
):
    if payload.duplicate_company_id == company_id:
        raise HTTPException(status_code=400, detail="Cannot merge a company with itself")

    _build_company_detail(db, company_id)
    duplicate = db.query(Company).filter(Company.id == payload.duplicate_company_id).first()
    if not duplicate:
        raise HTTPException(status_code=404, detail="Duplicate company not found")

    merge_company_into(db, payload.duplicate_company_id, company_id)
    db.commit()
    return _build_company_detail(db, company_id)


@router.post("/", response_model=CompanyDetail, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return _build_company_detail(db, company.id)


@router.patch("/{company_id}", response_model=CompanyDetail)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    return _build_company_detail(db, company_id)


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    purchase_count = (
        db.query(func.count(Purchase.id)).filter(Purchase.company_id == company_id).scalar() or 0
    )
    if purchase_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete a company with {purchase_count} purchase record(s). "
                "Merge it into another company or contact support."
            ),
        )

    db.delete(company)
    db.commit()


@router.post("/{company_id}/contacts", response_model=CompanyDetail, status_code=201)
def add_contact(company_id: int, payload: ContactCreate, db: Session = Depends(get_db)):
    _build_company_detail(db, company_id)

    contact = Contact(
        company_id=company_id,
        name=payload.name.strip(),
        email=normalize_email(payload.email),
        phone=normalize_phone(payload.phone),
    )
    db.add(contact)
    db.commit()
    return _build_company_detail(db, company_id)


@router.patch("/{company_id}/contacts/{contact_id}", response_model=CompanyDetail)
def update_contact(
    company_id: int,
    contact_id: int,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
):
    contact = _get_contact_for_company(db, company_id, contact_id)

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        contact.name = updates["name"].strip()
    if "email" in updates:
        contact.email = normalize_email(updates["email"])
    if "phone" in updates:
        contact.phone = normalize_phone(updates["phone"])

    db.commit()
    return _build_company_detail(db, company_id)


@router.delete("/{company_id}/contacts/{contact_id}", response_model=CompanyDetail)
def delete_contact(company_id: int, contact_id: int, db: Session = Depends(get_db)):
    contact = _get_contact_for_company(db, company_id, contact_id)
    db.delete(contact)
    db.commit()
    return _build_company_detail(db, company_id)


@router.post("/{company_id}/purchases", response_model=PurchaseResponse, status_code=201)
def add_purchase(company_id: int, payload: PurchaseCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    purchase = Purchase(company_id=company_id, **payload.model_dump(exclude={"company_id"}))
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase
