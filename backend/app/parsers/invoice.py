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
EURO_LINE = re.compile(r"([\d.,]+)\s*€")
HS_CODE_PATTERN = re.compile(r"\b\d{8,10}\b")
BARCODE_PATTERN = re.compile(r"/\s*\d{10,}.*$")
TUMay_INV_PATTERN = re.compile(r"^INV[_\s]?\d*\s+(.+?)\.pdf$", re.I)
TUMay_PKL_PATTERN = re.compile(r"^PKL[_\s]?\d*\s+(.+?)\.pdf$", re.I)
ZIHNI_INV_PATTERN = re.compile(r"\d+\s+(.+?)\s+INVOICE", re.I)
MUTLU_INV_PATTERN = re.compile(r"^(MUT20\d+)\.pdf$", re.I)
COMPANY_PATTERNS = [
    re.compile(r"(?:invoice address|bill\s*to|sold\s*to|customer)\s*:\s*(.+)", re.I),
    re.compile(r"^name\s*:\s*(.+)$", re.I),
    re.compile(r"company name\s+(.+?)(?:\s+date|\s*$)", re.I),
    re.compile(r"^([A-Z][A-Z\s.&'-]+(?:S\.?P\.?A\.?|SRL|SPA|LTD|LLC|GMBH|S\.?L\.?U\.?))\s*$"),
]
SPANISH_INVOICE_BUYER_PATTERNS = [
    re.compile(r"FACTURA\s+VENTA\s*\n\s*([^\n]+)", re.I),
    re.compile(r"Envio a[-\s]*(?:Direccion)?\s*\n\s*([^\n]+)", re.I),
]
COMPANY_SUFFIX_RE = re.compile(
    r"\b(S\.?P\.?A\.?|S\.?R\.?L\.?|S\.?L\.?U\.?|SNC|SAS|LTD|LLC|GMBH|AG|NV|BV|SCR?L)\b",
    re.I,
)
INVALID_COMPANY_SUBSTRINGS = (
    "zona de produccion",
    "pais de origen",
    "metodo de produccion",
    "registro sanitario",
    "products we work with",
    "#sayi/",
    "description of goods",
    "commercial invoice",
    "net weight",
    "gross weight",
)
COMPANY_SUFFIX_WORDS = {
    "snc", "sas", "srl", "spa", "slu", "ltd", "llc", "gmbh", "ag", "nv", "bv", "scrl", "scr",
}
SUPPORTING_DOC_KEYWORDS = (
    "PKL_",
    "PACKING LIST",
    "PACKING L",
    "CMR",
    "T1",
    "BEYANNAME",
    "BEYANI",
    "AVCILIK",
    "CHEDP",
    "GDB",
    "SAĞLIK",
    "SAGLIK",
    "VGB",
    "IL TARIM",
    "İL TARIM",
    "ANNEX",
    "CREDIT NOTE",
    "TRANSİT",
    "TRANSIT",
    "SERTİFİK",
    "SERTIFIK",
)


def classify_invoice_document(filename: str) -> str:
    """Return 'invoice' for commercial invoices, 'supporting' for logistics/customs docs."""
    upper = filename.upper()
    if MUTLU_INV_PATTERN.match(filename):
        return "invoice"
    if TUMay_INV_PATTERN.match(filename) or ZIHNI_INV_PATTERN.search(upper):
        return "invoice"
    if " INVOICE" in upper and "PACKING" not in upper:
        return "invoice"
    if any(keyword in upper for keyword in SUPPORTING_DOC_KEYWORDS):
        return "supporting"
    if TUMay_PKL_PATTERN.match(filename):
        return "supporting"
    return "invoice"


def parse_invoice(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="invoice")
    filename = Path(filepath).name
    doc_role = classify_invoice_document(filename)
    output.metadata["document_role"] = doc_role
    output.metadata["filename"] = filename

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
                "No text extracted — PDF may be scanned/image-based (request a text-based PDF from the producer)"
            )
            return output

        full_text = "\n".join(text_parts)
        output.raw_text = full_text[:8000]
        output.metadata["char_count"] = len(full_text)

        if doc_role == "supporting":
            output.company_name = _extract_company_from_filename(filename)
            if output.company_name and not is_plausible_company_name(
                output.company_name, allow_short=True
            ):
                output.company_name = None
        else:
            output.company_name = _extract_buyer_company(full_text, filename)

        if doc_role == "invoice":
            output.contacts.extend(_extract_contacts(full_text))
            output.purchases.extend(_extract_line_items(full_text))
            output.product_interests.extend(_extract_product_interests(full_text))
            if not output.purchases:
                output.purchases.extend(_extract_summary_purchase(full_text))
        else:
            output.metadata["skipped"] = "supporting_document"

        forms = detect_form_in_text(full_text)
        output.metadata["forms_detected"] = list(forms)

    except Exception as exc:
        output.errors.append(str(exc))

    return output


