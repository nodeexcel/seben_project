from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Purchase
from app.schemas import CustomerAnalytics, InactiveClientAnalytics, ProductAnalytics
from app.utils.product_names import _catalog_terms_for_filter, normalize_product_label, product_matches_filter

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _purchase_query(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    product: str | None,
    company_id: int | None = None,
):
    query = db.query(Purchase).filter(Purchase.product_name_raw.isnot(None))
    if date_from:
        query = query.filter(Purchase.purchase_date >= date_from)
    if date_to:
        query = query.filter(Purchase.purchase_date <= date_to)
    if company_id is not None:
        query = query.filter(Purchase.company_id == company_id)
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
    company_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    purchases = _purchase_query(
        db,
        date_from=date_from,
        date_to=date_to,
        product=product,
        company_id=company_id,
    ).all()
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


@router.get("/inactive", response_model=list[InactiveClientAnalytics])
def inactive_clients(
    months: int = Query(6, ge=1, le=36),
    db: Session = Depends(get_db),
):
    cutoff = date.today() - timedelta(days=months * 30)
    purchases = (
        db.query(Purchase)
        .filter(Purchase.purchase_date.isnot(None), Purchase.product_name_raw.isnot(None))
        .all()
    )
    buckets: dict[int, dict] = defaultdict(
        lambda: {"last_date": None, "total_revenue": 0.0, "order_count": 0}
    )

    for purchase in purchases:
        bucket = buckets[purchase.company_id]
        bucket["total_revenue"] += float(purchase.revenue or 0)
        bucket["order_count"] += 1
        last_date = bucket["last_date"]
        if last_date is None or purchase.purchase_date > last_date:
            bucket["last_date"] = purchase.purchase_date

    inactive_ids = [
        company_id
        for company_id, data in buckets.items()
        if data["last_date"] is not None and data["last_date"] < cutoff
    ]
    if not inactive_ids:
        return []

    company_names = {
        row.id: row.name
        for row in db.query(Company.id, Company.name).filter(Company.id.in_(inactive_ids)).all()
    }
    today = date.today()
    rows = sorted(
        inactive_ids,
        key=lambda cid: buckets[cid]["last_date"] or date.min,
    )

    return [
        InactiveClientAnalytics(
            company_id=company_id,
            company_name=company_names.get(company_id, "Unknown"),
            last_purchase_date=buckets[company_id]["last_date"],
            days_since_last_order=(today - buckets[company_id]["last_date"]).days
            if buckets[company_id]["last_date"]
            else None,
            total_historical_revenue=buckets[company_id]["total_revenue"],
            total_historical_orders=buckets[company_id]["order_count"],
        )
        for company_id in rows
    ]
