# Create your tests here.
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import timedelta, time
from django.utils import timezone

from .models import Event, EventServiceBooking
from services.models import Service

User = get_user_model()


class EventModelTests(TestCase):
    """Test Event model functionality"""

    def setUp(self):
        """Set up test data"""
        self.client_user = User.objects.create_user(
            email="client@test.com",
            password="testpass123",
            role="client",
            first_name="Test",
            last_name="Client"
        )

    def test_event_creation(self):
        """Test that events can be created with required fields"""
        event = Event.objects.create(
            client=self.client_user,
            title="Test Event",
            event_date=timezone.localdate() + timedelta(days=7),
            event_time=time(14, 0),
            venue_name="Test Venue"
        )
        self.assertEqual(event.title, "Test Event")
        self.assertIsNone(event.completed_at)

    def test_event_stores_timestamps(self):
        """Test that created_at and updated_at are set"""
        event = Event.objects.create(
            client=self.client_user,
            title="Test Event",
            event_date=timezone.localdate() + timedelta(days=7),
            event_time=time(14, 0),
            venue_name="Test Venue"
        )
        self.assertIsNotNone(event.created_at)
        self.assertIsNotNone(event.updated_at)

    def test_event_can_be_marked_complete(self):
        """Test that event can be marked as completed"""
        event = Event.objects.create(
            client=self.client_user,
            title="Test Event",
            event_date=timezone.localdate() + timedelta(days=7),
            event_time=time(14, 0),
            venue_name="Test Venue"
        )
        event.completed_at = timezone.now()
        event.save()
        
        event.refresh_from_db()
        self.assertIsNotNone(event.completed_at)


class EventServiceBookingTests(TestCase):
    """Test EventServiceBooking model and booking lifecycle"""

    def setUp(self):
        """Set up test data"""
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
        self.event = Event.objects.create(
            client=self.client_user,
            title="Test Event",
            event_date=timezone.localdate() + timedelta(days=7),
            event_time=time(14, 0),
            venue_name="Test Venue"
        )
        self.service = Service.objects.create(
            vendor=self.vendor_user,
            name="Photography",
            description="Photo service",
            price=Decimal("5000.00"),
            service_type="photography"
        )

    def test_booking_creation_with_pending_status(self):
        """Test that new booking starts in pending status"""
        booking = EventServiceBooking.objects.create(
            event=self.event,
            service=self.service,
            vendor=self.vendor_user,
            status="pending",
            requested_date=self.event.event_date,
            price_snapshot=Decimal("5000.00")
        )
        self.assertEqual(booking.status, "pending")
        self.assertIsNone(booking.responded_at)

    def test_booking_can_transition_to_approved(self):
        """Test booking can move from pending to approved"""
        booking = EventServiceBooking.objects.create(
            event=self.event,
            service=self.service,
            vendor=self.vendor_user,
            status="pending",
            requested_date=self.event.event_date,
            price_snapshot=Decimal("5000.00")
        )
        booking.status = "approved"
        booking.responded_at = timezone.now()
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, "approved")
        self.assertIsNotNone(booking.responded_at)

    def test_booking_can_transition_to_rejected(self):
        """Test booking can move from pending to rejected"""
        booking = EventServiceBooking.objects.create(
            event=self.event,
            service=self.service,
            vendor=self.vendor_user,
            status="pending",
            requested_date=self.event.event_date,
            price_snapshot=Decimal("5000.00")
        )
        booking.status = "rejected"
        booking.responded_at = timezone.now()
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, "rejected")
        self.assertIsNotNone(booking.responded_at)

    def test_booking_stores_price_snapshot(self):
        """Test that booking captures price at time of request"""
        booking = EventServiceBooking.objects.create(
            event=self.event,
            service=self.service,
            vendor=self.vendor_user,
            status="pending",
            requested_date=self.event.event_date,
            price_snapshot=Decimal("5000.00")
        )
        self.assertEqual(booking.price_snapshot, Decimal("5000.00"))

    def test_booking_can_store_quoted_price(self):
        """Test that vendor can provide a quoted price different from snapshot"""
        booking = EventServiceBooking.objects.create(
            event=self.event,
            service=self.service,
            vendor=self.vendor_user,
            status="quoted",
            requested_date=self.event.event_date,
            price_snapshot=Decimal("5000.00"),
            quoted_price=Decimal("4500.00")
        )
        self.assertEqual(booking.quoted_price, Decimal("4500.00"))


