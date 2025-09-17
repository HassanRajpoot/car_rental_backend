from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from .models import Car, CarReview
from .serializers import (
    CarListSerializer, CarDetailSerializer, CarCreateUpdateSerializer,
    CarReviewSerializer
)
from .services import CarService, CarReviewService
from .filters import CarFilter
from .permissions import IsFleetManagerOrReadOnly


class CarViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cars.
    Provides different serializers for list/detail views and CRUD operations.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CarFilter
    search_fields = ['name', 'description', 'make', 'model', 'location']
    ordering_fields = ['price_per_day', 'year', 'created_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsFleetManagerOrReadOnly]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Get queryset based on user and action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Fleet managers see only their cars
            if hasattr(self.request.user, 'is_fleet') and self.request.user.is_fleet():
                return Car.objects.filter(owner=self.request.user)
            return Car.objects.none()
        
        # Public views - only show available cars
        return CarService.get_cars_with_stats().filter(is_active=True)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return CarListSerializer
        elif self.action == 'retrieve':
            return CarDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CarCreateUpdateSerializer
        return CarDetailSerializer
    
    def perform_create(self, serializer):
        """Set owner when creating a car."""
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get available cars for specific dates and location."""
        location = request.query_params.get('location')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        start_dt = parse_datetime(start_date) if start_date else None
        end_dt = parse_datetime(end_date) if end_date else None
        
        cars = CarService.get_available_cars(location, start_dt, end_dt)
        
        # Apply additional filters
        queryset = self.filter_queryset(cars)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CarListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = CarListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular cars based on ratings and bookings."""
        cars = CarService.get_popular_cars()
        serializer = CarListSerializer(cars, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def review(self, request, pk=None):
        """Create a review for a car."""
        car = self.get_object()
        data = request.data
        
        try:
            review = CarReviewService.create_review(
                user=request.user,
                car=car,
                rating=data.get('rating'),
                title=data.get('title', ''),
                comment=data.get('comment'),
                booking=data.get('booking_id')
            )
            serializer = CarReviewSerializer(review)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all reviews for a car."""
        car = self.get_object()
        reviews = car.reviews.filter(is_approved=True).order_by('-created_at')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = CarReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CarReviewSerializer(reviews, many=True)
        return Response(serializer.data)
