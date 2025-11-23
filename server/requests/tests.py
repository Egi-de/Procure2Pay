from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import ApprovalStep, PurchaseRequest, RequestItem, ReceiptValidationResult
from .serializers import PurchaseRequestSerializer, PurchaseRequestWriteSerializer
from .services.document_processing import extract_proforma_metadata, generate_purchase_order, validate_receipt

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

    def test_model_status_transitions(self):
        req = self._build_request()
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)
        req.mark_approved(self.approver_l1, {"comment": "L1 approved"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)
        self.assertEqual(req.current_approval_level, 2)
        req.mark_approved(self.approver_l2, {"comment": "L2 approved"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.APPROVED)
        self.assertIsNotNone(req.approved_by)

    def test_email_notifications_on_approval(self):
        req = self._build_request()
        req.mark_approved(self.approver_l1, {"comment": "Approved"})
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Purchase Request Approved", email.subject)
        self.assertIn(req.title, email.subject)
        self.assertIn(self.staff.email, email.recipients())
        self.assertIn("approved by", email.body)

    def test_email_notifications_on_rejection(self):
        req = self._build_request()
        req.mark_rejected(self.approver_l1, "Insufficient funds")
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Purchase Request Rejected", email.subject)
        self.assertIn(req.title, email.subject)
        self.assertIn(self.staff.email, email.recipients())
        self.assertIn("rejected by", email.body)
        self.assertIn("Insufficient funds", email.body)

    def test_approval_step_creation(self):
        req = self._build_request()
        self.assertEqual(req.approvals.count(), 2)
        self.assertEqual(req.approvals.filter(level=1).first().level, 1)


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass", role=User.Roles.STAFF)

    def test_purchase_request_creation(self):
        req = PurchaseRequest.objects.create(
            title="Test",
            description="Test desc",
            amount=Decimal("1000.00"),
            created_by=self.user,
        )
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)
        self.assertEqual(req.required_approval_levels, 2)
        self.assertEqual(req.current_approval_level, 1)

    def test_request_item_creation(self):
        req = PurchaseRequest.objects.create(
            title="Test",
            description="Test",
            amount=Decimal("1000.00"),
            created_by=self.user,
        )
        item = RequestItem.objects.create(
            request=req,
            description="Item",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        self.assertEqual(item.total_price, Decimal("1000.00"))
        self.assertEqual(req.amount, Decimal("1000.00"))


class SerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass", role=User.Roles.STAFF)
        self.req = PurchaseRequest.objects.create(
            title="Test",
            description="Test",
            amount=Decimal("1000.00"),
            created_by=self.user,
        )
        RequestItem.objects.create(
            request=self.req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )

    def test_purchase_request_serializer(self):
        serializer = PurchaseRequestSerializer(self.req)
        data = serializer.data
        self.assertEqual(data["title"], "Test")
        self.assertEqual(data["status"], "PENDING")
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 1)

    def test_write_serializer_create(self):
        data = {
            "title": "New Request",
            "description": "New desc",
            "amount": "2000.00",
            "items": [
                {"description": "Mouse", "quantity": 5, "unit_price": "100.00"}
            ],
        }
        serializer = PurchaseRequestWriteSerializer(data=data)
        serializer.is_valid()
        request = serializer.save(created_by=self.user)
        self.assertEqual(request.title, "New Request")
        self.assertEqual(request.items.count(), 1)
        item = request.items.first()
        self.assertEqual(item.description, "Mouse")
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.unit_price, Decimal("100.00"))

    def test_write_serializer_update(self):
        data = {
            "title": "Updated Title",
            "description": "Updated desc",
            "amount": "1500.00",
            "items": [
                {"description": "Keyboard", "quantity": 2, "unit_price": "750.00"}
            ],
        }
        serializer = PurchaseRequestWriteSerializer(self.req, data=data)
        serializer.is_valid()
        serializer.save()
        self.req.refresh_from_db()
        self.assertEqual(self.req.title, "Updated Title")
        self.assertEqual(self.req.items.count(), 1)
        item = self.req.items.first()
        self.assertEqual(item.description, "Keyboard")


class ServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass", role=User.Roles.STAFF)
        self.req = PurchaseRequest.objects.create(
            title="Test",
            description="Test",
            amount=Decimal("1000.00"),
            created_by=self.user,
        )
        self.req.proforma = ContentFile(b"Sample proforma text\nVendor: Test Vendor\nTotal: $1000", name="proforma.pdf")
        self.req.save()

    def test_extract_proforma_metadata(self):
        metadata = extract_proforma_metadata(self.req.proforma)
        self.assertIn("vendor", metadata)
        self.assertIn("total_amount", metadata)
        self.assertEqual(metadata["vendor"], "Test Vendor")
        self.assertEqual(metadata["total_amount"], "1000")

    def test_generate_purchase_order(self):
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        po_data = generate_purchase_order(self.req)
        self.assertIn("po_number", po_data)
        self.assertEqual(po_data["vendor"], "Test Vendor")
        self.assertIsNotNone(self.req.purchase_order)
        self.assertIn("purchase_order_metadata", self.req.__dict__)

    def test_validate_receipt(self):
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        generate_purchase_order(self.req)
        receipt_file = ContentFile(b"Receipt text\nVendor: Test Vendor\nTotal: $1000", name="receipt.pdf")
        validation = validate_receipt(receipt_file, self.req.purchase_order_metadata)
        self.assertTrue(validation["is_valid"])
        self.assertEqual(validation["mismatches"], {})

        # Test mismatch
        mismatch_receipt = ContentFile(b"Receipt text\nVendor: Wrong Vendor\nTotal: $2000", name="mismatch.pdf")
        mismatch_validation = validate_receipt(mismatch_receipt, self.req.purchase_order_metadata)
        self.assertFalse(mismatch_validation["is_valid"])
        self.assertIn("vendor", mismatch_validation["mismatches"])
        self.assertIn("amount", mismatch_validation["mismatches"])


class ViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user("staff", password="pass", role=User.Roles.STAFF)
        self.approver = User.objects.create_user("approver", password="pass", role=User.Roles.APPROVER_L1)
        self.req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=self.req,
            description="Item",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, self.req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=self.req, level=level)

    def test_list_requests_staff(self):
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse('purchaserequest-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_request(self):
        self.client.login(username="staff", password="pass")
        data = {
            "title": "New Request",
            "description": "New",
            "amount": "2000.00",
            "items": [
                {"description": "New Item", "quantity": 1, "unit_price": "2000.00"}
            ],
        }
        response = self.client.post(reverse('purchaserequest-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseRequest.objects.count(), 2)

    def test_approve_request(self):
        self.client.login(username="approver", password="pass")
        response = self.client.patch(
            reverse('purchaserequest-approve', kwargs={'pk': self.req.pk}),
            {'comment': 'Approved'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.req.refresh_from_db()
        self.assertEqual(self.req.current_approval_level, 2)

    def test_permission_denied_non_approver(self):
        self.client.login(username="staff", password="pass")
        response = self.client.patch(
            reverse('purchaserequest-approve', kwargs={'pk': self.req.pk}),
            {'comment': 'Try approve'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receipt_submission(self):
        self.client.login(username="staff", password="pass")
        # Simulate approval
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        receipt_file = ContentFile(b"Receipt data", name="receipt.pdf")
        data = {'receipt': receipt_file}
        response = self.client.post(
            reverse('purchaserequest-submit-receipt', kwargs={'pk': self.req.pk}),
            data,
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.req.receipt)
        self.assertIsNotNone(self.req.receipt_validation)