def _extract_company_from_filename(filename: str) -> str | None:
    for pattern in (TUMay_INV_PATTERN, TUMay_PKL_PATTERN):
        match = pattern.match(filename)
        if match:
            return _clean_company_name(match.group(1))
    match = ZIHNI_INV_PATTERN.search(filename)
    if match:
        return _clean_company_name(match.group(1))
    match = MUTLU_INV_PATTERN.match(filename)
    if match:
        return "Mutlu Sofralar"
    return None


def _extract_buyer_company(text: str, filename: str) -> str | None:
    from_filename = _extract_company_from_filename(filename)
    if from_filename and is_plausible_company_name(from_filename, allow_short=True):
        return from_filename

    for pattern in SPANISH_INVOICE_BUYER_PATTERNS:
        match = pattern.search(text)
        if match:
            name = _clean_company_name(match.group(1))
            if is_plausible_company_name(name):
                return name

    for pattern in COMPANY_PATTERNS:
        match = pattern.search(text)
        if match:
            name = _clean_company_name(match.group(1).strip())
            if is_plausible_company_name(name):
                return name

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:30]:
        if not COMPANY_SUFFIX_RE.search(line):
            continue
        name = _clean_company_name(line)
        if is_plausible_company_name(name):
            return name

    return None


def is_plausible_company_name(name: str, *, allow_short: bool = False) -> bool:
    """Reject invoice metadata, species names, and product labels mistaken for companies."""
    cleaned = name.strip()
    if len(cleaned) < 3:
        return False

    lower = cleaned.lower()
    if any(sub in lower for sub in INVALID_COMPANY_SUBSTRINGS):
        return False
    if "|" in cleaned or "#" in cleaned:
        return False
    if _looks_like_scientific_name(cleaned):
        return False

    if COMPANY_SUFFIX_RE.search(cleaned):
        return True
    if allow_short:
        words = [word for word in cleaned.split() if word]
        if len(words) >= 2 and all(word[0].isupper() for word in words):
            return True
        if len(words) == 1 and len(cleaned) >= 4 and cleaned[0].isupper():
            return True
    if len(cleaned.split()) >= 3:
        return True
    return False


def _looks_like_scientific_name(name: str) -> bool:
    parts = name.strip().split()
    if len(parts) != 2:
        return False
    genus, species = parts
    if species.lower() in COMPANY_SUFFIX_WORDS:
        return False
    return (
        genus[0].isupper()
        and genus[1:].islower()
        and species.islower()
        and species.isalpha()
    )


def _clean_company_name(name: str) -> str:
    name = re.sub(r"^(name|address)\s*:\s*", "", name, flags=re.I).strip()
    name = re.sub(r"\s*\.pdf$", "", name, flags=re.I)
    return name[:255]


def _extract_contacts(text: str) -> list[ParsedContact]:
    contacts: list[ParsedContact] = []
    for email_addr in set(EMAIL_PATTERN.findall(text)):
        local = email_addr.split("@")[0]
        if local and local.lower() not in {"info", "admin", "noreply"}:
            contacts.append(ParsedContact(name=local, email=email_addr))
    return contacts


def _clean_product_name(raw: str) -> str:
    name = BARCODE_PATTERN.sub("", raw)
    name = HS_CODE_PATTERN.sub("", name)
    name = re.sub(r"^\d+\s+", "", name)
    name = re.sub(
        r"\s+\d{1,4}(?:[.,]\d+)?(?:\s+\d{1,4}(?:[.,]\d+)?){1,3}\s*(?:KG|K)?\s*$",
        "",
        name,
        flags=re.I,
    )
    name = re.sub(r"\s+", " ", name).strip(" -/")
    return name[:255]


def _extract_line_items(text: str) -> list[ParsedPurchase]:
    purchases: list[ParsedPurchase] = []
    date_match = DATE_PATTERN.search(text)
    purchase_date = date_match.group(1) if date_match else None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        upper = stripped.upper()
        if not any(
            kw in upper
            for kw in (
                "FROZEN",
                "FRESH",
                "KG",
                "BOX",
                "PRAWN",
                "TROUT",
                "URCHIN",
                "ATHERINA",
                "OMBRI",
                "ORATA",
                "BRANZ",
                "VONGOL",
                "SEABASS",
                "SEABREAM",
                "MACKEREL",
                "CUTTLEFISH",
                "SHRIMP",
                "SALMON",
                "BASS",
                "BREAM",
            )
        ):
            continue
        if any(
            skip in upper
            for skip in (
                "TOTAL BOXES",
                "TOTAL PALLETS",
                "NET WEIGHT",
                "GROSS WEIGHT",
                "DESCRIPTION OF GOODS",
                "COMMERCIAL INVOICE",
                "SUBTOTAL",
                "GRAND TOTAL",
            )
        ):
            continue

        euros = EURO_LINE.findall(stripped)
        revenue = parse_euro_amount(euros[-1]) if euros else None

        qty_match = re.search(r"(\d+(?:[.,]\d+)?)\s*KG", stripped, re.I)
        quantity = parse_euro_amount(qty_match.group(1)) if qty_match else None

        product_name = stripped
        for euro in euros:
            product_name = product_name.replace(f"{euro} €", "").replace(f"€ {euro}", "")
        product_name = _clean_product_name(product_name)

        if len(product_name) < 4:
            continue
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
