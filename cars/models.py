from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

class CarManager(models.Manager):
    """Custom manager for Car model."""
    
    def available(self):
        """Return only available cars."""
        return self.filter(status='available')
    
    def by_location(self, location):
        """Filter cars by location."""
        return self.filter(location__icontains=location)
    
    def by_price_range(self, min_price=None, max_price=None):
        """Filter cars by price range."""
        queryset = self.get_queryset()
        if min_price:
            queryset = queryset.filter(price_per_day__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_per_day__lte=max_price)
        return queryset


class Car(models.Model):
    """Car model with enhanced fields and validation."""
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('unavailable', 'Unavailable'),
        ('rented', 'Currently Rented'),
    ]
    
    FUEL_TYPE_CHOICES = [
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
    ]
    
    TRANSMISSION_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    make = models.CharField(max_length=128)
    model = models.CharField(max_length=128)
    year = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(timezone.now().year + 1)
        ]
    )
    
    # Specifications
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPE_CHOICES, default='gasoline')
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, default='manual')
    seats = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(15)])
    doors = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(2), MaxValueValidator(6)])
    
    # Rental Information
    price_per_day = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='available')
    
    # Additional Features
    features = models.TextField(
        blank=True, 
        null=True, 
        help_text="Comma-separated list of features (e.g., 'GPS, AC, Bluetooth')"
    )
    
    # Ownership & Management
    owner = models.ForeignKey(
        "users.User", 
        on_delete=models.CASCADE, 
        related_name="owned_cars",
        help_text="Fleet manager who owns this car"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Custom manager
    objects = CarManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'location']),
            models.Index(fields=['make', 'model']),
            models.Index(fields=['price_per_day']),
            models.Index(fields=['owner', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price_per_day__gt=0),
                name='positive_price_per_day'
            ),
            models.CheckConstraint(
                check=models.Q(year__gte=1900),
                name='valid_year'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.make} {self.model} {self.year})"
    
    @property
    def full_name(self):
        """Return full car name including make, model, and year."""
        return f"{self.make} {self.model} {self.year}"
    
    @property
    def feature_list(self):
        """Return features as a list."""
        if self.features:
            return [feature.strip() for feature in self.features.split(',')]
        return []
    
    @property
    def is_available_for_booking(self):
        """Check if car is available for booking."""
        return self.status == 'available' and self.is_active
    
    def get_current_booking(self):
        """Get current active booking for this car."""
        from bookings.models import Booking
        return Booking.objects.filter(
            car=self,
            status__in=['pending', 'confirmed'],
            start__lte=timezone.now(),
            end__gte=timezone.now()
        ).first()


class CarImage(models.Model):
    """Car image model with enhanced functionality."""
    
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="images")
    file = models.ImageField(upload_to="cars/%Y/%m/")
    alt = models.CharField(max_length=128, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'order', 'uploaded_at']
        indexes = [
            models.Index(fields=['car', 'is_primary']),
        ]
    
    def __str__(self):
        return f"Image for {self.car.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per car
        if self.is_primary:
            CarImage.objects.filter(car=self.car, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class CarReview(models.Model):
    """Car review model for customer feedback."""
    
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, null=True, blank=True)
    
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['car', 'user', 'booking']  # One review per booking
        indexes = [
            models.Index(fields=['car', 'is_approved']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"Review for {self.car.name} by {self.user.email}"