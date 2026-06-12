from __future__ import annotations
import re

import phonenumbers
from phonenumbers import NumberParseException


def normalize_phone(phone: str | None, default_region: str = "US") -> str | None:
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if not cleaned:
        return None
    try:
        parsed = phonenumbers.parse(cleaned, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        pass
    return cleaned


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    return email.strip().lower()


def normalize_company_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = name.strip().lower()
    suffixes = [" ltd", " llc", " inc", " corp", " co", " gmbh", " sa", " srl"]
    for suffix in suffixes:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()
