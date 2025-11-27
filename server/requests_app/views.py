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

from .throttles import ApprovalThrottle

from .models import Notification, PurchaseRequest
from .permissions import IsApprover, IsStaff
from .serializers import (
    ApprovalActionSerializer,
    NotificationSerializer,
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
        if 'only_notifications' in self.request.query_params:
            return PurchaseRequest.objects.none()  # Return empty for notifications param
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
        request_obj = serializer.save(created_by=self.request.user)
        
        # Import notification functions
        from .notifications import create_notification_for_user, notify_approvers_new_request
        
        # Create in-app notification for the creator
        create_notification_for_user(
            self.request.user,
            f"Purchase request '{request_obj.title}' created successfully.",
            request_obj
        )
        
        # Notify approvers about the new request
        notify_approvers_new_request(request_obj)

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
            logger.info(f"Permission denied for approve: user {request.user.username} role '{request.user.role}' != expected '{expected_role}' for request {pk}")
            if request.user.role == "APPROVER_L2" and expected_role == "APPROVER_L1":
                raise PermissionDenied("Please wait for Approver L1 to approve or deny this request first.")
            elif request.user.role == "APPROVER_L1" and expected_role == "APPROVER_L2":
                raise PermissionDenied("This request has been approved by Approver L1 and now requires approval from Approver L2.")
            else:
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

    @action(detail=True, methods=["patch"], permission_classes=[permissions.IsAuthenticated, IsApprover], throttle_classes=[ApprovalThrottle])
    def reject(self, request, pk=None):
        try:
            purchase_request = self.get_object()
            if purchase_request.is_terminal:
                raise ValidationError("Request already finalized.")
            expected_role = purchase_request.next_required_role
            if request.user.role != expected_role:
                logger.info(f"Permission denied for reject: user {request.user.username} role '{request.user.role}' != expected '{expected_role}' for request {pk}")
                if request.user.role == "APPROVER_L2" and expected_role == "APPROVER_L1":
                    raise PermissionDenied("Please wait for Approver L1 to approve or deny this request first.")
                elif request.user.role == "APPROVER_L1" and expected_role == "APPROVER_L2":
                    raise PermissionDenied("This request has been approved by Approver L1 and now requires action from Approver L2.")
                else:
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
            from .notifications import send_receipt_submitted_notification, create_notification_for_user
            send_receipt_submitted_notification(purchase_request, request.user)

            # Create in-app notification for the submitter (with WebSocket)
            create_notification_for_user(
                request.user,
                f"Receipt submitted for request '{purchase_request.title}'.",
                purchase_request
            )

            output = PurchaseRequestDetailSerializer(
                purchase_request, context=self.get_serializer_context()
            )
            logger.info(f"Receipt submitted for request {purchase_request.id} by {request.user.username}")
            return Response(output.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error submitting receipt for request {pk}: {e}")
            raise


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.select_related('user', 'related_request').filter(user=self.request.user).order_by('-timestamp')

    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        try:
            notification = self.get_object()
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return Response({'status': 'marked as read'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['patch'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read', 'count': count})
