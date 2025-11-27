from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


def send_websocket_notification(user_id, notification_data):
    """Send a notification via WebSocket to a specific user."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "notification_message",
                    "notification": notification_data
                }
            )
            logger.info(f"WebSocket notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")


def send_websocket_notification_to_role(role, notification_data):
    """Send a notification via WebSocket to all users with a specific role."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"role_{role}",
                {
                    "type": "notification_message",
                    "notification": notification_data
                }
            )
            logger.info(f"WebSocket notification sent to role {role}")
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification to role: {e}")


def create_notification_for_user(user, message, request_obj=None):
    """Create an in-app notification for a user and send via WebSocket."""
    from .models import Notification
    
    notification = Notification.objects.create(
        user=user,
        message=message,
        related_request=request_obj
    )
    
    # Send via WebSocket
    notification_data = {
        'id': notification.id,
        'message': notification.message,
        'timestamp': notification.timestamp.isoformat(),
        'is_read': notification.is_read,
        'related_request_id': str(request_obj.id) if request_obj else None,
        'related_request_title': request_obj.title if request_obj else None,
    }
    send_websocket_notification(user.id, notification_data)
    
    return notification


def create_notifications_for_role(role, message, request_obj=None, exclude_user=None):
    """Create in-app notifications for all users with a specific role."""
    from home.models import User
    from .models import Notification
    
    users = User.objects.filter(role=role)
    if exclude_user:
        users = users.exclude(id=exclude_user.id)
    
    notifications = []
    for user in users:
        notification = Notification.objects.create(
            user=user,
            message=message,
            related_request=request_obj
        )
        notifications.append(notification)
        
        # Send via WebSocket
        notification_data = {
            'id': notification.id,
            'message': notification.message,
            'timestamp': notification.timestamp.isoformat(),
            'is_read': notification.is_read,
            'related_request_id': str(request_obj.id) if request_obj else None,
            'related_request_title': request_obj.title if request_obj else None,
        }
        send_websocket_notification(user.id, notification_data)
    
    logger.info(f"Created {len(notifications)} notifications for role {role}")
    return notifications


def notify_approvers_new_request(request_obj):
    """Notify ALL approvers (L1 and L2) when a new request is created."""
    from home.models import User
    
    message = f"New purchase request '{request_obj.title}' requires approval. Amount: {request_obj.amount}"
    
    # Notify ALL approvers (both L1 and L2) in real-time
    approver_roles = [User.Roles.APPROVER_L1, User.Roles.APPROVER_L2]
    
    for role in approver_roles:
        create_notifications_for_role(role, message, request_obj)
    
    # Send email notification to all approvers
    send_approval_request_notification_to_all(request_obj)


def notify_request_approved(request_obj, approver):
    """Notify ALL users (approvers, staff, finance) when a request is approved."""
    from home.models import User
    
    approver_name = approver.get_full_name() or approver.username
    
    # Determine approval status message
    if request_obj.status == request_obj.Status.APPROVED:
        status_text = "fully approved"
        staff_message = f"Your purchase request '{request_obj.title}' has been fully approved by {approver_name}."
    else:
        current_level = request_obj.current_approval_level - 1
        status_text = f"approved at level {current_level}"
        staff_message = f"Your purchase request '{request_obj.title}' has been approved at level {current_level} by {approver_name}. Awaiting next level approval."
    
    # 1. Notify the request creator (staff)
    create_notification_for_user(request_obj.created_by, staff_message, request_obj)
    
    # 2. Notify ALL approvers (both L1 and L2)
    approver_message = f"Purchase request '{request_obj.title}' has been {status_text} by {approver_name}. Amount: {request_obj.amount}"
    for role in [User.Roles.APPROVER_L1, User.Roles.APPROVER_L2]:
        create_notifications_for_role(role, approver_message, request_obj, exclude_user=approver)
    
    # 3. Notify Finance team
    finance_message = f"Purchase request '{request_obj.title}' has been {status_text} by {approver_name}. Amount: {request_obj.amount}"
    create_notifications_for_role(User.Roles.FINANCE, finance_message, request_obj)
    
    # Send email notifications
    if request_obj.status == request_obj.Status.APPROVED:
        # Send email to finance when fully approved
        notify_finance_request_approved_email(request_obj)
    
    # Send email to all approvers about the status change
    send_approval_status_email_to_all(request_obj, approver, status_text)


