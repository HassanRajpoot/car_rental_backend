import django_filters
from .models import Car

class CarFilter(django_filters.FilterSet):
    """Advanced filtering for cars."""
    
    min_price = django_filters.NumberFilter(field_name='price_per_day', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price_per_day', lookup_expr='lte')
    min_year = django_filters.NumberFilter(field_name='year', lookup_expr='gte')
    max_year = django_filters.NumberFilter(field_name='year', lookup_expr='lte')
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    
    class Meta:
        model = Car
        fields = {
            'make': ['exact', 'icontains'],
            'model': ['exact', 'icontains'],
            'fuel_type': ['exact'],
            'transmission': ['exact'],
            'seats': ['exact', 'gte', 'lte'],
            'status': ['exact'],
        }