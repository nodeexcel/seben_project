from __future__ import annotations
import re
from pathlib import Path

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedMessage, ParsedProductInterest, _read_text_file
from app.services.product_detection import detect_form_in_text, detect_products_in_text

WHATSAPP_PATTERN = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APMapm]{2})?)\]\s([^:]+):\s(.*)$"
)

INTERNAL_SENDERS = {"mehmet göle", "mehmet gole", "you"}


def parse_whatsapp(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="whatsapp")
    try:
        text = _read_text_file(filepath)
        output.raw_text = text[:8000]
        output.metadata["filename"] = Path(filepath).name

        lines = text.splitlines()
        chat_title = _extract_chat_title(lines)
        if chat_title:
            output.company_name = chat_title
            output.metadata["chat_title"] = chat_title

        participants: set[str] = set()
        all_content: list[str] = []

        for line in lines:
            match = WHATSAPP_PATTERN.match(line.strip())
            if match:
                timestamp, sender, content = match.groups()
                sender = sender.strip()
                content = content.strip()
                output.messages.append(
                    ParsedMessage(sender=sender, content=content, timestamp=timestamp)
                )
                if sender.lower() not in INTERNAL_SENDERS:
                    participants.add(sender)
                all_content.append(content)

        if not output.messages:
            output.errors.append(
                "No messages parsed — format may differ from standard WhatsApp .txt export"
            )

        for participant in participants:
            output.contacts.append(ParsedContact(name=participant))

        if participants and not output.company_name:
            output.company_name = sorted(participants)[0]

        combined = "\n".join(all_content)
        for detected in detect_products_in_text(combined):
            output.product_interests.append(
                ParsedProductInterest(
                    product_name=detected.name,
                    form=detected.form,
                    source="whatsapp",
                )
            )

        forms = detect_form_in_text(combined)
        output.metadata["forms_detected"] = list(forms)
        output.metadata["participant_count"] = len(participants)
        output.metadata["message_count"] = len(output.messages)
        output.metadata["products_detected"] = [p.product_name for p in output.product_interests]

    except Exception as exc:
        output.errors.append(str(exc))

    return output


def _extract_chat_title(lines: list[str]) -> str | None:
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and not stripped.startswith("["):
            return stripped
    return None
