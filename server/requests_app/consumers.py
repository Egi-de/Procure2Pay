import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications."""

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = None
        self.user_group_name = None
        self.role_group_name = None

        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        token = None
        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=')[1]
                break

        if not token:
            logger.warning("WebSocket connection rejected: No token provided")
            await self.close()
            return

        # Validate token and get user
        self.user = await self.get_user_from_token(token)
        if not self.user:
            logger.warning("WebSocket connection rejected: Invalid token")
            await self.close()
            return

        # Create user-specific group
        self.user_group_name = f"user_{self.user.id}"
        
        # Create role-specific group for approvers
        self.role_group_name = f"role_{self.user.role}"

        # Join user-specific group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Join role-specific group
        await self.channel_layer.group_add(
            self.role_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for user {self.user.username} (role: {self.user.role})")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        if self.role_group_name:
            await self.channel_layer.group_discard(
                self.role_group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for user {self.user.username if self.user else 'unknown'}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            elif message_type == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket")

    async def notification_message(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    @database_sync_to_async
    def get_user_from_token(self, token):
        """Validate JWT token and return user."""
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist) as e:
            logger.error(f"Token validation failed: {e}")
            return None

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        from .models import Notification
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            pass