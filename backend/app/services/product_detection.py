from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.products import FRESH_KEYWORDS, FROZEN_KEYWORDS, PRODUCT_CATALOG


@dataclass
class DetectedProduct:
    name: str
    form: str  # fresh, frozen, unknown
    matched_term: str


def detect_products_in_text(text: str) -> list[DetectedProduct]:
    if not text:
        return []

    lower = text.lower()
    found: list[DetectedProduct] = []
    seen: set[str] = set()

    for product in PRODUCT_CATALOG:
        terms = (product.name_it,) + product.aliases
        for term in sorted(terms, key=len, reverse=True):
            if term.lower() in lower and product.name_it not in seen:
                form = _detect_form_near_term(lower, term.lower(), product.default_form)
                found.append(DetectedProduct(name=product.name_it, form=form, matched_term=term))
                seen.add(product.name_it)
                break

    return found


def detect_form_in_text(text: str) -> set[str]:
    if not text:
        return set()
    lower = text.lower()
    forms: set[str] = set()
    if any(kw in lower for kw in FROZEN_KEYWORDS):
        forms.add("frozen")
    if any(kw in lower for kw in FRESH_KEYWORDS):
        forms.add("fresh")
    return forms


def classify_company_form(signals: set[str]) -> str:
    if "fresh" in signals and "frozen" in signals:
        return "Both"
    if "frozen" in signals:
        return "Frozen"
    if "fresh" in signals:
        return "Fresh"
    return "Unknown"


def _detect_form_near_term(text: str, term: str, default: str) -> str:
    idx = text.find(term)
    if idx == -1:
        return default
    window = text[max(0, idx - 40) : idx + len(term) + 40]
    if any(kw in window for kw in FROZEN_KEYWORDS):
        return "frozen"
    if any(kw in window for kw in FRESH_KEYWORDS):
        return "fresh"
    if any(kw in text for kw in FROZEN_KEYWORDS):
        return "frozen"
    if any(kw in text for kw in FRESH_KEYWORDS):
        return "fresh"
    return default


def parse_euro_amount(value: str) -> float | None:
    cleaned = value.strip().replace("€", "").replace(" ", "")
    # European format: 18.392,50 or 18392.50
    if re.search(r"\d+\.\d{3},\d{2}$", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None