def notify_request_rejected(request_obj, rejector, reason=""):
    """Notify ALL users (approvers, staff, finance) when a request is rejected."""
    from home.models import User
    
    rejector_name = rejector.get_full_name() or rejector.username
    reason_text = f" Reason: {reason}" if reason else ""
    
    # 1. Notify the request creator (staff)
    staff_message = f"Your purchase request '{request_obj.title}' has been rejected by {rejector_name}.{reason_text}"
    create_notification_for_user(request_obj.created_by, staff_message, request_obj)
    
    # 2. Notify ALL approvers (both L1 and L2)
    approver_message = f"Purchase request '{request_obj.title}' has been rejected by {rejector_name}.{reason_text} Amount: {request_obj.amount}"
    for role in [User.Roles.APPROVER_L1, User.Roles.APPROVER_L2]:
        create_notifications_for_role(role, approver_message, request_obj, exclude_user=rejector)
    
    # 3. Notify Finance team
    finance_message = f"Purchase request '{request_obj.title}' has been rejected by {rejector_name}.{reason_text} Amount: {request_obj.amount}"
    create_notifications_for_role(User.Roles.FINANCE, finance_message, request_obj)


def send_approval_notification(request_obj, approver):
    """Send approval notification to the requester."""
    if not request_obj.created_by.email:
        logger.warning(f"No email for requester {request_obj.created_by.username}, skipping approval notification")
        return
    try:
        subject = f'Purchase Request {request_obj.id} Approved'
        html_content = render_to_string('requests/approval_notification.html', {
            'request': request_obj,
            'approver': approver,
        })
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, [request_obj.created_by.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Approval email sent for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")


def send_rejection_notification(request_obj, rejector):
    """Send rejection notification to the requester."""
    if not request_obj.created_by.email:
        logger.warning(f"No email for requester {request_obj.created_by.username}, skipping rejection notification")
        return
    # Get the approval step for the rejection to fetch reason
    from .models import ApprovalStep
    approval_step = ApprovalStep.objects.filter(
        request=request_obj,
        level=request_obj.current_approval_level,
        decision=ApprovalStep.Decision.REJECTED
    ).first()
    reason = approval_step.metadata.get('reason', '') if approval_step else ''
    try:
        subject = f'Purchase Request {request_obj.id} Rejected'
        html_content = render_to_string('requests/rejection_notification.html', {
            'request': request_obj,
            'rejector': rejector,
            'reason': reason,
        })
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, [request_obj.created_by.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Rejection email sent for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send rejection email: {e}")


def send_approval_request_notification(request_obj):
    """Send approval request notification to the next approver(s)."""
    from home.models import User
    next_role = request_obj.next_required_role
    if not next_role:
        logger.warning(f"No next role for request {request_obj.id}")
        return
    approvers = User.objects.filter(role=next_role)
    if not approvers.exists():
        logger.warning(f"No approvers found for role {next_role}")
        return
    try:
        subject = f'New Approval Request: {request_obj.title}'
        html_content = render_to_string('requests/approval_notification.html', {
            'request': request_obj,
            'approver': None,  # No specific approver yet
        })
        emails = [approver.email for approver in approvers if approver.email]
        if not emails:
            logger.warning(f"No emails found for approvers of role {next_role}")
            return
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, emails)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Approval request email sent to {len(emails)} approvers for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send approval request email: {e}")


def send_approval_request_notification_to_all(request_obj):
    """Send approval request notification to ALL approvers (L1 and L2)."""
    from home.models import User
    
    # Get all approvers (both L1 and L2)
    approvers = User.objects.filter(role__in=[User.Roles.APPROVER_L1, User.Roles.APPROVER_L2])
    if not approvers.exists():
        logger.warning(f"No approvers found for request {request_obj.id}")
        return
    
    try:
        subject = f'New Approval Request: {request_obj.title}'
        html_content = render_to_string('requests/approval_notification.html', {
            'request': request_obj,
            'approver': None,  # No specific approver yet
        })
        emails = [approver.email for approver in approvers if approver.email]
        if not emails:
            logger.warning(f"No emails found for any approvers")
            return
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, emails)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Approval request email sent to {len(emails)} approvers (L1 and L2) for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send approval request email to all approvers: {e}")


