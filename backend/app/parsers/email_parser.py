from __future__ import annotations
import email
import mailbox
import re
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedMessage, ParsedProductInterest
from app.services.product_detection import detect_products_in_text

INTERNAL_DOMAINS = {
    "happytablefoods.com",
    "sulablu.com",
    "zihni.com",
}

SUBJECT_COMPANY_PATTERNS = [
    re.compile(r"^(.+?)\s*[-–]\s*(nuovo ordine|ordine|order|offerta)", re.I),
    re.compile(r"^ORDINE\s+(.+?)\s+PER\b", re.I),
]

REPLY_PREFIX = re.compile(r"^(?:(?:re|fw|fwd|r|aw|antwort)\s*:\s*)+", re.I)

KNOWN_BRAND_TOKENS = [
    (re.compile(r"\bAVRAMAR\b", re.I), "AVRAMAR"),
    (re.compile(r"\bNETTUNO\b", re.I), "NETTUNO"),
    (re.compile(r"\bBLU\s+MARES\s+GOURMET\b", re.I), "BLU MARES GOURMET"),
    (re.compile(r"\bGEL\s+GROUP\b", re.I), "GEL GROUP"),
    (re.compile(r"\bZIHNI\b", re.I), "Zihni"),
]

GENERIC_COMPANY_LABELS = {
    "nuovo ordine",
    "ordine",
    "stock",
    "offerta",
    "documenti",
}

GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "esselunga.it",
}

DOMAIN_COMPANY_HINTS = {
    "neptun.it": "NETTUNO",
    "marr.it": "Marr",
    "bofrost.it": "Bofrost",
    "conservieraadriatica.it": "Conserviera Adriatica",
    "gruppodac.eu": "Gruppodac",
    "panapesca.it": "Panapesca",
    "alicesurgelati.it": "Alicesurgelati",
    "newfoodsrl.com": "Newfoodsrl",
    "gelpiave.it": "Gelpiave",
}


def parse_email(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="email")
    suffix = Path(filepath).suffix.lower()
    filename_stem = Path(filepath).stem

    try:
        if suffix == ".eml":
            _parse_eml(filepath, output, filename_stem)
        elif suffix == ".mbox":
            _parse_mbox(filepath, output)
        else:
            output.errors.append(f"Unsupported email format: {suffix}. Use .eml or .mbox")
    except Exception as exc:
        output.errors.append(str(exc))

    _enrich_from_content(output, filename_stem)
    output.metadata["message_count"] = len(output.messages)
    return output


