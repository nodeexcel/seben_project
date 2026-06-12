from __future__ import annotations
import re
from pathlib import Path

from app.parsers.base import ExtractionOutput, ParsedContact, ParsedMessage, _read_text_file

# WhatsApp export format: [DD/MM/YYYY, HH:MM:SS] Sender: Message
WHATSAPP_PATTERN = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APMapm]{2})?)\]\s([^:]+):\s(.*)$"
)


def parse_whatsapp(filepath: str) -> ExtractionOutput:
    output = ExtractionOutput(source_type="whatsapp")
    try:
        text = _read_text_file(filepath)
        output.raw_text = text[:5000]
        output.metadata["filename"] = Path(filepath).name

        lines = text.splitlines()
        chat_title = _extract_chat_title(lines)
        if chat_title:
            output.company_name = chat_title
            output.metadata["chat_title"] = chat_title

        for line in lines:
            match = WHATSAPP_PATTERN.match(line.strip())
            if match:
                timestamp, sender, content = match.groups()
                output.messages.append(
                    ParsedMessage(sender=sender.strip(), content=content.strip(), timestamp=timestamp)
                )

        if not output.messages:
            output.errors.append(
                "No messages parsed — format may differ from standard WhatsApp .txt export"
            )

        participants = {m.sender for m in output.messages if m.sender}
        output.metadata["participant_count"] = len(participants)
        output.metadata["message_count"] = len(output.messages)

    except Exception as exc:
        output.errors.append(str(exc))

    return output


def _extract_chat_title(lines: list[str]) -> str | None:
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and not stripped.startswith("["):
            return stripped
    return None
