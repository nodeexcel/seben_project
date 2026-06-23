from __future__ import annotations
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Purchase
from app.schemas import CustomerAnalytics, ProductAnalytics
from app.utils.product_names import _catalog_terms_for_filter, normalize_product_label, product_matches_filter

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _purchase_query(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    product: str | None,
):
    query = db.query(Purchase).filter(Purchase.product_name_raw.isnot(None))
    if date_from:
        query = query.filter(Purchase.purchase_date >= date_from)
    if date_to:
        query = query.filter(Purchase.purchase_date <= date_to)
    if product:
        terms = _catalog_terms_for_filter(product)
        if terms:
            query = query.filter(
                or_(*[Purchase.product_name_raw.ilike(f"%{term}%") for term in terms])
            )
    return query


@router.get("/customers", response_model=list[CustomerAnalytics])
def customer_analytics(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    product: str | None = Query(None),
    db: Session = Depends(get_db),
):
    purchases = _purchase_query(db, date_from=date_from, date_to=date_to, product=product).all()
    company_names = {
        row.id: row.name
        for row in db.query(Company.id, Company.name)
        .filter(Company.id.in_({p.company_id for p in purchases}))
        .all()
    }
    buckets: dict[int, dict] = defaultdict(
        lambda: {"total_revenue": 0.0, "total_quantity": 0.0, "purchase_count": 0, "name": ""}
    )

    for purchase in purchases:
        if product and not product_matches_filter(purchase.product_name_raw, product):
            continue
        bucket = buckets[purchase.company_id]
        bucket["name"] = company_names.get(purchase.company_id, "Unknown")
        bucket["total_revenue"] += float(purchase.revenue or 0)
        bucket["total_quantity"] += float(purchase.quantity or 0)
        bucket["purchase_count"] += 1

    rows = sorted(
        buckets.items(),
        key=lambda item: (item[1]["total_revenue"], item[1]["total_quantity"]),
        reverse=True,
    )

    return [
        CustomerAnalytics(
            company_id=company_id,
            company_name=data["name"],
            total_revenue=data["total_revenue"],
            total_quantity=data["total_quantity"],
            purchase_count=data["purchase_count"],
        )
        for company_id, data in rows
        if data["purchase_count"] > 0
    ]


@router.get("/products", response_model=list[ProductAnalytics])
def product_analytics(
    product: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    purchases = _purchase_query(db, date_from=date_from, date_to=date_to, product=product).all()
    buckets: dict[str, dict] = defaultdict(
        lambda: {"customer_ids": set(), "total_revenue": 0.0, "total_quantity": 0.0}
    )

    for purchase in purchases:
        if product and not product_matches_filter(purchase.product_name_raw, product):
            continue
        label = normalize_product_label(purchase.product_name_raw)
        if not label:
            continue
        bucket = buckets[label]
        bucket["customer_ids"].add(purchase.company_id)
        bucket["total_revenue"] += float(purchase.revenue or 0)
        bucket["total_quantity"] += float(purchase.quantity or 0)

    rows = sorted(
        buckets.items(),
        key=lambda item: (item[1]["total_revenue"], item[1]["total_quantity"]),
        reverse=True,
    )

    return [
        ProductAnalytics(
            product_name=label,
            customer_count=len(data["customer_ids"]),
            total_quantity=data["total_quantity"],
            total_revenue=data["total_revenue"],
        )
        for label, data in rows
    ]