def _parse_eml(filepath: str, output: ExtractionOutput, filename_stem: str) -> None:
    with open(filepath, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    _extract_email_message(msg, output, filename_stem)


def _parse_mbox(filepath: str, output: ExtractionOutput) -> None:
    mbox = mailbox.mbox(filepath)
    for msg in mbox:
        _extract_email_message(msg, output, Path(filepath).stem)


def _extract_email_message(msg, output: ExtractionOutput, filename_stem: str) -> None:
    subject = (msg.get("Subject", "") or "").strip()
    sender = msg.get("From", "")
    to = msg.get("To", "")
    date_str = msg.get("Date", "")

    timestamp = None
    if date_str:
        try:
            timestamp = parsedate_to_datetime(date_str).isoformat()
        except Exception:
            timestamp = date_str

    body = _get_email_body(msg)
    output.messages.append(
        ParsedMessage(
            sender=sender,
            subject=subject or None,
            content=body.strip() or subject,
            timestamp=timestamp,
        )
    )

    contacts: list[ParsedContact] = []
    for raw_addrs in (sender, to):
        contacts.extend(_parse_addresses(raw_addrs))
    for contact in contacts:
        if _is_internal_email(contact.email):
            continue
        output.contacts.append(contact)

    company = _resolve_email_company(subject, filename_stem, contacts)
    if company:
        output.company_name = company


def _get_email_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return str(msg.get_payload())


def _parse_addresses(raw: str) -> list[ParsedContact]:
    if not raw:
        return []
    contacts: list[ParsedContact] = []
    for part in re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", raw):
        contact = _parse_address(part.strip())
        if contact:
            contacts.append(contact)
    return contacts


def _parse_address(raw: str) -> ParsedContact | None:
    if not raw:
        return None
    name = raw
    email_addr = None
    if "<" in raw and ">" in raw:
        name = raw.split("<")[0].strip().strip('"')
        email_addr = raw.split("<")[1].split(">")[0].strip()
    elif "@" in raw:
        email_addr = raw.strip()
        name = email_addr.split("@")[0]
    if name or email_addr:
        return ParsedContact(name=name or email_addr or "Unknown", email=email_addr)
    return None


def _is_internal_email(email_addr: str | None) -> bool:
    if not email_addr or "@" not in email_addr:
        return False
    domain = email_addr.split("@")[1].lower()
    return any(domain == d or domain.endswith("." + d) for d in INTERNAL_DOMAINS)


def _strip_reply_prefix(subject: str) -> str:
    cleaned = subject.strip()
    while True:
        match = REPLY_PREFIX.match(cleaned)
        if not match:
            break
        cleaned = cleaned[match.end() :].strip()
    return cleaned


def _clean_company_label(name: str) -> str:
    cleaned = name.strip().strip("-– ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:255]


def _is_generic_company_label(name: str) -> bool:
    low = _clean_company_label(name).lower()
    if low in GENERIC_COMPANY_LABELS:
        return True
    return low.startswith(("r:", "re:", "fw:", "fwd:"))


def _company_from_known_tokens(text: str) -> str | None:
    for pattern, label in KNOWN_BRAND_TOKENS:
        if pattern.search(text):
            return label
    return None


def _company_from_subject(subject: str) -> str | None:
    subject = _strip_reply_prefix(subject.strip())
    if not subject:
        return None
    for pattern in SUBJECT_COMPANY_PATTERNS:
        match = pattern.match(subject)
        if match:
            candidate = _clean_company_label(match.group(1))
            if len(candidate) > 2 and not _is_generic_company_label(candidate):
                return candidate
    return _company_from_known_tokens(subject)


def _company_from_filename(stem: str) -> str | None:
    cleaned = stem.replace("_", " ").strip()
    return _company_from_subject(cleaned) or _company_from_known_tokens(cleaned)


def _company_from_domain(email_addr: str) -> str | None:
    if _is_internal_email(email_addr):
        return None
    domain = email_addr.split("@")[1].lower()
    if domain in DOMAIN_COMPANY_HINTS:
        return DOMAIN_COMPANY_HINTS[domain]
    if domain in GENERIC_EMAIL_DOMAINS:
        return None
    base = domain.split(".")[0]
    if base in {"comunicazioni", "info", "sales", "orders", "order"}:
        return None
    return base.replace("-", " ").title()


def _company_from_external_contacts(contacts: list[ParsedContact]) -> str | None:
    for contact in contacts:
        if contact.email and not _is_internal_email(contact.email):
            domain_company = _company_from_domain(contact.email)
            if domain_company:
                return domain_company
    for contact in contacts:
        name_company = _company_from_contact(contact)
        if name_company:
            return name_company
    return None


def _company_from_contact(contact: ParsedContact) -> str | None:
    if _is_internal_email(contact.email):
        return None
    if contact.name and contact.name.lower() not in {"unknown", "info", "sales", "order"}:
        return contact.name.strip()
    return None


def _resolve_email_company(
    subject: str,
    filename_stem: str,
    contacts: list[ParsedContact],
) -> str | None:
    stripped = _strip_reply_prefix(subject)
    company = (
        _company_from_known_tokens(stripped)
        or _company_from_known_tokens(filename_stem)
        or _company_from_subject(subject)
    )
    if company and _is_generic_company_label(company):
        company = None
    if not company:
        company = _company_from_external_contacts(contacts)
    return company


def _enrich_from_content(output: ExtractionOutput, filename: str) -> None:
    combined = "\n".join(
        f"{m.subject or ''}\n{m.content or ''}" for m in output.messages
    )
    if not output.company_name:
        output.company_name = _company_from_filename(filename.replace("_", " "))

    seen: set[str] = set()
    for detected in detect_products_in_text(combined):
        key = detected.name.lower()
        if key in seen:
            continue
        seen.add(key)
        output.product_interests.append(
            ParsedProductInterest(
                product_name=detected.name,
                form=detected.form,
                source="email",
            )
        )

    output.metadata["products_detected"] = [p.product_name for p in output.product_interests]
