from __future__ import annotations
import re
from pathlib import Path

import pdfplumber

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedPurchase, ParsedProductInterest
from app.services.product_detection import detect_form_in_text, detect_products_in_text, parse_euro_amount

DATE_PATTERN = re.compile(
    r"(?:date|data)\s*[:\s]*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.I,
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
EURO_LINE = re.compile(r"([\d.,]+)\s*€")
COMPANY_PATTERNS = [
    re.compile(r"(?:invoice address|name)\s*:\s*(.+)", re.I),
    re.compile(r"^name\s*:\s*(.+)$", re.I),
    re.compile(r"company name\s+(.+?)(?:\s+date|\s*$)", re.I),
    re.compile(r"^([A-Z][A-Z\s.&]+(?:S\.?P\.?A\.?|SRL|SPA|LTD|LLC|GMBH))\s*$"),
]


def parse_invoice(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="invoice")

    try:
        text_parts: list[str] = []
        with pdfplumber.open(filepath) as pdf:
            output.metadata["page_count"] = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        if not text_parts:
            output.errors.append(
                "No text extracted — PDF may be scanned/image-based (OCR not yet implemented)"
            )
            return output

        full_text = "\n".join(text_parts)
        output.raw_text = full_text[:8000]
        output.metadata["filename"] = Path(filepath).name
        output.metadata["char_count"] = len(full_text)

        output.company_name = _extract_buyer_company(full_text)
        output.contacts.extend(_extract_contacts(full_text))
        output.purchases.extend(_extract_line_items(full_text))
        output.product_interests.extend(_extract_product_interests(full_text))

        if not output.purchases:
            output.purchases.extend(_extract_summary_purchase(full_text))

        forms = detect_form_in_text(full_text)
        output.metadata["forms_detected"] = list(forms)

    except Exception as exc:
        output.errors.append(str(exc))

    return output


def _extract_buyer_company(text: str) -> str | None:
    for pattern in COMPANY_PATTERNS:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            if len(name) > 2 and "invoice" not in name.lower():
                return _clean_company_name(name)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skip = {"commercial invoice", "invoice", "description", "total", "bank", "producer"}
    for line in lines[:15]:
        lower = line.lower()
        if any(kw in lower for kw in skip):
            continue
        if re.search(r"(S\.?P\.?A\.?|SRL|SPA|LTD)", line, re.I):
            return _clean_company_name(line)
    return None


def _clean_company_name(name: str) -> str:
    name = re.sub(r"^(name|address)\s*:\s*", "", name, flags=re.I).strip()
    return name[:255]


def _extract_contacts(text: str) -> list[ParsedContact]:
    contacts: list[ParsedContact] = []
    for email_addr in set(EMAIL_PATTERN.findall(text)):
        contacts.append(ParsedContact(name=email_addr.split("@")[0], email=email_addr))
    for phone in set(PHONE_PATTERN.findall(text)[:5]):
        contacts.append(ParsedContact(name="Unknown", phone=phone.strip()))
    return contacts


def _extract_line_items(text: str) -> list[ParsedPurchase]:
    purchases: list[ParsedPurchase] = []
    date_match = DATE_PATTERN.search(text)
    purchase_date = date_match.group(1) if date_match else None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        upper = stripped.upper()
        if not any(kw in upper for kw in ("FROZEN", "FRESH", "KG", "BOX", "PRAWN", "TROUT", "URCHIN", "ATHERINA", "OMBRI", "ORATA", "BRANZ", "VONGOL")):
            continue
        if any(skip in upper for skip in ("TOTAL BOXES", "TOTAL PALLETS", "NET WEIGHT", "GROSS WEIGHT", "DESCRIPTION OF GOODS", "COMMERCIAL INVOICE")):
            continue

        euros = EURO_LINE.findall(stripped)
        revenue = parse_euro_amount(euros[-1]) if euros else None

        qty_match = re.search(r"(\d+(?:[.,]\d+)?)\s*KG", stripped, re.I)
        quantity = parse_euro_amount(qty_match.group(1)) if qty_match else None

        product_name = stripped
        for euro in euros:
            product_name = product_name.replace(f"{euro} €", "").replace(f"€ {euro}", "")
        product_name = re.sub(r"\s+", " ", product_name).strip()[:255]

        if product_name and (revenue or quantity):
            purchases.append(
                ParsedPurchase(
                    product_name=product_name,
                    quantity=quantity,
                    revenue=revenue,
                    currency="EUR",
                    purchase_date=purchase_date,
                )
            )

    return purchases


def _extract_summary_purchase(text: str) -> list[ParsedPurchase]:
    purchases: list[ParsedPurchase] = []
    date_match = DATE_PATTERN.search(text)
    purchase_date = date_match.group(1) if date_match else None

    total_match = re.search(
        r"total\s+[\d.,\s]+\s+([\d.,]+)\s*€",
        text,
        re.I,
    )
    net_weight = re.search(r"net weight\s*:\s*(\d+(?:[.,]\d+)?)\s*kg", text, re.I)

    if total_match:
        products = detect_products_in_text(text)
        purchases.append(
            ParsedPurchase(
                product_name=products[0].name if products else "Mixed products",
                quantity=parse_euro_amount(net_weight.group(1)) if net_weight else None,
                revenue=parse_euro_amount(total_match.group(1)),
                currency="EUR",
                purchase_date=purchase_date,
            )
        )
    return purchases


def _extract_product_interests(text: str) -> list[ParsedProductInterest]:
    interests: list[ParsedProductInterest] = []
    for detected in detect_products_in_text(text):
        interests.append(
            ParsedProductInterest(
                product_name=detected.name,
                form=detected.form,
                source="invoice",
            )
        )
    return interests
