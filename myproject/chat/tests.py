# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import Conversation, Message

User = get_user_model()


class ChatMessageTests(TestCase):
    """Test chat messaging between clients and vendors"""

    def setUp(self):
        self.client_user = User.objects.create_user(
            email="client@test.com",
            password="testpass123",
            role="client",
            first_name="Test",
            last_name="Client"
        )
        self.vendor_user = User.objects.create_user(
            email="vendor@test.com",
            password="testpass123",
            role="vendor",
            company_name="Test Vendor"
        )

    def test_conversation_creation_between_client_and_vendor(self):
        """Test conversation can be created between client and vendor"""
        conv = Conversation.objects.create(
            client=self.client_user,
            vendor=self.vendor_user
        )
        self.assertEqual(conv.client, self.client_user)
        self.assertEqual(conv.vendor, self.vendor_user)

    def test_message_creation_in_conversation(self):
        """Test messages can be created in a conversation"""
        conv = Conversation.objects.create(
            client=self.client_user,
            vendor=self.vendor_user
        )
        msg = Message.objects.create(
            conversation=conv,
            sender=self.client_user,
            content="Hello, are you available?"
        )
        self.assertEqual(msg.content, "Hello, are you available?")
        self.assertEqual(msg.sender, self.client_user)
        self.assertIsNotNone(msg.created_at)

    def test_system_message_creation(self):
        """Test system messages can be created (e.g., booking decisions)"""
        conv = Conversation.objects.create(
            client=self.client_user,
            vendor=self.vendor_user
        )
        sys_msg = Message.objects.create(
            conversation=conv,
            is_system=True,
            content="System: Booking was approved."
        )
        self.assertTrue(sys_msg.is_system)
        self.assertIsNone(sys_msg.sender)

    def test_conversation_retrieves_message_history(self):
        """Test conversation can retrieve all messages in order"""
        conv = Conversation.objects.create(
            client=self.client_user,
            vendor=self.vendor_user
        )
        msg1 = Message.objects.create(
            conversation=conv,
            sender=self.client_user,
            content="First message"
        )
        msg2 = Message.objects.create(
            conversation=conv,
            sender=self.vendor_user,
            content="Reply message"
        )
        
        messages = conv.messages.all().order_by('created_at')
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].content, "First message")
        self.assertEqual(messages[1].content, "Reply message")

