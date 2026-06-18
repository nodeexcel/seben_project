from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedContact:
    name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    phones: list[str] = field(default_factory=list)


@dataclass
class ParsedPurchase:
    product_name: str | None = None
    quantity: float | None = None
    revenue: float | None = None
    currency: str | None = None
    purchase_date: str | None = None


@dataclass
class ParsedMessage:
    sender: str | None = None
    content: str | None = None
    timestamp: str | None = None
    subject: str | None = None


@dataclass
class ParsedProductInterest:
    product_name: str
    form: str | None = None
    source: str | None = None


@dataclass
class ExtractionOutput:
    source_type: str
    contacts: list[ParsedContact] = field(default_factory=list)
    purchases: list[ParsedPurchase] = field(default_factory=list)
    messages: list[ParsedMessage] = field(default_factory=list)
    product_interests: list[ParsedProductInterest] = field(default_factory=list)
    company_name: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "company_name": self.company_name,
            "contacts": [
                {"name": c.name, "email": c.email, "phone": c.phone, "company_name": c.company_name}
                for c in self.contacts
            ],
            "purchases": [
                {
                    "product_name": p.product_name,
                    "quantity": p.quantity,
                    "revenue": p.revenue,
                    "currency": p.currency,
                    "purchase_date": p.purchase_date,
                }
                for p in self.purchases
            ],
            "messages": [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "subject": m.subject,
                }
                for m in self.messages
            ],
            "product_interests": [
                {
                    "product_name": p.product_name,
                    "form": p.form,
                    "source": p.source,
                }
                for p in self.product_interests
            ],
            "metadata": self.metadata,
            "errors": self.errors,
        }


def _read_text_file(filepath: str) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(filepath, encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode file: {filepath}")
