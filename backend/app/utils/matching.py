from __future__ import annotations
from rapidfuzz import fuzz

from app.utils.normalize import normalize_company_name, normalize_email, normalize_phone


def contact_name_match_score(name_a: str | None, name_b: str | None) -> float:
    if not name_a or not name_b:
        return 0.0
    return fuzz.token_sort_ratio(name_a.strip().lower(), name_b.strip().lower())


def company_match_score(name_a: str | None, name_b: str | None) -> float:
    norm_a = normalize_company_name(name_a)
    norm_b = normalize_company_name(name_b)
    if not norm_a or not norm_b:
        return 0.0
    return fuzz.token_sort_ratio(norm_a, norm_b)


def contact_match_score(
    email_a: str | None,
    phone_a: str | None,
    email_b: str | None,
    phone_b: str | None,
) -> float:
    norm_email_a = normalize_email(email_a)
    norm_email_b = normalize_email(email_b)
    if norm_email_a and norm_email_b and norm_email_a == norm_email_b:
        return 100.0

    norm_phone_a = normalize_phone(phone_a)
    norm_phone_b = normalize_phone(phone_b)
    if norm_phone_a and norm_phone_b and norm_phone_a == norm_phone_b:
        return 100.0

    return 0.0


def is_likely_same_company(name_a: str | None, name_b: str | None, threshold: float = 85.0) -> bool:
    return company_match_score(name_a, name_b) >= threshold


def is_likely_same_contact(
    email_a: str | None,
    phone_a: str | None,
    email_b: str | None,
    phone_b: str | None,
) -> bool:
    return contact_match_score(email_a, phone_a, email_b, phone_b) >= 100.0
