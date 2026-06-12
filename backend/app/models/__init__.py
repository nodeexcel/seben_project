import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductCategory(str, enum.Enum):
    FRESH = "Fresh"
    FROZEN = "Frozen"
    UNKNOWN = "Unknown"


class DocumentSourceType(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    CONTACT = "contact"
    INVOICE = "invoice"
    MANUAL = "manual"


class InteractionType(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    MANUAL = "manual"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    product_category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory), default=ProductCategory.UNKNOWN
    )
    first_interaction_date: Mapped[Optional[date]] = mapped_column(Date)
    last_interaction_date: Mapped[Optional[date]] = mapped_column(Date)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    contacts: Mapped[List["Contact"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    interactions: Mapped[List["Interaction"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    product_interests: Mapped[List["ProductInterest"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped[Optional["Company"]] = relationship(back_populates="contacts")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory), default=ProductCategory.UNKNOWN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    purchases: Mapped[List["Purchase"]] = relationship(back_populates="product")
    interests: Mapped[List["ProductInterest"]] = relationship(back_populates="product")


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), index=True)
    product_name_raw: Mapped[Optional[str]] = mapped_column(String(255))
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    revenue: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(10), default="USD")
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="purchases")
    product: Mapped[Optional["Product"]] = relationship(back_populates="purchases")
    document: Mapped[Optional["Document"]] = relationship(back_populates="purchases")


class ProductInterest(Base):
    __tablename__ = "product_interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), index=True)
    product_name_raw: Mapped[Optional[str]] = mapped_column(String(255))
    source: Mapped[Optional[str]] = mapped_column(String(50))
    mentioned_at: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="product_interests")
    product: Mapped[Optional["Product"]] = relationship(back_populates="interests")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), index=True)
    interaction_type: Mapped[InteractionType] = mapped_column(Enum(InteractionType), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(500))
    content: Mapped[Optional[str]] = mapped_column(Text)
    interaction_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    sender: Mapped[Optional[str]] = mapped_column(String(255))
    recipient: Mapped[Optional[str]] = mapped_column(String(255))
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    company: Mapped[Optional["Company"]] = relationship(back_populates="interactions")
    document: Mapped[Optional["Document"]] = relationship(back_populates="interactions")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_type: Mapped[DocumentSourceType] = mapped_column(Enum(DocumentSourceType), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    extracted_data: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    purchases: Mapped[List["Purchase"]] = relationship(back_populates="document")
    interactions: Mapped[List["Interaction"]] = relationship(back_populates="document")
