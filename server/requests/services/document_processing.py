from __future__ import annotations

import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image
from PyPDF2 import PdfReader
import pytesseract


def _extract_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    uploaded_file.open("rb")
    data = uploaded_file.read()
    uploaded_file.seek(0)
    if uploaded_file.name.lower().endswith(".pdf"):
        pdf_reader = PdfReader(io.BytesIO(data))
        text_chunks = []
        for page in pdf_reader.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
        return "\n".join(text_chunks)
    try:
        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image)
    except Exception:
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


def extract_proforma_metadata(uploaded_file) -> dict[str, Any]:
    text = _extract_text(uploaded_file)
    vendor_match = re.search(r"Vendor[:\-]\s*(.*)", text, re.IGNORECASE)
    currency_match = re.search(r"Currency[:\-]\s*([A-Z]{3})", text, re.IGNORECASE)
    total = _extract_number_from_text(r"Total[:\-]?\s*([$€£]?)(\d+(\.\d{1,2})?)", text)
    metadata = {
        "vendor": vendor_match.group(1).strip() if vendor_match else "Unknown Vendor",
        "currency": currency_match.group(1) if currency_match else "USD",
        "total_amount": str(total) if total is not None else "0",
        "extracted_on": timezone.now().isoformat(),
        "source": "proforma",
        "raw_excerpt": text[:500],
    }
    return metadata


def generate_purchase_order(request_obj) -> dict[str, Any]:
    metadata = request_obj.proforma_metadata or {}
    po_data = {
        "po_number": f"PO-{datetime.utcnow():%Y%m%d}-{str(request_obj.id)[:8]}",
        "vendor": metadata.get("vendor", "Unknown Vendor"),
        "currency": metadata.get("currency", "USD"),
        "total_amount": metadata.get("total_amount", str(request_obj.amount)),
        "generated_at": timezone.now().isoformat(),
        "items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in request_obj.items.all()
        ],
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
    return {"is_valid": not mismatches, "mismatches": mismatches, "raw_excerpt": text[:500]}

