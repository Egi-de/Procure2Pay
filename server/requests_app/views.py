import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import PurchaseRequest
from .permissions import IsApprover, IsStaff
from .serializers import (
    ApprovalActionSerializer,
    PurchaseRequestDetailSerializer,
    PurchaseRequestSerializer,
    PurchaseRequestWriteSerializer,
    ReceiptUploadSerializer,
)
from .services.document_processing import generate_purchase_order

User = get_user_model()
logger = logging.getLogger(__name__)


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseRequest.objects.select_related("created_by", "approved_by", "validation_result")
        .prefetch_related("items", "approvals")
        .all()
    )
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "submit_receipt"}:
            return [permissions.IsAuthenticated(), IsStaff()]
        if self.action in {"approve", "reject"}:
            return [permissions.IsAuthenticated(), IsApprover()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if user.role == User.Roles.STAFF:
            return qs.filter(created_by=user)
        if user.role in (User.Roles.APPROVER_L1, User.Roles.APPROVER_L2):
            return qs.filter(status=PurchaseRequest.Status.PENDING)
        if user.role == User.Roles.FINANCE:
            return qs  # Full access for finance
        return qs

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PurchaseRequestWriteSerializer
        if self.action == "retrieve":
            return PurchaseRequestDetailSerializer
        return PurchaseRequestSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.created_by != self.request.user:
            raise PermissionDenied("Only the owner can update the request")
        if instance.status != PurchaseRequest.Status.PENDING:
            raise ValidationError("Only pending requests can be updated.")
        serializer.save()

    @action(detail=True, methods=["patch"], permission_classes=[permissions.IsAuthenticated, IsApprover])
    def approve(self, request, pk=None):
        purchase_request = self.get_object()
        if purchase_request.is_terminal:
            raise ValidationError("Request already finalized.")
        expected_role = purchase_request.next_required_role
        if request.user.role != expected_role:
            raise PermissionDenied("You are not the expected approver for this level.")
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            purchase_request.mark_approved(request.user, serializer.validated_data)
            if purchase_request.status == PurchaseRequest.Status.APPROVED:
                generate_purchase_order(purchase_request)
        output = PurchaseRequestDetailSerializer(
            purchase_request, context=self.get_serializer_context()
        )
        return Response(output.data)

    @action(detail=True, methods=["patch"], permission_classes=[permissions.IsAuthenticated, IsApprover])
    def reject(self, request, pk=None):
        try:
            purchase_request = self.get_object()
            if purchase_request.is_terminal:
                raise ValidationError("Request already finalized.")
            expected_role = purchase_request.next_required_role
            if request.user.role != expected_role:
                raise PermissionDenied("You are not the expected approver for this level.")
            serializer = ApprovalActionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                purchase_request.mark_rejected(
                    request.user, serializer.validated_data.get("comment", "")
                )
            output = PurchaseRequestDetailSerializer(
                purchase_request, context=self.get_serializer_context()
            )
            logger.info(f"Request {purchase_request.id} rejected by {request.user.username}")
            return Response(output.data)
        except Exception as e:
            logger.error(f"Error rejecting request {pk}: {e}")
            raise

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, IsStaff],
        url_path="submit-receipt",
    )
    def submit_receipt(self, request, pk=None):
        try:
            purchase_request = self.get_object()
            if purchase_request.created_by != request.user:
                raise PermissionDenied("Only the request owner can submit receipts.")
            if purchase_request.status != PurchaseRequest.Status.APPROVED:
                raise ValidationError("Receipt submission allowed only after approval.")
            serializer = ReceiptUploadSerializer(
                data=request.data,
                context={"request_obj": purchase_request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Send notification to finance team
            from .notifications import send_receipt_submitted_notification
            send_receipt_submitted_notification(purchase_request, request.user)

            output = PurchaseRequestDetailSerializer(
                purchase_request, context=self.get_serializer_context()
            )
            logger.info(f"Receipt submitted for request {purchase_request.id} by {request.user.username}")
            return Response(output.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error submitting receipt for request {pk}: {e}")
            raise
