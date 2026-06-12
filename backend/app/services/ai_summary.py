from __future__ import annotations
from openai import OpenAI

from app.config import settings


def generate_customer_summary(company_data: dict) -> str | None:
    if not settings.openai_api_key:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = (
        "Generate a concise business summary for this customer profile. "
        "Include key contacts, purchase patterns, and communication highlights.\n\n"
        f"Customer data:\n{company_data}"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    return response.choices[0].message.content
