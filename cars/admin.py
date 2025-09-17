from django.contrib import admin
from .models import Car, CarImage, CarReview

class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 1
    fields = ['file', 'alt', 'is_primary', 'order']

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'make', 'model', 'year', 'price_per_day', 
        'location', 'status', 'owner', 'created_at'
    ]
    list_filter = ['status', 'make', 'fuel_type', 'transmission', 'location', 'created_at']
    search_fields = ['name', 'make', 'model', 'location', 'owner__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [CarImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'make', 'model', 'year')
        }),
        ('Specifications', {
            'fields': ('fuel_type', 'transmission', 'seats', 'doors', 'features')
        }),
        ('Rental Information', {
            'fields': ('price_per_day', 'location', 'status', 'owner')
        }),
        ('Metadata', {
            'fields': ('id', 'is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CarReview)
class CarReviewAdmin(admin.ModelAdmin):
    list_display = ['car', 'user', 'rating', 'title', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['car__name', 'user__email', 'title', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['approve_reviews', 'disapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    
    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    
    approve_reviews.short_description = "Approve selected reviews"
    disapprove_reviews.short_description = "Disapprove selected reviews"
