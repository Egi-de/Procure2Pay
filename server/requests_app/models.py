import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class PurchaseRequest(models.Model):
    WORKFLOW_ROLES = [
        "APPROVER_L1",
        "APPROVER_L2",
    ]

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="created_requests", on_delete=models.CASCADE
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="approved_requests",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    current_approval_level = models.PositiveSmallIntegerField(default=1)
    required_approval_levels = models.PositiveSmallIntegerField(
        default=len(WORKFLOW_ROLES)
    )
    proforma = models.FileField(upload_to="proformas/", blank=True, null=True)
    purchase_order = models.FileField(upload_to="purchase_orders/", blank=True, null=True)
    receipt = models.FileField(upload_to="receipts/", blank=True, null=True)
    proforma_metadata = models.JSONField(default=dict, blank=True)
    purchase_order_metadata = models.JSONField(default=dict, blank=True)
    receipt_validation = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_terminal(self):
        return self.status in {self.Status.APPROVED, self.Status.REJECTED}

    @property
    def next_required_role(self):
        idx = self.current_approval_level - 1
        return (
            self.WORKFLOW_ROLES[idx]
            if idx < len(self.WORKFLOW_ROLES)
            else None
        )

    @transaction.atomic
    def mark_approved(self, approver, metadata: dict | None = None) -> None:
        if self.is_terminal:
            raise ValueError("Cannot approve a terminal request")
        level = self.current_approval_level
        ApprovalStep.objects.update_or_create(
            request=self,
            level=level,
            defaults={
                "approver": approver,
                "decision": ApprovalStep.Decision.APPROVED,
                "decided_at": timezone.now(),
                "metadata": metadata or {},
            },
        )
        if level >= self.required_approval_levels:
            self.status = self.Status.APPROVED
            self.approved_by = approver
        else:
            self.current_approval_level += 1
        self.save(update_fields=["current_approval_level", "status", "approved_by", "updated_at"])
        
        # Send notifications (email + in-app + WebSocket)
        from .notifications import send_approval_notification, notify_request_approved
        send_approval_notification(self, approver)
        notify_request_approved(self, approver)

    @transaction.atomic
    def mark_rejected(self, approver, reason: str = "") -> None:
        if self.is_terminal:
            raise ValueError("Cannot reject a terminal request")
        ApprovalStep.objects.update_or_create(
            request=self,
            level=self.current_approval_level,
            defaults={
                "approver": approver,
                "decision": ApprovalStep.Decision.REJECTED,
                "decided_at": timezone.now(),
                "metadata": {"reason": reason},
            },
        )
        self.status = self.Status.REJECTED
        self.approved_by = approver
        self.save(update_fields=["status", "approved_by", "updated_at"])
        
        # Send notifications (email + in-app + WebSocket)
        from .notifications import send_rejection_notification, notify_request_rejected
        send_rejection_notification(self, approver)
        notify_request_rejected(self, approver, reason)


class RequestItem(models.Model):
    request = models.ForeignKey(
        PurchaseRequest, related_name="items", on_delete=models.CASCADE
    )
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} x{self.quantity}"
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price


class ApprovalStep(models.Model):
    class Decision(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    request = models.ForeignKey(
        PurchaseRequest, related_name="approvals", on_delete=models.CASCADE
    )
    level = models.PositiveSmallIntegerField()
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="approval_steps",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    decision = models.CharField(
        max_length=16, choices=Decision.choices, default=Decision.PENDING
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("request", "level")
        ordering = ["level"]

    def __str__(self):
        return f"{self.request_id} - level {self.level} - {self.decision}"


class ReceiptValidationResult(models.Model):
    request = models.OneToOneField(
        PurchaseRequest, related_name="validation_result", on_delete=models.CASCADE
    )
    is_valid = models.BooleanField(default=False)
    mismatches = models.JSONField(default=dict, blank=True)
    validated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request_id} validation: {'valid' if self.is_valid else 'invalid'}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    related_request = models.ForeignKey(
        PurchaseRequest, related_name="notifications", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"
