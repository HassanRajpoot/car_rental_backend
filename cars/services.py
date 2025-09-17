from django.db.models import Q, Avg, Count
from django.utils import timezone
from .models import Car, CarReview
from bookings.models import Booking

class CarService:
    """Service class for car-related business logic."""
    
    @classmethod
    def get_available_cars(cls, location=None, start_date=None, end_date=None):
        """
        Get cars available for booking in a specific location and time period.
        
        Args:
            location: Optional location filter
            start_date: Start date for availability check
            end_date: End date for availability check
            
        Returns:
            QuerySet of available cars
        """
        queryset = Car.objects.available().filter(is_active=True)
        
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if start_date and end_date:
            # Exclude cars with conflicting bookings
            conflicting_bookings = Booking.objects.filter(
                status__in=['pending', 'confirmed'],
                start__lt=end_date,
                end__gt=start_date
            ).values_list('car_id', flat=True)
            
            queryset = queryset.exclude(id__in=conflicting_bookings)
        
        return queryset.select_related('owner').prefetch_related('images', 'reviews')
    
    @classmethod
    def search_cars(cls, query):
        """
        Search cars by name, make, model, or description.
        
        Args:
            query: Search query string
            
        Returns:
            QuerySet of matching cars
        """
        return Car.objects.available().filter(
            Q(name__icontains=query) |
            Q(make__icontains=query) |
            Q(model__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        ).distinct()
    
    @classmethod
    def get_cars_with_stats(cls):
        """
        Get cars with aggregated statistics.
        
        Returns:
            QuerySet with annotations for ratings and booking counts
        """
        return Car.objects.available().annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
            booking_count=Count('bookings', filter=Q(bookings__status='completed'))
        )
    
    @classmethod
    def get_popular_cars(cls, limit=10):
        """
        Get most popular cars based on bookings and ratings.
        
        Args:
            limit: Number of cars to return
            
        Returns:
            QuerySet of popular cars
        """
        return cls.get_cars_with_stats().filter(
            avg_rating__gte=4.0,
            booking_count__gte=5
        ).order_by('-avg_rating', '-booking_count')[:limit]
    
    @classmethod
    def update_car_status_after_booking(cls, car, booking_status):
        """
        Update car status based on booking status changes.
        
        Args:
            car: Car instance
            booking_status: New booking status
        """
        if booking_status == 'confirmed':
            car.status = 'rented'
            car.save()
        elif booking_status in ['cancelled', 'completed']:
            # Check if there are other active bookings
            active_bookings = Booking.objects.filter(
                car=car,
                status__in=['pending', 'confirmed'],
                start__lte=timezone.now(),
                end__gte=timezone.now()
            ).exists()
            
            if not active_bookings:
                car.status = 'available'
                car.save()


class CarReviewService:
    """Service class for car review operations."""
    
    @classmethod
    def can_user_review_car(cls, user, car, booking=None):
        """
        Check if user can review a car.
        
        Args:
            user: User instance
            car: Car instance
            booking: Optional booking instance
            
        Returns:
            bool: Whether user can review the car
        """
        if booking:
            return (booking.user == user and 
                   booking.car == car and 
                   booking.status == 'completed')
        
        # Check if user has completed bookings for this car
        return Booking.objects.filter(
            user=user,
            car=car,
            status='completed'
        ).exists()
    
    @classmethod
    def create_review(cls, user, car, rating, title, comment, booking=None):
        """
        Create a new car review.
        
        Args:
            user: User instance
            car: Car instance
            rating: Rating (1-5)
            title: Review title
            comment: Review comment
            booking: Optional booking instance
            
        Returns:
            CarReview instance
            
        Raises:
            ValueError: If user cannot review this car
        """
        if not cls.can_user_review_car(user, car, booking):
            raise ValueError("User cannot review this car")
        
        return CarReview.objects.create(
            user=user,
            car=car,
            booking=booking,
            rating=rating,
            title=title,
            comment=comment
        )