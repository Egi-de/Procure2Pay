from decimal import Decimal
import os
import threading
import time

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch

from .models import ApprovalStep, PurchaseRequest, RequestItem, ReceiptValidationResult
from .serializers import PurchaseRequestSerializer, PurchaseRequestWriteSerializer
from .services.document_processing import extract_proforma_metadata, generate_purchase_order, validate_receipt

User = get_user_model()


# server/requests_app/tests.py - Add email to users in setUp

class PurchaseRequestWorkflowTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            "staff",
            email="staff@example.com",  # Add email
            password="pass",
            role=User.Roles.STAFF
        )
        self.approver_l1 = User.objects.create_user(
            "approver1",
            email="approver1@example.com",  # Add email
            password="pass",
            role=User.Roles.APPROVER_L1
        )
        self.approver_l2 = User.objects.create_user(
            "approver2",
            email="approver2@example.com",  # Add email
            password="pass",
            role=User.Roles.APPROVER_L2
        )

    def test_request_creation(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)
        self.assertEqual(req.amount, Decimal("1000.00"))
        self.assertEqual(req.items.count(), 1)

    def test_request_approval_workflow(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        # Create approval steps
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Approve with L1
        req.mark_approved(self.approver_l1, {"comment": "Approved by L1"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)

        # Approve with L2
        req.mark_approved(self.approver_l2, {"comment": "Approved by L2"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.APPROVED)

    def test_request_rejection(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        # Create approval steps
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Reject with L1
        req.mark_rejected(self.approver_l1, "Rejected by L1")
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.REJECTED)

    def test_request_status_transitions(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        # Create approval steps
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Initial status
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)

        # Approve L1
        req.mark_approved(self.approver_l1, {"comment": "Approved"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)

        # Approve L2
        req.mark_approved(self.approver_l2, {"comment": "Approved"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.APPROVED)

    def test_approval_notifications(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        # Create approval steps
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Approve request (L1)
        req.mark_approved(self.approver_l1, {"comment": "Approved"})
        req.refresh_from_db()

        # Check that approval email sent to staff
        self.assertEqual(len(mail.outbox), 1)
        emails_to_staff = [email for email in mail.outbox if self.staff.email in email.to]
        self.assertEqual(len(emails_to_staff), 1)
        self.assertIn("Approved", emails_to_staff[0].subject)

    def test_rejection_notifications(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        # Create approval steps
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Reject request
        req.mark_rejected(self.approver_l1, "Rejected")
        req.refresh_from_db()

        # Check that rejection email was sent to staff
        self.assertEqual(len(mail.outbox), 1)
        rejection_email = mail.outbox[-1]
        self.assertIn(self.staff.email, rejection_email.to)
        self.assertIn("rejected", rejection_email.subject.lower())

    def test_invalid_approval_on_terminal_request(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Reject first
        req.mark_rejected(self.approver_l1, "Rejected")
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.REJECTED)

        # Try to approve rejected request
        with self.assertRaises(ValueError):
            req.mark_approved(self.approver_l2, {"comment": "Should fail"})

    def test_rejection_at_any_level(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Approve L1
        req.mark_approved(self.approver_l1, {"comment": "Approved L1"})
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.PENDING)

        # Reject at L2
        req.mark_rejected(self.approver_l2, "Rejected at L2")
        req.refresh_from_db()
        self.assertEqual(req.status, PurchaseRequest.Status.REJECTED)

    def test_email_notifications_multi_level(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Approve L1 (sends approval to staff, request to L2)
        req.mark_approved(self.approver_l1, {"comment": "Approved L1"})
        req.refresh_from_db()
        self.assertEqual(len(mail.outbox), 2)
        emails_to_staff = [email for email in mail.outbox if self.staff.email in email.to]
        self.assertEqual(len(emails_to_staff), 1)
        self.assertIn("Approved", emails_to_staff[0].subject)

        # Approve L2 (sends approval to staff)
        req.mark_approved(self.approver_l2, {"comment": "Approved L2"})
        req.refresh_from_db()
        self.assertEqual(len(mail.outbox), 3)
        emails_to_staff_after_l2 = [email for email in mail.outbox if self.staff.email in email.to]
        self.assertEqual(len(emails_to_staff_after_l2), 2)
        self.assertIn("Approved", emails_to_staff_after_l2[1].subject)

    def test_email_failure_logging(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        # Mock send_mail to raise exception
        with patch('django.core.mail.send_mail') as mock_send:
            mock_send.side_effect = Exception("SMTP error")
            req.mark_approved(self.approver_l1, {"comment": "Approved"})
            # Should not raise, but log error (can't easily test logging in unit test)

    def test_no_email_if_no_staff_email(self):
        staff_no_email = User.objects.create_user(
            "staff_no_email",
            password="pass",
            role=User.Roles.STAFF
        )
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=staff_no_email,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        req.mark_approved(self.approver_l1, {"comment": "Approved"})
        # Approval email not sent to staff (no email)
        self.assertEqual(len(mail.outbox), 0)
        # Ensure no email to staff
        emails_to_staff = [email for email in mail.outbox if staff_no_email.email in email.to]
        self.assertEqual(len(emails_to_staff), 0)


class ConcurrentApprovalTests(TransactionTestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            "staff",
            email="staff@example.com",
            password="pass",
            role=User.Roles.STAFF
        )
        self.approver_l1 = User.objects.create_user(
            "approver1",
            email="approver1@example.com",
            password="pass",
            role=User.Roles.APPROVER_L1
        )
        self.approver_l2 = User.objects.create_user(
            "approver2",
            email="approver2@example.com",
            password="pass",
            role=User.Roles.APPROVER_L2
        )

    def test_concurrent_approvals(self):
        req = PurchaseRequest.objects.create(
            title="Test Request",
            description="Test description",
            amount=Decimal("1000.00"),
            created_by=self.staff,
        )
        RequestItem.objects.create(
            request=req,
            description="Laptop",
            quantity=1,
            unit_price=Decimal("1000.00"),
        )
        for level in range(1, req.required_approval_levels + 1):
            ApprovalStep.objects.get_or_create(request=req, level=level)

        results = []

        def approve_l1():
            time.sleep(0.1)  # Simulate delay
            req.mark_approved(self.approver_l1, {"comment": "Concurrent L1"})
            results.append("L1 done")

        def approve_l2():
            req.mark_approved(self.approver_l2, {"comment": "Concurrent L2"})
            results.append("L2 done")

        thread1 = threading.Thread(target=approve_l1)
        thread2 = threading.Thread(target=approve_l2)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        req.refresh_from_db()
        # Should be approved despite concurrency
        self.assertEqual(req.status, PurchaseRequest.Status.APPROVED)
        self.assertIn("L1 done", results)
        self.assertIn("L2 done", results)


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "testuser",
            email="testuser@example.com",  # Add email
            password="pass",
            role=User.Roles.STAFF
        )

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
        self.user = User.objects.create_user(
            "testuser",
            email="testuser@example.com",  # Add email
            password="pass",
            role=User.Roles.STAFF
        )
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

    def test_write_serializer_create(self):
        data = {
            "title": "New Request",
            "description": "New desc",
            "amount": "2000.00",
            "items": [
                {"description": "Mouse", "quantity": 5, "unit_price": "100.00"}
            ],
        }
        # Add context with request
        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.user = self.user
        
        serializer = PurchaseRequestWriteSerializer(
            data=data,
            context={'request': mock_request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        request = serializer.save(created_by=self.user)
        self.assertEqual(request.title, "New Request")
        self.assertEqual(request.items.count(), 1)

    def test_write_serializer_update(self):
        data = {
            "title": "Updated Title",
            "description": "Updated desc",
            "amount": "1500.00",
            "items": [
                {"description": "Keyboard", "quantity": 2, "unit_price": "750.00"}
            ],
        }
        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.user = self.user
        
        serializer = PurchaseRequestWriteSerializer(
            self.req,
            data=data,
            context={'request': mock_request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.req.refresh_from_db()
        self.assertEqual(self.req.title, "Updated Title")


class ServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "testuser",
            email="testuser@example.com",
            password="pass",
            role=User.Roles.STAFF
        )
        self.req = PurchaseRequest.objects.create(
            title="Test",
            description="Test",
            amount=Decimal("1000.00"),
            created_by=self.user,
        )

    def test_extract_proforma_metadata_valid_pdf(self):
        # Realistic proforma text
        proforma_text = (
            "Proforma Invoice\n"
            "Vendor: Acme Supplies Inc.\n"
            "Currency: USD\n"
            "Item: Laptop Qty: 1 Unit Price: 1000.00\n"
            "Item: Mouse Qty: 2 Unit Price: 25.00\n"
            "Total Amount: $1050.00"
        )
        self.req.proforma.save("proforma.pdf", ContentFile(proforma_text.encode(), name="proforma.pdf"), save=True)

        metadata = extract_proforma_metadata(self.req.proforma)
        self.assertIn("vendor", metadata)
        self.assertIn("total_amount", metadata)
        self.assertIn("currency", metadata)
        self.assertIn("items", metadata)
        self.assertEqual(metadata["vendor"], "Acme Supplies Inc.")
        self.assertEqual(metadata["currency"], "USD")
        self.assertEqual(metadata["total_amount"], "1050.00")
        self.assertEqual(len(metadata["items"]), 2)
        self.assertEqual(metadata["items"][0]["description"], "Laptop")
        self.assertEqual(metadata["items"][0]["quantity"], 1)
        self.assertEqual(Decimal(metadata["items"][0]["unit_price"]), Decimal("1000.00"))

    def test_extract_proforma_metadata_euro_currency(self):
        proforma_text = (
            "Proforma Invoice\n"
            "Vendor: European Vendor Ltd.\n"
            "Currency: EUR\n"
            "Item: Software License Qty: 5 Unit Price: 200.00\n"
            "Total Amount: €1000.00"
        )
        self.req.proforma.save("proforma_euro.pdf", ContentFile(proforma_text.encode(), name="proforma_euro.pdf"), save=True)

        metadata = extract_proforma_metadata(self.req.proforma)
        self.assertEqual(metadata["vendor"], "European Vendor Ltd.")
        self.assertEqual(metadata["currency"], "EUR")
        self.assertEqual(metadata["total_amount"], "1000.00")
        self.assertEqual(len(metadata["items"]), 1)

    def test_extract_proforma_metadata_missing_fields(self):
        proforma_text = "Incomplete proforma\nNo vendor or total mentioned."
        self.req.proforma.save("incomplete.pdf", ContentFile(proforma_text.encode(), name="incomplete.pdf"), save=True)

        metadata = extract_proforma_metadata(self.req.proforma)
        self.assertEqual(metadata["vendor"], "Unknown Vendor")
        self.assertEqual(metadata["currency"], "USD")
        self.assertEqual(metadata["total_amount"], "0")
        self.assertEqual(metadata["items"], [])
        self.assertTrue(metadata["extraction_error"])

    def test_extract_proforma_metadata_zero_amount(self):
        proforma_text = (
            "Proforma Invoice\n"
            "Vendor: Free Vendor\n"
            "Currency: USD\n"
            "Total Amount: $0.00"
        )
        self.req.proforma.save("zero.pdf", ContentFile(proforma_text.encode(), name="zero.pdf"), save=True)

        metadata = extract_proforma_metadata(self.req.proforma)
        self.assertEqual(metadata["total_amount"], "0.00")

    def test_extract_proforma_metadata_non_numeric(self):
        proforma_text = (
            "Proforma Invoice\n"
            "Vendor: Bad Vendor\n"
            "Total Amount: Free"
        )
        self.req.proforma.save("non_numeric.pdf", ContentFile(proforma_text.encode(), name="non_numeric.pdf"), save=True)

        metadata = extract_proforma_metadata(self.req.proforma)
        self.assertEqual(metadata["total_amount"], "0")

    def test_generate_purchase_order(self):
        self.req.proforma_metadata = {
            "vendor": "Test Vendor",
            "currency": "USD",
            "total_amount": "1000",
            "items": [
                {"description": "Laptop", "quantity": 1, "unit_price": "1000.00"}
            ]
        }
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()

        po_data = generate_purchase_order(self.req)
        self.assertIn("po_number", po_data)
        self.assertEqual(po_data["vendor"], "Test Vendor")
        self.assertEqual(po_data["currency"], "USD")
        self.assertEqual(po_data["total_amount"], "1000")
        self.assertEqual(len(po_data["items"]), 1)
        self.assertIsNotNone(self.req.purchase_order)
        self.assertIsNotNone(self.req.purchase_order_metadata)

    def test_validate_receipt_valid_match(self):
        self.req.proforma_metadata = {
            "vendor": "Test Vendor",
            "currency": "USD",
            "total_amount": "1000",
            "items": [
                {"description": "Laptop", "quantity": 1, "unit_price": "1000.00"}
            ]
        }
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        generate_purchase_order(self.req)

        receipt_text = (
            "Receipt\n"
            "Vendor: Test Vendor\n"
            "Item: Laptop Qty: 1 Unit Price: 1000.00\n"
            "Total: $1000.00"
        )
        receipt_file = ContentFile(receipt_text.encode(), name="receipt.pdf")
        validation = validate_receipt(receipt_file, self.req.purchase_order_metadata)
        self.assertTrue(validation["is_valid"])
        self.assertEqual(len(validation["mismatches"]), 0)

    def test_validate_receipt_vendor_mismatch(self):
        self.req.proforma_metadata = {
            "vendor": "Test Vendor",
            "currency": "USD",
            "total_amount": "1000",
            "items": []
        }
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        generate_purchase_order(self.req)

        receipt_text = "Receipt\nVendor: Wrong Vendor\nTotal: $1000.00"
        receipt_file = ContentFile(receipt_text.encode(), name="receipt.pdf")
        validation = validate_receipt(receipt_file, self.req.purchase_order_metadata)
        self.assertFalse(validation["is_valid"])
        self.assertIn("vendor", validation["mismatches"])
        self.assertEqual(validation["mismatches"]["vendor"]["expected"], "Test Vendor")
        self.assertEqual(validation["mismatches"]["vendor"]["actual"], "Wrong Vendor")

    def test_validate_receipt_amount_mismatch(self):
        self.req.proforma_metadata = {
            "vendor": "Test Vendor",
            "currency": "USD",
            "total_amount": "1000",
            "items": []
        }
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        generate_purchase_order(self.req)

        receipt_text = "Receipt\nVendor: Test Vendor\nTotal: $2000.00"
        receipt_file = ContentFile(receipt_text.encode(), name="receipt.pdf")
        validation = validate_receipt(receipt_file, self.req.purchase_order_metadata)
        self.assertFalse(validation["is_valid"])
        self.assertIn("amount", validation["mismatches"])
        self.assertEqual(validation["mismatches"]["amount"]["expected"], "1000")
        self.assertEqual(validation["mismatches"]["amount"]["actual"], "2000.00")

    def test_validate_receipt_item_mismatch(self):
        self.req.proforma_metadata = {
            "vendor": "Test Vendor",
            "currency": "USD",
            "total_amount": "1050",
            "items": [
                {"description": "Laptop", "quantity": 1, "unit_price": "1000.00"},
                {"description": "Mouse", "quantity": 2, "unit_price": "25.00"}
            ]
        }
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.save()
        generate_purchase_order(self.req)

        receipt_text = (
            "Receipt\n"
            "Vendor: Test Vendor\n"
            "Item: Keyboard Qty: 1 Unit Price: 50.00\n"
            "Total: $1050.00"
        )
        receipt_file = ContentFile(receipt_text.encode(), name="receipt.pdf")
        validation = validate_receipt(receipt_file, self.req.purchase_order_metadata)
        self.assertFalse(validation["is_valid"])
        self.assertIn("items", validation["mismatches"])
        self.assertTrue(len(validation["mismatches"]["items"]) > 0)

    def test_validate_receipt_no_po_metadata(self):
        receipt_file = ContentFile(b"Receipt data", name="receipt.pdf")
        validation = validate_receipt(receipt_file, None)
        self.assertFalse(validation["is_valid"])
        self.assertIn("reason", validation["mismatches"])

    def test_validate_receipt_no_receipt_file(self):
        validation = validate_receipt(None, {"vendor": "Test"})
        self.assertFalse(validation["is_valid"])
        self.assertIn("reason", validation["mismatches"])


class ViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            "staff",
            email="staff@example.com",
            password="pass",
            role=User.Roles.STAFF
        )
        self.approver_l1 = User.objects.create_user(
            "approver1",
            email="approver1@example.com",
            password="pass",
            role=User.Roles.APPROVER_L1
        )
        self.approver_l2 = User.objects.create_user(
            "approver2",
            email="approver2@example.com",
            password="pass",
            role=User.Roles.APPROVER_L2
        )
        self.finance = User.objects.create_user(
            "finance",
            email="finance@example.com",
            password="pass",
            role=User.Roles.FINANCE
        )
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
        self.client.force_authenticate(user=self.staff)
        response = self.client.get('/api/v1/requests/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_request(self):
        self.client.force_authenticate(user=self.staff)
        data = {
            "title": "New Request",
            "description": "New",
            "amount": "2000.00",
            "items": [
                {"description": "New Item", "quantity": 1, "unit_price": "2000.00"}
            ],
        }
        response = self.client.post('/api/v1/requests/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_approve_request_l1_only(self):
        self.client.force_authenticate(user=self.approver_l1)
        response = self.client.patch(
            f'/api/v1/requests/{self.req.pk}/approve/',
            {'comment': 'Approved L1'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.req.refresh_from_db()
        self.assertEqual(self.req.current_approval_level, 2)

    def test_approve_request_l2_only(self):
        # First approve L1
        self.req.mark_approved(self.approver_l1, {"comment": "L1"})
        self.req.refresh_from_db()
        self.assertEqual(self.req.current_approval_level, 2)

        # Now L2 can approve
        self.client.force_authenticate(user=self.approver_l2)
        response = self.client.patch(
            f'/api/v1/requests/{self.req.pk}/approve/',
            {'comment': 'Approved L2'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, PurchaseRequest.Status.APPROVED)

    def test_permission_denied_non_approver(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            f'/api/v1/requests/{self.req.pk}/approve/',
            {'comment': 'Try approve'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_denied_wrong_level_approver(self):
        # L2 trying to approve at L1
        self.client.force_authenticate(user=self.approver_l2)
        response = self.client.patch(
            f'/api/v1/requests/{self.req.pk}/approve/',
            {'comment': 'Wrong level'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reject_request_any_level(self):
        self.client.force_authenticate(user=self.approver_l1)
        response = self.client.patch(
            f'/api/v1/requests/{self.req.pk}/reject/',
            {'reason': 'Rejected'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, PurchaseRequest.Status.REJECTED)

    def test_unauthenticated_access(self):
        response = self.client.get('/api/v1/requests/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_finance_can_access_approved_requests(self):
        # Approve request
        self.req.mark_approved(self.approver_l1, {"comment": "L1"})
        self.req.mark_approved(self.approver_l2, {"comment": "L2"})
        self.req.refresh_from_db()

        self.client.force_authenticate(user=self.finance)
        response = self.client.get(f'/api/v1/requests/{self.req.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_receipt_submission(self):
        self.client.force_authenticate(user=self.staff)
        # Simulate approval
        self.req.status = PurchaseRequest.Status.APPROVED
        self.req.purchase_order_metadata = {
            "vendor": "Test",
            "total_amount": "1000"
        }
        self.req.save()

        receipt_file = ContentFile(b"Receipt data", name="receipt.pdf")
        data = {'receipt': receipt_file}
        response = self.client.post(
            f'/api/v1/requests/{self.req.pk}/submit-receipt/',
            data,
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_receipt_submission_unapproved_request(self):
        self.client.force_authenticate(user=self.staff)
        receipt_file = ContentFile(b"Receipt data", name="receipt.pdf")
        data = {'receipt': receipt_file}
        response = self.client.post(
            f'/api/v1/requests/{self.req.pk}/submit-receipt/',
            data,
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
