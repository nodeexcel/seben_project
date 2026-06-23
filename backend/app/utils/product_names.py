from __future__ import annotations

import re

from app.data.products import PRODUCT_CATALOG
from app.parsers.invoice import _clean_product_name
from app.services.product_detection import detect_products_in_text

JUNK_PRODUCT_PATTERNS = (
    re.compile(r"\bCIP\b", re.I),
    re.compile(r"Karayolu", re.I),
    re.compile(r"Latince ismi", re.I),
    re.compile(r"\b\d{10,}\b"),
    re.compile(r"\d+kg\s+\d+[,.]?\d*EUR", re.I),
    re.compile(r"%\d\s+0[,.]00\s*EUR", re.I),
    re.compile(r"Gr\.\s*Weight\s*:", re.I),
    re.compile(r"FLERO\s+FLERO", re.I),
    re.compile(r"OLONA\s+OLONA", re.I),
    re.compile(r"\(\s*Latince", re.I),
    re.compile(r"^Not:\s*", re.I),
    re.compile(r"\bNET\s*KG\b", re.I),
    re.compile(r"\bBRÜT\s*KG\b", re.I),
    re.compile(r"\bBRUT\s*KG\b", re.I),
)

WEIGHT_LINE_PRODUCT = re.compile(
    r"Gr\.\s*Weight\s*:.*?kg\s+(.+?)(?:\s+0[,.]00)?$",
    re.I,
)

FISH_TOKEN_TO_CATALOG: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(sea\s*bream|seabream|wr\s*bream|bream|spigola)\b", re.I), "orata"),
    (re.compile(r"\b(sea\s*bass|seabass|bass\s*gutted|branzino)\b", re.I), "branzino"),
    (re.compile(r"\b(red\s*deep\s*sea\s*prawn\s*rosso|gambero\s*rosso)\b", re.I), "gambero rosso"),
    (re.compile(r"\b(red\s*deep\s*sea\s*prawn\s*viola|gambero\s*viola|purple\s*shrimp)\b", re.I), "gambero viola"),
    (re.compile(r"\b(shrimp|prawn)\b", re.I), "gambero rosso"),
    (re.compile(r"\b(cuttlefish|seppia)\b", re.I), "seppia"),
    (re.compile(r"\b(mackerel|sgombro)\b", re.I), "sgombro"),
    (re.compile(r"\b(trout|trota)\b", re.I), "trota"),
    (re.compile(r"\b(octopus|polpo)\b", re.I), "polpo"),
    (re.compile(r"\b(meagre|ombrina|corvina)\b", re.I), "ombrina"),
    (re.compile(r"\b(sole|sogliola)\b", re.I), "sogliola"),
    (re.compile(r"\b(clam|vongol)\b", re.I), "vongole veraci"),
    (re.compile(r"\b(urchin|riccio)\b", re.I), "polpa di riccio"),
]

SIZE_ONLY_RE = re.compile(r"^\d{2,4}\s*[-/]\s*\d{2,4}$")

CATALOG_NAMES = {product.name_it.lower(): product.name_it for product in PRODUCT_CATALOG}


def is_junk_product_name(name: str | None) -> bool:
    if not name:
        return True
    cleaned = name.strip()
    if len(cleaned) < 3:
        return True
    if not re.search(r"[A-Za-z]{3,}", cleaned):
        return True
    if len(cleaned) > 80:
        return True
    if SIZE_ONLY_RE.match(cleaned):
        return True
    if any(pattern.search(cleaned) for pattern in JUNK_PRODUCT_PATTERNS):
        return True
    euro_hits = len(re.findall(r"\bEUR\b|€", cleaned, re.I))
    if euro_hits >= 1 and re.search(r"\d+[,.]\d+", cleaned):
        return True
    if euro_hits >= 2:
        return True
    digit_groups = len(re.findall(r"\d{5,}", cleaned))
    if digit_groups >= 1 and any(p.search(cleaned) for p in JUNK_PRODUCT_PATTERNS[:4]):
        return True
    return False


def _map_fish_token_to_catalog(text: str) -> str | None:
    for pattern, catalog_name in FISH_TOKEN_TO_CATALOG:
        if pattern.search(text):
            return catalog_name
    return None


def normalize_product_label(raw: str | None) -> str | None:
    if not raw or is_junk_product_name(raw):
        return None

    working = raw.strip()
    weight_match = WEIGHT_LINE_PRODUCT.search(working)
    if weight_match:
        working = weight_match.group(1).strip()

    detected = detect_products_in_text(working)
    if detected:
        return CATALOG_NAMES.get(detected[0].name.lower(), detected[0].name)

    catalog = _map_fish_token_to_catalog(working)
    if catalog:
        return catalog

    cleaned = _clean_product_name(working)
    if cleaned:
        catalog = _map_fish_token_to_catalog(cleaned)
        if catalog:
            return catalog
        detected = detect_products_in_text(cleaned)
        if detected:
            return CATALOG_NAMES.get(detected[0].name.lower(), detected[0].name)

    return None


def _catalog_terms_for_filter(filter_term: str) -> set[str]:
    term = filter_term.strip().lower()
    if not term:
        return set()
    terms = {term}
    for product in PRODUCT_CATALOG:
        names = (product.name_it.lower(),) + tuple(alias.lower() for alias in product.aliases)
        if any(term in name or name in term for name in names):
            terms.add(product.name_it.lower())
            terms.update(alias.lower() for alias in product.aliases)
    mapped = _map_fish_token_to_catalog(term)
    if mapped:
        terms.add(mapped.lower())
    return terms


def product_matches_filter(raw: str | None, filter_term: str | None) -> bool:
    if not filter_term:
        return True
    label = normalize_product_label(raw)
    terms = _catalog_terms_for_filter(filter_term)
    haystacks = [h for h in (label, raw) if h]
    for haystack in haystacks:
        low = haystack.lower()
        if any(term in low for term in terms):
            return True
    return False
