from __future__ import annotations
from pathlib import Path

from app.parsers.contacts import parse_contacts
from app.parsers.crm_xlsx import parse_crm_xlsx
from app.parsers.email_parser import parse_email
from app.parsers.invoice import parse_invoice
from app.parsers.whatsapp import parse_whatsapp
from app.parsers.base import ExtractionOutput

PARSERS = {
    "whatsapp": {".txt"},
    "contact": {".vcf", ".csv", ".tsv"},
    "email": {".eml", ".mbox"},
    "invoice": {".pdf"},
    "crm": {".xlsx", ".xls"},
}

PARSER_FUNCTIONS = {
    "whatsapp": parse_whatsapp,
    "contact": parse_contacts,
    "email": parse_email,
    "invoice": parse_invoice,
    "crm": parse_crm_xlsx,
}


def detect_source_type(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    for source_type, extensions in PARSERS.items():
        if suffix in extensions:
            return source_type
    return None


def parse_file(filepath: str, source_type: str | None = None) -> ExtractionOutput:
    if source_type is None:
        source_type = detect_source_type(filepath)
    if source_type is None:
        return ExtractionOutput(
            source_type="unknown",
            errors=[f"Could not detect file type for: {Path(filepath).name}"],
        )

    parser = PARSER_FUNCTIONS.get(source_type)
    if parser is None:
        return ExtractionOutput(
            source_type=source_type,
            errors=[f"No parser available for source type: {source_type}"],
        )

    return parser(filepath)
