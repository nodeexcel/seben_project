from __future__ import annotations
import re

import phonenumbers
from phonenumbers import NumberParseException


def normalize_phone(phone: str | None, default_region: str = "IT") -> str | None:
    if not phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    if not cleaned or len(cleaned) > 15:
        return None
    for region in (default_region, "IT", "US", "TR"):
        try:
            parsed = phonenumbers.parse(cleaned, region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException:
            continue
    if cleaned.startswith("+") and 8 <= len(cleaned) <= 16:
        return cleaned[:50]
    if cleaned.isdigit() and 7 <= len(cleaned) <= 15:
        return cleaned[:50]
    return None


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
