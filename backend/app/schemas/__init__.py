from __future__ import annotations
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import DocumentSourceType, InteractionType, ProductCategory


# --- Shared ---

class MessageResponse(BaseModel):
    message: str


# --- Company ---

class CompanyBase(BaseModel):
    name: str
    country: str | None = None
    product_category: ProductCategory = ProductCategory.UNKNOWN
    notes: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    product_category: ProductCategory | None = None
    notes: str | None = None
    ai_summary: str | None = None


class ContactBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
    phone: str | None = None


class PurchaseBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name_raw: str | None = None
    quantity: float | None = None
    revenue: float | None = None
    currency: str | None = None
    purchase_date: date | None = None
    supplier_name: str | None = None


class ProductInterestBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name_raw: str | None = None
    source: str | None = None


class CompanyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str | None = None
    product_category: ProductCategory
    first_interaction_date: date | None = None
    last_interaction_date: date | None = None
    contact_count: int = 0
    total_revenue: float = 0.0
    total_quantity: float = 0.0


class CompanyDetail(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_interaction_date: date | None = None
    last_interaction_date: date | None = None
    ai_summary: str | None = None
    contacts: list[ContactBrief] = []
    purchases: list[PurchaseBrief] = []
    purchase_count: int = 0
    product_interests: list[ProductInterestBrief] = []
    created_at: datetime
    updated_at: datetime


class MergeCandidate(BaseModel):
    id: int
    name: str
    score: float
    contact_count: int = 0
    purchase_count: int = 0


class CompanyMergeRequest(BaseModel):
    duplicate_company_id: int


# --- Contact ---

class ContactCreate(BaseModel):
    company_id: int | None = None
    name: str
    email: str | None = None
    phone: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None
    name: str
    email: str | None
    phone: str | None


# --- Purchase ---

class PurchaseCreate(BaseModel):
    company_id: int
    product_name_raw: str | None = None
    quantity: float | None = None
    revenue: float | None = None
    currency: str = "USD"
    purchase_date: date | None = None


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    product_name_raw: str | None
    quantity: float | None
    revenue: float | None
    currency: str | None
    purchase_date: date | None


# --- Search ---

class SearchParams(BaseModel):
    q: str | None = None
    product: str | None = None
    country: str | None = None
    category: ProductCategory | None = None
    date_from: date | None = None
    date_to: date | None = None


# --- Analytics ---

class CustomerAnalytics(BaseModel):
    company_id: int
    company_name: str
    total_revenue: float
    total_quantity: float
    purchase_count: int


class ProductAnalytics(BaseModel):
    product_name: str
    customer_count: int
    total_quantity: float
    total_revenue: float


class InactiveClientAnalytics(BaseModel):
    company_id: int
    company_name: str
    last_purchase_date: date | None = None
    days_since_last_order: int | None = None
    total_historical_revenue: float
    total_historical_orders: int


# --- Upload / Extraction ---

class ExtractionResult(BaseModel):
    source_type: DocumentSourceType
    filename: str
    status: str
    extracted: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    document_id: int
    filename: str
    source_type: DocumentSourceType
    status: str
    extraction: ExtractionResult | None = None


class InteractionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interaction_type: InteractionType
    subject: str | None
    content: str | None
    interaction_date: datetime | None
    sender: str | None
