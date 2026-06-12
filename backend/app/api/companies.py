from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Company, Contact, Product, Purchase
from app.schemas import (
    CompanyCreate,
    CompanyDetail,
    CompanyListItem,
    CompanyUpdate,
    ContactCreate,
    ContactResponse,
    PurchaseCreate,
    PurchaseResponse,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=list[CompanyListItem])
def list_companies(
    q: str | None = Query(None),
    product: str | None = Query(None),
    country: str | None = Query(None),
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
    if product:
        query = query.filter(
            Company.id.in_(
                db.query(Purchase.company_id).filter(
                    Purchase.product_name_raw.ilike(f"%{product}%")
                )
            )
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
    company = (
        db.query(Company)
        .options(joinedload(Company.contacts), joinedload(Company.purchases))
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("/", response_model=CompanyDetail, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompanyDetail)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company


@router.post("/{company_id}/contacts", response_model=ContactResponse, status_code=201)
def add_contact(company_id: int, payload: ContactCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    contact = Contact(company_id=company_id, **payload.model_dump(exclude={"company_id"}))
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


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