def notify_finance_request_approved_email(request_obj):
    """Send email notification to finance team when a request is fully approved."""
    from home.models import User
    
    finance_users = User.objects.filter(role=User.Roles.FINANCE)
    if not finance_users.exists():
        logger.warning(f"No finance users found for request {request_obj.id}")
        return
    
    try:
        subject = f'Purchase Request Fully Approved: {request_obj.title}'
        html_content = render_to_string('requests/approval_notification.html', {
            'request': request_obj,
            'approver': request_obj.approved_by,
        })
        emails = [user.email for user in finance_users if user.email]
        if not emails:
            logger.warning(f"No emails found for finance users")
            return
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, emails)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Finance approval email sent to {len(emails)} users for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send finance approval email: {e}")


def send_approval_status_email_to_all(request_obj, approver, status_text):
    """Send approval status email to approvers and finance (excluding staff who gets a separate email)."""
    from home.models import User
    
    # Collect all emails (excluding staff who already receives a dedicated approval email)
    all_emails = []
    
    # All approvers (L1 and L2), excluding the one who made the action
    approvers = User.objects.filter(role__in=[User.Roles.APPROVER_L1, User.Roles.APPROVER_L2]).exclude(id=approver.id)
    all_emails.extend([u.email for u in approvers if u.email])
    
    # Finance users
    finance_users = User.objects.filter(role=User.Roles.FINANCE)
    all_emails.extend([u.email for u in finance_users if u.email])
    
    # Remove duplicates
    all_emails = list(set(all_emails))
    
    if not all_emails:
        logger.warning(f"No emails found for approval status notification on request {request_obj.id}")
        return
    
    try:
        approver_name = approver.get_full_name() or approver.username
        subject = f'Purchase Request {status_text.title()}: {request_obj.title}'
        html_content = render_to_string('requests/approval_notification.html', {
            'request': request_obj,
            'approver': approver,
        })
        msg = EmailMultiAlternatives(subject, html_content, settings.DEFAULT_FROM_EMAIL, all_emails)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info(f"Approval status email sent to {len(all_emails)} users for request {request_obj.id}")
    except Exception as e:
        logger.error(f"Failed to send approval status email: {e}")


def notify_finance_request_approved(request_obj):
    """Notify finance team when a request is fully approved (legacy function for compatibility)."""
    from home.models import User
    
    # Create in-app notifications for all finance users
    message = f"Purchase request '{request_obj.title}' has been fully approved and is ready for processing. Amount: {request_obj.amount}"
    create_notifications_for_role(User.Roles.FINANCE, message, request_obj)
    
    # Send email notification to finance users
    notify_finance_request_approved_email(request_obj)


def send_receipt_submitted_notification(request_obj, user):
    """Send notification when receipt is submitted."""
    from home.models import User
    
    # Create in-app notifications for all finance users
    message = f"Receipt submitted for purchase request '{request_obj.title}'. Please review."
    create_notifications_for_role(User.Roles.FINANCE, message, request_obj)
    
    # Get finance users from database
    finance_users = User.objects.filter(role=User.Roles.FINANCE)
    finance_emails = [u.email for u in finance_users if u.email]
    
    # Fallback to settings if no finance users in database
    if not finance_emails:
        finance_emails = getattr(settings, 'FINANCE_EMAILS', [])
        if not finance_emails:
            logger.warning(f"No finance emails found for receipt notification on request {request_obj.id}")
            return
    
    try:
        subject = f'Receipt Submitted for Purchase Request {request_obj.id}'
        message_text = f"""
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
        send_mail(
            subject,
            message_text,
            settings.DEFAULT_FROM_EMAIL,
            finance_emails,
            fail_silently=False,
        )
        logger.info(f"Receipt submitted notification sent for request {request_obj.id} to {len(finance_emails)} finance users")
    except Exception as e:
        logger.error(f"Failed to send receipt submitted notification: {e}")
