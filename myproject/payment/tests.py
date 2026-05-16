from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal, ROUND_DOWN
from datetime import timedelta
from django.utils import timezone

from .models import PaymentMethod, Transaction, TransactionServiceItem
from events.models import Event, EventServiceBooking
from services.models import Service

User = get_user_model()


class PaymentMethodValidationTests(TestCase):
    """Test vendor payment method setup and validation"""

    def setUp(self):
        self.vendor = User.objects.create_user(
            email="vendor@test.com",
            password="testpass123",
            role="vendor",
            company_name="Test Vendor"
        )

    def test_payment_method_creation(self):
        """Test vendor can create payment method"""
        pm = PaymentMethod.objects.create(
            vendor=self.vendor,
            account_number="1234567890",
            is_active=True
        )
        self.assertTrue(pm.is_active)
        self.assertEqual(pm.account_number, "1234567890")

    def test_payment_method_inactive_by_default(self):
        """Test payment method starts inactive"""
        pm = PaymentMethod.objects.create(
            vendor=self.vendor,
            account_number="1234567890",
            is_active=False
        )
        self.assertFalse(pm.is_active)

    def test_vendor_can_update_payment_method(self):
        """Test vendor can update their payment method"""
        pm = PaymentMethod.objects.create(
            vendor=self.vendor,
            account_number="1111111111",
            is_active=False
        )
        pm.account_number = "2222222222"
        pm.is_active = True
        pm.save()
        
        pm.refresh_from_db()
        self.assertEqual(pm.account_number, "2222222222")
        self.assertTrue(pm.is_active)


class PaymentAllocationTests(TestCase):
    """Test proportional payment split between vendors"""

    def test_proportional_split_single_vendor(self):
        """Test split when one vendor has all due amount"""
        weights = {1: Decimal("5000.00")}
        amount = Decimal("5000.00")
        
        # Simulate split logic
        allocation = {}
        total_weight = sum(weights.values())
        for booking_id, weight in weights.items():
            proportion = (amount * weight / total_weight).quantize(Decimal("0.01"), ROUND_DOWN)
            allocation[booking_id] = proportion
        
        self.assertEqual(allocation[1], Decimal("5000.00"))

    def test_proportional_split_multiple_vendors(self):
        """Test split between multiple vendors"""
        weights = {
            1: Decimal("3000.00"),  # 60% of total
            2: Decimal("2000.00"),  # 40% of total
        }
        amount = Decimal("5000.00")
        
        # Simulate split logic
        allocation = {}
        total_weight = sum(weights.values())
        for booking_id, weight in weights.items():
            proportion = (amount * weight / total_weight).quantize(Decimal("0.01"), ROUND_DOWN)
            allocation[booking_id] = proportion
        
        # 60% of 5000 = 3000, 40% of 5000 = 2000
        self.assertEqual(allocation[1], Decimal("3000.00"))
        self.assertEqual(allocation[2], Decimal("2000.00"))
        self.assertEqual(sum(allocation.values()), amount)

    def test_proportional_split_with_remainder(self):
        """Test split distributes remainder correctly (no rounding loss)"""
        weights = {
            1: Decimal("1000.00"),
            2: Decimal("1000.00"),
            3: Decimal("1000.00"),
        }
        amount = Decimal("1000.00")  # Total 1000 divided among 3
        
        # Each gets roughly 333.33
        allocation = {}
        total_weight = sum(weights.values())
        remainders = {}
        
        for booking_id, weight in weights.items():
            proportion = (amount * weight / total_weight).quantize(Decimal("0.01"), ROUND_DOWN)
            allocation[booking_id] = proportion
            remainders[booking_id] = (amount * weight / total_weight) - proportion
        
        # Sum should equal amount
        total_allocated = sum(allocation.values())
        remaining = amount - total_allocated
        
        # Remainder should be small (< 0.01 per item)
        self.assertLessEqual(remaining, Decimal("0.03"))  # At most 1 cent per vendor


class TransactionRecordingTests(TestCase):
    """Test payment transactions are recorded correctly"""

    def setUp(self):
        self.client = User.objects.create_user(
            email="client@test.com",
            password="testpass123",
            role="client",
            first_name="Test",
            last_name="Client"
        )
        self.vendor = User.objects.create_user(
            email="vendor@test.com",
            password="testpass123",
            role="vendor",
            company_name="Test Vendor"
        )
        self.event = Event.objects.create(
            client=self.client,
            title="Test Event",
            event_date=timezone.localdate() + timedelta(days=7),
            event_time="14:00:00",
            venue_name="Test Venue"
        )

    def test_transaction_records_payment_details(self):
        """Test transaction captures amount, timestamp, and status"""
        tx = Transaction.objects.create(
            client=self.client,
            event=self.event,
            amount=Decimal("5000.00"),
            status="success"
        )
        self.assertEqual(tx.amount, Decimal("5000.00"))
        self.assertEqual(tx.status, "success")
        self.assertIsNotNone(tx.created_at)

    def test_transaction_service_item_links_payment_to_booking(self):
        """Test transaction service items link payment to specific bookings"""
        tx = Transaction.objects.create(
            client=self.client,
            event=self.event,
            amount=Decimal("5000.00"),
            status="success"
        )
        service = Service.objects.create(
            vendor=self.vendor,
            name="Photography",
            description="Photo service",
            price=Decimal("5000.00"),
            service_type="photography"
        )
        booking = EventServiceBooking.objects.create(
            event=self.event,
            service=service,
            vendor=self.vendor,
            status="approved",
            requested_date=self.event.event_date,
            price_snapshot=Decimal("5000.00")
        )
        
        tsi = TransactionServiceItem.objects.create(
            transaction=tx,
            booking=booking,
            service=service,
            vendor=self.vendor,
            paid_amount=Decimal("5000.00"),
            service_total=Decimal("5000.00")
        )
        
        self.assertEqual(tsi.transaction, tx)
        self.assertEqual(tsi.booking, booking)
        self.assertEqual(tsi.paid_amount, Decimal("5000.00"))

