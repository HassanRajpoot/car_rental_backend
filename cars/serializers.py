from django.utils import timezone
from rest_framework import serializers
from django.db.models import Avg, Count
from .models import Car, CarImage, CarReview

class CarImageSerializer(serializers.ModelSerializer):
    """Serializer for car images."""
    
    class Meta:
        model = CarImage
        fields = ['id', 'file', 'alt', 'is_primary', 'order']


class CarReviewSerializer(serializers.ModelSerializer):
    """Serializer for car reviews."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CarReview
        fields = ['id', 'user_name', 'rating', 'title', 'comment', 'created_at']


class CarListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for car listings."""
    
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Car
        fields = [
            'id', 'name', 'make', 'model', 'year', 'price_per_day', 
            'location', 'fuel_type', 'transmission', 'seats', 
            'primary_image', 'average_rating', 'review_count'
        ]
    
    def get_primary_image(self, obj):
        """Get the primary image for the car."""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.file.url)
            return primary_image.file.url
        return None
    
    def get_average_rating(self, obj):
        """Get average rating for the car."""
        return obj.reviews.filter(is_approved=True).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
    
    def get_review_count(self, obj):
        """Get total review count for the car."""
        return obj.reviews.filter(is_approved=True).count()


class CarDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual car views."""
    
    images = CarImageSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    feature_list = serializers.ReadOnlyField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    
    class Meta:
        model = Car
        fields = [
            'id', 'name', 'description', 'make', 'model', 'year',
            'fuel_type', 'transmission', 'seats', 'doors',
            'price_per_day', 'location', 'status', 'feature_list',
            'images', 'reviews', 'average_rating', 'review_count',
            'owner_name', 'created_at'
        ]
    
    def get_reviews(self, obj):
        """Get recent approved reviews."""
        recent_reviews = obj.reviews.filter(is_approved=True)[:5]
        return CarReviewSerializer(recent_reviews, many=True).data
    
    def get_average_rating(self, obj):
        """Get average rating for the car."""
        return obj.reviews.filter(is_approved=True).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
    
    def get_review_count(self, obj):
        """Get total review count for the car."""
        return obj.reviews.filter(is_approved=True).count()


class CarCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating cars (for fleet managers)."""
    
    class Meta:
        model = Car
        fields = [
            'name', 'description', 'make', 'model', 'year',
            'fuel_type', 'transmission', 'seats', 'doors',
            'price_per_day', 'location', 'status', 'features'
        ]
    
    def validate_year(self, value):
        """Validate car year."""
        current_year = timezone.now().year
        if value < 1900 or value > current_year + 1:
            raise serializers.ValidationError(
                f"Year must be between 1900 and {current_year + 1}"
            )
        return value
    
    def validate_price_per_day(self, value):
        """Validate price per day."""
        if value <= 0:
            raise serializers.ValidationError("Price per day must be greater than 0")
        return value