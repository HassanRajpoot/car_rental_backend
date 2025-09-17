from rest_framework import serializers
from .models import Booking

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ("id","user","car","start","end","total_price","status","stripe_payment_intent")
        read_only_fields = ("status","stripe_payment_intent","user","total_price")
