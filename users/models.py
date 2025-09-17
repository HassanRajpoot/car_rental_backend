from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):
    ROLE_CHOICES = (
        ("customer", "Customer"),
        ("fleet", "FleetManager"),
        ("admin", "Admin"),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_customer(self):
        return self.role == "customer"

    def is_fleet(self):
        return self.role == "fleet"

    def is_admin(self):
        return self.role == "admin"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"