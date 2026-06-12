from __future__ import annotations
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Purchase
from app.schemas import CustomerAnalytics, ProductAnalytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/customers", response_model=list[CustomerAnalytics])
def customer_analytics(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            Company.id,
            Company.name,
            func.coalesce(func.sum(Purchase.revenue), 0).label("total_revenue"),
            func.coalesce(func.sum(Purchase.quantity), 0).label("total_quantity"),
            func.count(Purchase.id).label("purchase_count"),
        )
        .outerjoin(Purchase, Purchase.company_id == Company.id)
    )

    if date_from:
        query = query.filter(Purchase.purchase_date >= date_from)
    if date_to:
        query = query.filter(Purchase.purchase_date <= date_to)

    rows = query.group_by(Company.id, Company.name).order_by(func.sum(Purchase.revenue).desc()).all()

    return [
        CustomerAnalytics(
            company_id=row.id,
            company_name=row.name,
            total_revenue=float(row.total_revenue),
            total_quantity=float(row.total_quantity),
            purchase_count=row.purchase_count,
        )
        for row in rows
    ]


@router.get("/products", response_model=list[ProductAnalytics])
def product_analytics(
    product: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(
        Purchase.product_name_raw,
        func.count(func.distinct(Purchase.company_id)).label("customer_count"),
        func.coalesce(func.sum(Purchase.quantity), 0).label("total_quantity"),
        func.coalesce(func.sum(Purchase.revenue), 0).label("total_revenue"),
    ).filter(Purchase.product_name_raw.isnot(None))

    if product:
        query = query.filter(Purchase.product_name_raw.ilike(f"%{product}%"))
    if date_from:
        query = query.filter(Purchase.purchase_date >= date_from)
    if date_to:
        query = query.filter(Purchase.purchase_date <= date_to)

    rows = (
        query.group_by(Purchase.product_name_raw)
        .order_by(func.sum(Purchase.revenue).desc())
        .all()
    )

    return [
        ProductAnalytics(
            product_name=row.product_name_raw or "Unknown",
            customer_count=row.customer_count,
            total_quantity=float(row.total_quantity),
            total_revenue=float(row.total_revenue),
        )
        for row in rows
    ]
