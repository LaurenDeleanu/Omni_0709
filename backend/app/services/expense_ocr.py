"""
expense_ocr.py — AI-powered receipt scanning and auto-categorization.
Uses the existing LLM cascade to extract structured expense data from images/text.
"""
import logging
import base64
import json
from typing import Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger("successcore.expense_ocr")


async def _call_llm(messages, model="gpt-4o-mini", temperature=0.1, max_tokens=1000):
    """Simple LLM call without agent context — for utility services."""
    from app.core.config import settings
    import openai
    client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise

RECEIPT_PROMPT = """Extract expense receipt information from the following text. Return ONLY valid JSON.

Fields:
- merchant: string (store/vendor name)
- date: string (ISO date YYYY-MM-DD)
- total: number (total amount including tax)
- tax: number (tax amount, 0 if not shown)
- currency: string (USD, EUR, etc.)
- category: string (one of: meals, travel, office_supplies, software, utilities, rent, marketing, other)
- items: list of {{description: string, amount: number}}
- payment_method: string (cash, credit_card, debit_card, other)
- notes: string (any additional notes)

Receipt text:
{receipt_text}

JSON:"""


class ReceiptData(BaseModel):
    merchant: str = ""
    date: str = ""
    total: float = 0
    tax: float = 0
    currency: str = "USD"
    category: str = "other"
    items: list = []
    payment_method: str = "other"
    notes: str = ""


async def scan_receipt_text(receipt_text: str, model: str = "gpt-4o-mini") -> Optional[ReceiptData]:
    """Extract structured expense data from receipt text using LLM."""
    if not receipt_text or len(receipt_text.strip()) < 10:
        return None

    prompt = RECEIPT_PROMPT.format(receipt_text=receipt_text[:6000])

    try:
        import json
        response = await _call_llm(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.1,
            max_tokens=1000,
        )
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response)
        return ReceiptData(**data)
    except Exception as e:
        logger.error(f"Receipt OCR failed: {e}")
        return None


async def scan_receipt_image(image_base64: str, model: str = "gpt-4o-mini") -> Optional[ReceiptData]:
    """Extract expense data from a receipt image using vision model."""
    if not image_base64:
        return None

    prompt = """Extract expense receipt information from this image. Return ONLY valid JSON with these fields:
merchant (vendor name), date (YYYY-MM-DD), total (number), tax (number), currency, category (meals/travel/office_supplies/software/utilities/rent/marketing/other),
items (list of {description, amount}), payment_method, notes."""

    try:
        import json
        response = await _call_llm(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ],
            }],
            model=model,
            temperature=0.1,
            max_tokens=1500,
        )
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response)
        return ReceiptData(**data)
    except Exception as e:
        logger.error(f"Receipt image OCR failed: {e}")
        return None


async def categorize_expense(description: str, amount: float, model: str = "gpt-4o-mini") -> str:
    """Auto-categorize an expense based on description."""
    prompt = f"""Categorize this expense into one category. Return ONLY the category name.

Categories: meals, travel, office_supplies, software, utilities, rent, marketing, payroll, legal, other

Description: {description}
Amount: {amount}

Category:"""

    try:
        response = await _call_llm(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=20,
        )
        category = response.strip().lower()
        valid = {"meals", "travel", "office_supplies", "software", "utilities", "rent", "marketing", "payroll", "legal", "other"}
        return category if category in valid else "other"
    except Exception:
        return "other"
