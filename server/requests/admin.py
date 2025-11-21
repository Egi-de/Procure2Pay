from django.contrib import admin

from .models import ApprovalStep, PurchaseRequest, ReceiptValidationResult, RequestItem


class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 0


class ApprovalInline(admin.TabularInline):
    model = ApprovalStep
    extra = 0


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "amount", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "created_by__username")
    inlines = [RequestItemInline, ApprovalInline]


@admin.register(ReceiptValidationResult)
class ReceiptValidationResultAdmin(admin.ModelAdmin):
    list_display = ("request", "is_valid", "validated_at")
