from __future__ import annotations
import email
import mailbox
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedMessage, _read_text_file


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
    subject = msg.get("Subject", "")
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
        ParsedMessage(sender=sender, content=f"{subject}\n\n{body}".strip(), timestamp=timestamp)
    )

    sender_contact = _parse_address(sender)
    if sender_contact:
        output.contacts.append(sender_contact)
        if not output.company_name:
            output.company_name = _guess_company_from_email(sender_contact.email)

    recipient_contact = _parse_address(to)
    if recipient_contact:
        output.contacts.append(recipient_contact)


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


def _guess_company_from_email(email_addr: str | None) -> str | None:
    if not email_addr or "@" not in email_addr:
        return None
    domain = email_addr.split("@")[1]
    generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
    if domain.lower() in generic:
        return None
    return domain.split(".")[0].replace("-", " ").title()
