from __future__ import annotations

import io
import json
import logging
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image
from PyPDF2 import PdfReader
import openai
import pytesseract
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def _extract_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    uploaded_file.open("rb")
    data = uploaded_file.read()
    uploaded_file.seek(0)
    if uploaded_file.name.lower().endswith(".pdf"):
        try:
            pdf_reader = PdfReader(io.BytesIO(data))
            text_chunks = []
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
            return "\n".join(text_chunks)
        except Exception as e:
            logger.error(f"PDF extraction failed for {uploaded_file.name}: {e}")
            return ""
    try:
        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image)
    except Exception as e:
        logger.error(f"Image extraction failed for {uploaded_file.name}: {e}")
        return ""


def _extract_number_from_text(pattern: str, text: str) -> Decimal | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    try:
        target = None
        for group in match.groups()[::-1]:
            if group and re.search(r"\d", group):
                target = group
                break
        if not target:
            return None
        value = target.replace(",", "").strip()
        return Decimal(value)
    except (ValueError, InvalidOperation):
        return None


def _extract_with_ai(text: str, prompt: str) -> dict[str, Any] | None:
    """Use OpenAI to extract structured data from text."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, skipping AI extraction.")
        return None
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert at extracting structured data from documents. Respond only with valid JSON."},
                {"role": "user", "content": f"{prompt}\n\nDocument text:\n{text[:4000]}"},  # Limit text to avoid token limits
            ],
            max_tokens=500,
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        return json.loads(content)
    except (openai.OpenAIError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"AI extraction failed: {e}")
        return None


def extract_proforma_metadata(uploaded_file) -> dict[str, Any]:
    try:
        text = _extract_text(uploaded_file)
    except Exception as e:
        logger.error(f"Proforma metadata extraction failed: {e}")
        text = ""
    if text:
        # Try AI extraction first
        prompt = (
            "Extract the following from the proforma document: vendor name, currency (3-letter code), total amount (as number), "
            "and a list of items with description, quantity, and unit_price. Respond as JSON: "
            '{"vendor": "string", "currency": "string", "total_amount": number, "items": [{"description": "string", "quantity": number, "unit_price": number}]}'
        )
        ai_result = _extract_with_ai(text, prompt)
        if ai_result and isinstance(ai_result, dict):
            metadata = {
                "vendor": ai_result.get("vendor", "Unknown Vendor"),
                "currency": ai_result.get("currency", "USD"),
                "total_amount": str(ai_result.get("total_amount", "0")),
                "items": ai_result.get("items", []),
                "extracted_on": timezone.now().isoformat(),
                "source": "proforma",
                "raw_excerpt": text[:500],
                "extraction_method": "ai",
                "extraction_error": False,
            }
            logger.info(f"AI extraction successful for proforma {uploaded_file.name if uploaded_file else 'unknown'}")
            return metadata
    # Fallback to regex
    try:
        vendor_match = re.search(r"Vendor[:\-]\s*(.*)", text, re.IGNORECASE)
        currency_match = re.search(r"Currency[:\-]\s*([A-Z]{3})", text, re.IGNORECASE)
        total = _extract_number_from_text(r"Total[:\-]?\s*([$€£]?)(\d+(\.\d{1,2})?)", text)
        metadata = {
            "vendor": vendor_match.group(1).strip() if vendor_match else "Unknown Vendor",
            "currency": currency_match.group(1) if currency_match else "USD",
            "total_amount": str(total) if total is not None else "0",
            "items": [],  # No items from regex
            "extracted_on": timezone.now().isoformat(),
            "source": "proforma",
            "raw_excerpt": text[:500],
            "extraction_method": "regex",
            "extraction_error": text == "" and uploaded_file is not None,
        }
        logger.info(f"Regex fallback extraction used for proforma {uploaded_file.name if uploaded_file else 'unknown'}")
        return metadata
    except Exception as e:
        logger.error(f"Regex extraction failed for proforma {uploaded_file.name if uploaded_file else 'unknown'}: {e}")
        return {
            "vendor": "Unknown Vendor",
            "currency": "USD",
            "total_amount": "0",
            "items": [],
            "extracted_on": timezone.now().isoformat(),
            "source": "proforma",
            "raw_excerpt": "",
            "extraction_method": "failed",
            "extraction_error": True,
        }


def generate_purchase_order(request_obj) -> dict[str, Any]:
    metadata = request_obj.proforma_metadata or {}
    po_data = {
        "po_number": f"PO-{datetime.utcnow():%Y%m%d}-{str(request_obj.id)[:8]}",
        "vendor": metadata.get("vendor", "Unknown Vendor"),
        "currency": metadata.get("currency", "USD"),
        "total_amount": metadata.get("total_amount", str(request_obj.amount)),
        "generated_at": timezone.now().isoformat(),
        "items": metadata.get("items", [  # Use AI-extracted items if available, else from request
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in request_obj.items.all()
        ]),
    }
    content = "\n".join(
        [
            "Purchase Order",
            f"PO Number: {po_data['po_number']}",
            f"Vendor: {po_data['vendor']}",
            f"Currency: {po_data['currency']}",
            f"Total Amount: {po_data['total_amount']}",
            "Items:",
        ]
        + [
            f"- {item['description']} x{item['quantity']} @ {item['unit_price']}"
            for item in po_data["items"]
        ]
    )
    filename = f"{po_data['po_number']}.txt"
    request_obj.purchase_order.save(filename, ContentFile(content), save=False)
    request_obj.purchase_order_metadata = po_data
    request_obj.save(update_fields=["purchase_order", "purchase_order_metadata"])
    return po_data


def validate_receipt(receipt_file, po_metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not receipt_file or not po_metadata:
        return {"is_valid": False, "mismatches": {"reason": "Missing receipt or PO metadata."}}
    text = _extract_text(receipt_file)
    vendor_match = re.search(r"Vendor[:\-]\s*(.*)", text, re.IGNORECASE)
    total = _extract_number_from_text(r"Total[:\-]?\s*([$€£]?)(\d+(\.\d{1,2})?)", text)
    mismatches = {}
    if vendor_match:
        receipt_vendor = vendor_match.group(1).strip()
        if receipt_vendor.lower() != po_metadata.get("vendor", "").lower():
            mismatches["vendor"] = {
                "expected": po_metadata.get("vendor"),
                "actual": receipt_vendor,
            }
    if total is not None and Decimal(str(total)) != Decimal(str(po_metadata.get("total_amount", "0"))):
        mismatches["amount"] = {
            "expected": po_metadata.get("total_amount"),
            "actual": str(total),
        }
    # Compare full item lists
    po_items = po_metadata.get("items", [])
    receipt_items = _extract_items_from_text(text)
    if po_items and receipt_items:
        item_mismatches = []
        for po_item in po_items:
            matched = False
            for rec_item in receipt_items:
                if (po_item.get("description", "").lower().strip() == rec_item.get("description", "").lower().strip() and
                    po_item.get("quantity") == rec_item.get("quantity") and
                    Decimal(str(po_item.get("unit_price", 0))) == Decimal(str(rec_item.get("unit_price", 0)))):
                    matched = True
                    break
            if not matched:
                item_mismatches.append({
                    "expected": po_item,
                    "reason": "No matching item in receipt"
                })
        if item_mismatches:
            mismatches["items"] = item_mismatches
    elif po_items:
        mismatches["items"] = [{"reason": "No items found in receipt"}]
    return {"is_valid": not mismatches, "mismatches": mismatches, "raw_excerpt": text[:500]}


def _extract_items_from_text(text: str) -> list[dict[str, Any]]:
    """Extract items from receipt text using regex or AI if possible."""
    items = []
    # Simple regex for items: assume format like "Item: desc x qty @ price"
    item_pattern = re.findall(r"Item[:\-]?\s*(.*?)\s*x?\s*(\d+)\s*@?\s*([$€£]?)(\d+(\.\d{1,2})?)", text, re.IGNORECASE)
    for match in item_pattern:
        desc, qty, currency, price, _ = match
        try:
            items.append({
                "description": desc.strip(),
                "quantity": int(qty),
                "unit_price": Decimal(price),
            })
        except (ValueError, InvalidOperation):
            continue
    # If no items, try AI
    if not items:
        prompt = "Extract a list of items from the receipt with description, quantity, and unit_price. Respond as JSON array: [{\"description\": \"string\", \"quantity\": number, \"unit_price\": number}]"
        ai_result = _extract_with_ai(text, prompt)
        if ai_result and isinstance(ai_result, list):
            items = ai_result
    return items

