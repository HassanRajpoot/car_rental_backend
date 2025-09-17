import os
from decimal import Decimal
from django.utils.dateparse import parse_datetime
import stripe
from .models import Booking
from cars.models import Car

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


class BookingService:
    """Service class for booking-related business logic."""
    
    class BookingConflictError(Exception):
        """Raised when booking conflicts with existing bookings."""
        pass

    @classmethod
    def create_booking(cls, user, car_id, start, end):
        """
        Create a new booking after validating availability.
        
        Args:
            user: The user making the booking
            car_id: ID of the car to book
            start: Start datetime
            end: End datetime
            
        Returns:
            Booking instance
            
        Raises:
            BookingConflictError: If car is not available
            ValueError: If car doesn't exist
        """
        try:
            car = Car.objects.get(pk=car_id)
        except Car.DoesNotExist:
            raise ValueError("Car not found")
        
        # Check for conflicts
        if not cls._is_car_available(car, start, end):
            raise cls.BookingConflictError("Car not available for selected dates")
        
        # Calculate total price
        total_price = cls._calculate_total_price(car, start, end)
        
        return Booking.objects.create(
            user=user,
            car=car,
            start=start,
            end=end,
            total_price=total_price,
            status="pending"
        )

    @classmethod
    def cancel_booking(cls, booking):
        """
        Cancel a booking if it's in a cancellable state.
        
        Args:
            booking: Booking instance to cancel
            
        Raises:
            ValueError: If booking cannot be cancelled
        """
        if booking.status not in ["pending", "confirmed"]:
            raise ValueError("Cannot cancel booking in current status")
        
        booking.status = "cancelled"
        booking.save()

    @classmethod
    def _is_car_available(cls, car, start, end):
        """Check if car is available for the given time period."""
        conflicting_bookings = Booking.objects.filter(
            car=car,
            status__in=["pending", "confirmed"]
        )
        
        for booking in conflicting_bookings:
            # Check for overlap: not (booking ends before start OR booking starts after end)
            if not (booking.end <= start or booking.start >= end):
                return False
        return True

    @classmethod
    def _calculate_total_price(cls, car, start, end):
        """Calculate total price for booking period."""
        duration = end - start
        days = max(duration.days, 1)  # Minimum 1 day
        return Decimal(days) * car.price_per_day


class PaymentService:
    """Service class for payment-related operations."""
    
    @classmethod
    def create_payment_intent(cls, booking):
        """
        Create a Stripe payment intent for a booking.
        
        Args:
            booking: Booking instance
            
        Returns:
            dict: Payment intent data
            
        Raises:
            ValueError: If booking is not in pending state
        """
        if booking.status != "pending":
            raise ValueError("Booking is not in pending state")
        
        intent = stripe.PaymentIntent.create(
            amount=int(booking.total_price * 100),  # Convert to cents
            currency="usd",
            metadata={"booking_id": str(booking.id)},
        )
        
        # Save payment intent ID for webhook reconciliation
        booking.stripe_payment_intent = intent["id"]
        booking.save()
        
        return {
            "client_secret": intent["client_secret"],
            "intent_id": intent["id"]
        }

    @classmethod
    def verify_webhook(cls, request):
        """Verify and parse Stripe webhook."""
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        return stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

    @classmethod
    def handle_webhook_event(cls, event):
        """Handle different types of webhook events."""
        if event["type"] == "payment_intent.succeeded":
            cls._handle_payment_success(event["data"]["object"])

    @classmethod
    def _handle_payment_success(cls, payment_intent):
        """Handle successful payment."""
        booking_id = payment_intent["metadata"].get("booking_id")
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                booking.status = "confirmed"
                booking.save()
            except Booking.DoesNotExist:
                # Log this error in production
                pass