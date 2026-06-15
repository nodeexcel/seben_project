from __future__ import annotations
import csv
from pathlib import Path

import vobject

from app.parsers.base import ExtractionOutput, ParsedContact, _read_text_file


def parse_contacts(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="contact")
    suffix = Path(filepath).suffix.lower()

    try:
        if suffix == ".vcf":
            _parse_vcf(filepath, output)
        elif suffix in (".csv", ".tsv"):
            _parse_csv(filepath, output, delimiter="," if suffix == ".csv" else "\t")
        else:
            output.errors.append(f"Unsupported contact format: {suffix}. Use .vcf or .csv")
    except Exception as exc:
        output.errors.append(str(exc))

    output.metadata["contact_count"] = len(output.contacts)
    return output


def _parse_vcf(filepath: str, output: ExtractionOutput) -> None:
    text = _read_text_file(filepath)
    for card in vobject.readComponents(text):
        if card.name != "VCARD":
            continue
        name = _get_vcard_name(card)
        email = _get_vcard_email(card)
        phones = _get_vcard_phones(card)
        org = _get_vcard_org(card)
        if name:
            output.contacts.append(
                ParsedContact(
                    name=name,
                    email=email,
                    phone=phones[0] if phones else None,
                    company_name=org,
                    phones=phones,
                )
            )
            if org and not output.company_name:
                output.company_name = org


def _get_vcard_name(card) -> str | None:
    if hasattr(card, "fn"):
        return str(card.fn.value)
    if hasattr(card, "n"):
        parts = card.n.value
        return " ".join(filter(None, [parts.given, parts.family])).strip() or None
    return None


def _get_vcard_email(card) -> str | None:
    if hasattr(card, "email"):
        emails = card.contents.get("email", [])
        return str(emails[0].value) if emails else None
    return None


def _get_vcard_phones(card) -> list[str]:
    if not hasattr(card, "tel"):
        return []

    preferred: list[str] = []
    other: list[str] = []
    for entry in card.contents.get("tel", []):
        value = str(entry.value).strip()
        if not value:
            continue
        params = getattr(entry, "params", {}) or {}
        types = [str(t).lower() for t in params.get("TYPE", [])]
        if "pref" in types:
            preferred.append(value)
        else:
            other.append(value)

    seen: set[str] = set()
    ordered: list[str] = []
    for phone in preferred + other:
        if phone not in seen:
            seen.add(phone)
            ordered.append(phone)
    return ordered


def _get_vcard_phone(card) -> str | None:
    phones = _get_vcard_phones(card)
    return phones[0] if phones else None


def _get_vcard_org(card) -> str | None:
    if hasattr(card, "org"):
        org = card.org.value
        if isinstance(org, list):
            return org[0] if org else None
        return str(org)
    return None


def _parse_csv(filepath: str, output: ExtractionOutput, delimiter: str = ",") -> None:
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            output.errors.append("CSV has no headers")
            return

        fields = {h.lower().strip(): h for h in reader.fieldnames}
        name_col = _find_column(fields, ["name", "full name", "display name", "contact name"])
        email_col = _find_column(fields, ["email", "e-mail", "email address"])
        phone_col = _find_column(fields, ["phone", "mobile", "telephone", "phone number"])
        company_col = _find_column(fields, ["company", "organization", "org"])

        if not name_col:
            output.errors.append("Could not find a name column in CSV")
            return

        for row in reader:
            name = row.get(name_col, "").strip()
            if not name:
                continue
            email = row.get(email_col, "").strip() if email_col else None
            phone = row.get(phone_col, "").strip() if phone_col else None
            company = row.get(company_col, "").strip() if company_col else None
            output.contacts.append(
                ParsedContact(name=name, email=email or None, phone=phone or None, company_name=company)
            )
            if company and not output.company_name:
                output.company_name = company


def _find_column(fields: dict[str, str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in fields:
            return fields[candidate]
    return None
