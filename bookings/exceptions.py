class BookingError(Exception):
    """Base exception for booking-related errors."""
    pass


class BookingConflictError(BookingError):
    """Raised when a booking conflicts with existing bookings."""
    pass


class PaymentError(Exception):
    """Base exception for payment-related errors."""
    pass