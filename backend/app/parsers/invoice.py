from __future__ import annotations
import re
from pathlib import Path

import pdfplumber

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedPurchase

DATE_PATTERN = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})"
)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
AMOUNT_PATTERN = re.compile(r"(?:total|amount|sum|due)[:\s]*[\$€£]?\s*([\d,]+\.?\d*)", re.I)
QTY_PATTERN = re.compile(r"(?:qty|quantity)[:\s]*([\d,]+\.?\d*)", re.I)


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
        output.raw_text = full_text[:5000]
        output.metadata["filename"] = Path(filepath).name

        output.company_name = _guess_company_name(full_text)
        output.contacts.extend(_extract_contacts(full_text))
        output.purchases.extend(_extract_purchases(full_text))
        output.metadata["char_count"] = len(full_text)

    except Exception as exc:
        output.errors.append(str(exc))

    return output


def _guess_company_name(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skip_keywords = {"invoice", "bill", "receipt", "tax", "date", "total", "amount"}
    for line in lines[:10]:
        lower = line.lower()
        if len(line) > 3 and not any(kw in lower for kw in skip_keywords):
            if not EMAIL_PATTERN.search(line) and not DATE_PATTERN.match(line):
                return line
    return None


def _extract_contacts(text: str) -> list[ParsedContact]:
    contacts: list[ParsedContact] = []
    emails = EMAIL_PATTERN.findall(text)
    phones = PHONE_PATTERN.findall(text)
    for email_addr in set(emails):
        contacts.append(ParsedContact(name=email_addr.split("@")[0], email=email_addr))
    for phone in set(phones[:3]):
        contacts.append(ParsedContact(name="Unknown", phone=phone.strip()))
    return contacts


def _extract_purchases(text: str) -> list[ParsedPurchase]:
    purchases: list[ParsedPurchase] = []

    date_match = DATE_PATTERN.search(text)
    purchase_date = date_match.group(1) if date_match else None

    amount_match = AMOUNT_PATTERN.search(text)
    revenue = _parse_number(amount_match.group(1)) if amount_match else None

    qty_match = QTY_PATTERN.search(text)
    quantity = _parse_number(qty_match.group(1)) if qty_match else None

    product_name = _guess_product_from_lines(text)

    if revenue or quantity or product_name:
        purchases.append(
            ParsedPurchase(
                product_name=product_name,
                quantity=quantity,
                revenue=revenue,
                currency="USD",
                purchase_date=purchase_date,
            )
        )

    return purchases


def _guess_product_from_lines(text: str) -> str | None:
    lines = text.splitlines()
    skip = {"invoice", "total", "subtotal", "tax", "amount", "date", "bill to", "ship to"}
    for line in lines:
        cleaned = line.strip()
        if len(cleaned) > 3 and not any(kw in cleaned.lower() for kw in skip):
            if not DATE_PATTERN.match(cleaned) and not AMOUNT_PATTERN.match(cleaned):
                if re.search(r"[a-zA-Z]{3,}", cleaned):
                    return cleaned[:255]
    return None


def _parse_number(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None
