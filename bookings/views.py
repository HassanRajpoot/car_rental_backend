import os
from decimal import Decimal
from datetime import timedelta

import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Booking
from .serializers import BookingSerializer
from .services import BookingService, PaymentService
from cars.models import Car

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing car bookings.
    Handles CRUD operations with appropriate permissions.
    """
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter bookings based on user role."""
        user = self.request.user
        if hasattr(user, 'is_fleet') and user.is_fleet() or hasattr(user, 'is_admin') and user.is_admin():
            return Booking.objects.all()
        return Booking.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        """Create a new booking in PENDING state."""
        try:
            booking_data = self._validate_booking_data(request.data)
            booking = BookingService.create_booking(
                user=request.user,
                car_id=booking_data['car_id'],
                start=booking_data['start'],
                end=booking_data['end']
            )
            serializer = self.get_serializer(booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except BookingService.BookingConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an existing booking."""
        booking = self.get_object()
        try:
            BookingService.cancel_booking(booking)
            return Response({"detail": "Booking cancelled successfully"})
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _validate_booking_data(self, data):
        """Validate and parse booking creation data."""
        car_id = data.get("car")
        start = data.get("start")
        end = data.get("end")
        
        if not all([car_id, start, end]):
            raise ValueError("car, start, and end are required fields")
        
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
        
        if not start_dt or not end_dt:
            raise ValueError("Invalid datetime format for start or end")
        
        if start_dt >= end_dt:
            raise ValueError("Start date must be before end date")
        
        return {
            'car_id': car_id,
            'start': start_dt,
            'end': end_dt
        }


class CreatePaymentIntentView(APIView):
    """Handle Stripe payment intent creation for bookings."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response(
                {"detail": "booking_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
            payment_data = PaymentService.create_payment_intent(booking)
            return Response(payment_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    try:
        event = PaymentService.verify_webhook(request)
        PaymentService.handle_webhook_event(event)
        return HttpResponse(status=200)
    except Exception:
        return HttpResponse(status=400)
