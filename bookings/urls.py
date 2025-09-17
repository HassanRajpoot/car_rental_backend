from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, CreatePaymentIntentView, stripe_webhook

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
    path('payment/create-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
]