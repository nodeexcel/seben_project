from __future__ import annotations

import openpyxl

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedProductInterest
from app.services.product_detection import detect_products_in_text


def parse_crm_xlsx(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="crm")

    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            output.errors.append("Spreadsheet is empty")
            return output

        headers = [str(h).strip().lower() if h else "" for h in rows[0]]
        col = {name: idx for idx, name in enumerate(headers) if name}

        company_col = _find_col(col, ["company"])
        contact_col = _find_col(col, ["contact"])
        email_col = _find_col(col, ["email"])
        phone_col = _find_col(col, ["phone"])
        products_col = _find_col(col, ["interested products", "products", "product"])
        notes_col = _find_col(col, ["notes"])

        imported = 0
        for row in rows[1:]:
            if not row or not any(row):
                continue
            company = _cell(row, company_col)
            if not company:
                continue

            contact_name = _cell(row, contact_col) or company
            email = _cell(row, email_col)
            phone = _cell(row, phone_col)
            products_raw = _cell(row, products_col) or ""
            notes = _cell(row, notes_col)

            output.contacts.append(
                ParsedContact(
                    name=contact_name,
                    email=email,
                    phone=phone,
                    company_name=company,
                )
            )

            for detected in detect_products_in_text(products_raw):
                output.product_interests.append(
                    ParsedProductInterest(
                        product_name=detected.name,
                        form=detected.form,
                        source="crm",
                    )
                )

            if not output.company_name:
                output.company_name = company

            if notes:
                output.metadata.setdefault("notes", {})[company] = notes

            imported += 1

        output.metadata["rows_imported"] = imported
        wb.close()

    except Exception as exc:
        output.errors.append(str(exc))

    return output


def _find_col(col_map: dict[str, int], candidates: list[str]) -> int | None:
    for candidate in candidates:
        if candidate in col_map:
            return col_map[candidate]
    return None


def _cell(row: tuple, idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    val = row[idx]
    if val is None:
        return None
    text = str(val).strip()
    return text or None
