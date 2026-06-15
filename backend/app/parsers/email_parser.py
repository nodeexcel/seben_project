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

COMPANY_SUBJECT_PATTERN = re.compile(r"^(.+?)\s*[-–]\s*(nuovo ordine|ordine|order|offerta)", re.I)


def parse_email(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="email")
    suffix = Path(filepath).suffix.lower()

    try:
        if suffix == ".eml":
            _parse_eml(filepath, output)
        elif suffix == ".mbox":
            _parse_mbox(filepath, output)
        else:
            output.errors.append(f"Unsupported email format: {suffix}. Use .eml or .mbox")
    except Exception as exc:
        output.errors.append(str(exc))

    _enrich_from_content(output, Path(filepath).stem)
    output.metadata["message_count"] = len(output.messages)
    return output


def _parse_eml(filepath: str, output: ExtractionOutput) -> None:
    with open(filepath, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    _extract_email_message(msg, output)


def _parse_mbox(filepath: str, output: ExtractionOutput) -> None:
    mbox = mailbox.mbox(filepath)
    for msg in mbox:
        _extract_email_message(msg, output)


def _extract_email_message(msg, output: ExtractionOutput) -> None:
    subject = msg.get("Subject", "") or ""
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
    full_content = f"{subject}\n\n{body}".strip()
    output.messages.append(
        ParsedMessage(sender=sender, content=full_content, timestamp=timestamp)
    )

    for raw_addr in (sender, to):
        contact = _parse_address(raw_addr)
        if not contact:
            continue
        output.contacts.append(contact)
        company = _company_from_contact(contact)
        if company and not output.company_name:
            output.company_name = company

    if not output.company_name:
        output.company_name = _company_from_subject(subject)


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


def _company_from_contact(contact: ParsedContact) -> str | None:
    if _is_internal_email(contact.email):
        return None
    if contact.email and "@" in contact.email:
        domain = contact.email.split("@")[1]
        generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "libero.it"}
        if domain.lower() not in generic:
            return domain.split(".")[0].replace("-", " ").title()
    if contact.name and contact.name not in ("Unknown",):
        return contact.name
    return None


def _company_from_subject(subject: str) -> str | None:
    match = COMPANY_SUBJECT_PATTERN.match(subject.strip())
    if match:
        return match.group(1).strip()
    if " - " in subject:
        left = subject.split(" - ")[0].strip()
        if len(left) > 2:
            return left
    return None


def _enrich_from_content(output: ExtractionOutput, filename: str) -> None:
    combined = "\n".join(m.content or "" for m in output.messages)
    if not output.company_name:
        output.company_name = _company_from_subject(filename.replace("_", " "))

    for detected in detect_products_in_text(combined):
        output.product_interests.append(
            ParsedProductInterest(
                product_name=detected.name,
                form=detected.form,
                source="email",
            )
        )

    output.metadata["products_detected"] = [p.product_name for p in output.product_interests]
