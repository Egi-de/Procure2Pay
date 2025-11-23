from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
import logging

logger = logging.getLogger(__name__)

def send_approval_notification(request_obj, approver):
    """Send approval notification to the requester."""
    try:
        subject = f'Purchase Request {request_obj.id} Approved'
        html_content = render_to_string('requests/approval_notification.html', {
            'request': request_obj,
            'approver': approver,
        })
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, [request_obj.requester.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Approval email sent for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")

def send_rejection_notification(request_obj, rejector):
    """Send rejection notification to the requester."""
    try:
        subject = f'Purchase Request {request_obj.id} Rejected'
        html_content = render_to_string('requests/rejection_notification.html', {
            'request': request_obj,
            'rejector': rejector,
        })
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, [request_obj.requester.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Rejection email sent for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send rejection email: {e}")

def send_receipt_submitted_notification(request_obj, user):
    """Send notification when receipt is submitted."""
    try:
        subject = f'Receipt Submitted for Purchase Request {request_obj.id}'
        message = f"""
        Dear Finance Team,

        A receipt has been submitted for the purchase request {request_obj.id}.

        Submitted by: {user.get_full_name() or user.username}

        Request Details:
        - ID: {request_obj.id}
        - Amount: {request_obj.amount}
        - Status: {request_obj.status}
        - Vendor: {request_obj.proforma_metadata.get('vendor', 'Unknown') if request_obj.proforma_metadata else 'Unknown'}

        Please review the receipt.

        Best regards,
        Procure2Pay System
        """
        # Assuming finance emails are in settings or default
        finance_emails = getattr(settings, 'FINANCE_EMAILS', ['finance@example.com'])
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            finance_emails,
            fail_silently=False,
        )
        logger.info(f"Receipt submitted notification sent for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send receipt submitted notification: {e}")
