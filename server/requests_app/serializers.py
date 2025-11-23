from __future__ import annotations

import json
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ApprovalStep, PurchaseRequest, ReceiptValidationResult, RequestItem
from .services.document_processing import (
    extract_proforma_metadata,
    generate_purchase_order,
    validate_receipt,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]


class RequestItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestItem
        fields = ["id", "description", "quantity", "unit_price"]


class ApprovalStepSerializer(serializers.ModelSerializer):
    approver = UserSerializer(read_only=True)

    class Meta:
        model = ApprovalStep
        fields = ["id", "level", "approver", "decision", "decided_at", "metadata"]


class PurchaseRequestSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    items = RequestItemSerializer(many=True, read_only=True)
    approvals = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseRequest
        fields = [
            "id",
            "title",
            "description",
            "amount",
            "status",
            "created_by",
            "approved_by",
            "current_approval_level",
            "required_approval_levels",
            "proforma",
            "purchase_order",
            "receipt",
            "proforma_metadata",
            "purchase_order_metadata",
            "receipt_validation",
            "items",
            "approvals",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "current_approval_level",
            "required_approval_levels",
            "purchase_order",
            "purchase_order_metadata",
            "receipt_validation",
        ]


class PurchaseRequestWriteSerializer(serializers.ModelSerializer):
    items = RequestItemSerializer(many=True, allow_empty=False)

    def _parse_items_from_form(self, data):
        """Helper to parse flat nested keys like items[0][description] into a list of dicts."""
        items_dict = {}
        for key in data:
            if key.startswith('items['):
                match = re.match(r'items\[(\d+)\]\[(\w+)\]', key)
                if not match:
                    raise serializers.ValidationError({"items": f"Invalid item key format: {key}"})
                idx = int(match.group(1))
                field = match.group(2)
                if idx not in items_dict:
                    items_dict[idx] = {}
                value = data[key][0] if isinstance(data[key], list) else data[key]
                items_dict[idx][field] = value
        if not items_dict:
            raise serializers.ValidationError({"items": "No valid items found in form data."})
        items_list = [items_dict[i] for i in sorted(items_dict)]
        # Validate and convert types
        for item in items_list:
            if not all(k in item for k in ['description', 'quantity', 'unit_price']):
                raise serializers.ValidationError({"items": "Each item must have description, quantity, and unit_price."})
            try:
                item['quantity'] = int(item['quantity'])
                item['unit_price'] = Decimal(item['unit_price'])
            except (ValueError, TypeError):
                raise serializers.ValidationError({"items": "Invalid quantity or unit_price type."})
        return items_list

    def to_internal_value(self, data):
        # Build clean mutable_data with flattened scalars and files
        mutable_data = {}
        for key, value in data.items():
            if key == 'proforma':
                mutable_data[key] = value[0] if isinstance(value, list) and value else value
            elif key.startswith('items['):
                # Skip nested keys, handled separately
                continue
            else:
                mutable_data[key] = value[0] if isinstance(value, list) and value else value

        items_value = mutable_data.get("items")

        # Handle flat nested keys like items[0][description]
        if not items_value or not isinstance(items_value, (list, str)):
            mutable_data["items"] = self._parse_items_from_form(data)

        if isinstance(items_value, str):
            try:
                mutable_data["items"] = json.loads(items_value)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({"items": "Invalid JSON payload"}) from exc

        # Convert amount to Decimal if present
        if 'amount' in mutable_data:
            mutable_data['amount'] = Decimal(mutable_data['amount'])

        return super().to_internal_value(mutable_data)

    class Meta:
        model = PurchaseRequest
        fields = [
            "id",
            "title",
            "description",
            "amount",
            "proforma",
            "items",
        ]

    def validate(self, attrs):
        if self.instance and self.instance.is_terminal:
            raise serializers.ValidationError("Cannot modify an approved or rejected request.")
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        proforma = validated_data.get("proforma")
        creator = validated_data.pop("created_by", self.context["request"].user)
        request_obj = PurchaseRequest.objects.create(created_by=creator, **validated_data)
        RequestItem.objects.bulk_create(
            [
                RequestItem(
                    request=request_obj,
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                )
                for item in items_data
            ]
        )
        if proforma:
            request_obj.proforma_metadata = extract_proforma_metadata(request_obj.proforma)
            request_obj.save(update_fields=["proforma_metadata"])
        for level in range(1, request_obj.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=request_obj, level=level)
        return request_obj

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        proforma = validated_data.get("proforma")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            RequestItem.objects.bulk_create(
                [
                    RequestItem(
                        request=instance,
                        description=item["description"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                    )
                    for item in items_data
                ]
            )
        if proforma:
            instance.proforma_metadata = extract_proforma_metadata(instance.proforma)
            instance.save(update_fields=["proforma_metadata"])
        return instance


class ApprovalActionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ReceiptUploadSerializer(serializers.Serializer):
    receipt = serializers.FileField()

    def validate_receipt(self, value):
        if not value.name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
            raise serializers.ValidationError("Supported receipt formats: pdf, png, jpg.")
        # Sanitize filename
        import re
        value.name = re.sub(r'[^\w\.-]', '_', value.name)
        return value

    def save(self, **kwargs):
        request_obj: PurchaseRequest = self.context["request_obj"]
        receipt_file = self.validated_data["receipt"]
        request_obj.receipt = receipt_file
        request_obj.save(update_fields=["receipt"])
        validation_payload = validate_receipt(request_obj.receipt, request_obj.purchase_order_metadata)
        request_obj.receipt_validation = validation_payload
        request_obj.save(update_fields=["receipt_validation"])
        ReceiptValidationResult.objects.update_or_create(
            request=request_obj,
            defaults={
                "is_valid": validation_payload.get("is_valid", False),
                "mismatches": validation_payload.get("mismatches", {}),
            },
        )
        return request_obj


class PurchaseRequestDetailSerializer(PurchaseRequestSerializer):
    validation_result = serializers.SerializerMethodField()

    class Meta(PurchaseRequestSerializer.Meta):
        fields = PurchaseRequestSerializer.Meta.fields + ["validation_result"]

    def get_validation_result(self, obj):
        if hasattr(obj, "validation_result"):
            return {
                "is_valid": obj.validation_result.is_valid,
                "mismatches": obj.validation_result.mismatches,
                "validated_at": obj.validation_result.validated_at,
            }
        return None
