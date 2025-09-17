from django.db import models
from django.conf import settings

class Booking(models.Model):
    STATUS = (("pending","Pending"),("confirmed","Confirmed"),("cancelled","Cancelled"),("refunded","Refunded"),("completed","Completed"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    car = models.ForeignKey("cars.Car", on_delete=models.CASCADE, related_name="bookings")
    start = models.DateTimeField()
    end = models.DateTimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=32, choices=STATUS, default="pending")
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start"]

    def overlaps(self, start, end):
        return not (self.end <= start or self.start >= end)
