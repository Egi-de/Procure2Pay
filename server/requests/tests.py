from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import ApprovalStep, PurchaseRequest, RequestItem

User = get_user_model()


class PurchaseRequestWorkflowTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="pass", role=User.Roles.STAFF)
        self.approver_l1 = User.objects.create_user(
            "approver1", password="pass", role=User.Roles.APPROVER_L1
        )
        self.approver_l2 = User.objects.create_user(
            "approver2", password="pass", role=User.Roles.APPROVER_L2
        )

    def _build_request(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Capex",
            amount=1000,
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=2,
            unit_price=500,
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)
        return req

    def test_final_approval_marks_request(self):
        req = self._build_request()
        req.mark_approved(self.approver_l1, {"comment": "Looks good"})
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)
        req.refresh_from_db()
        req.mark_approved(self.approver_l2, {"comment": "Approved"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.APPROVED)

    def test_rejection_short_circuits_workflow(self):
        req = self._build_request()
        req.mark_rejected(self.approver_l1, "Insufficient budget")
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.REJECTED)
