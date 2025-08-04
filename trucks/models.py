from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class TruckType(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g., "Mini Truck", "Large Truck", "Container"
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Truck(models.Model):
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ]

    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='trucks',
        limit_choices_to={'role': 'vendor'}
    )
    truck_type = models.ForeignKey(TruckType, on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=20, unique=True)
    capacity = models.DecimalField(max_digits=8, decimal_places=2, help_text="Capacity in tons")
    make = models.CharField(max_length=50)  # e.g., "Tata", "Mahindra"
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField(validators=[MinValueValidator(1990), MaxValueValidator(2030)])
    color = models.CharField(max_length=30, blank=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    base_price_per_km = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price per kilometer")
    
    # Location fields
    current_location_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_location_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_location_address = models.TextField(blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.registration_number} - {self.truck_type.name}"


class TruckDocument(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50)  # e.g., "RC", "Insurance", "Fitness Certificate"
    document_file = models.FileField(upload_to='trucks/documents/')
    expiry_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type} for {self.truck.registration_number}"


class TruckImage(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='trucks/images/')
    caption = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.truck.registration_number}"


class Driver(models.Model):
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='drivers',
        limit_choices_to={'role': 'vendor'}
    )
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    license_number = models.CharField(max_length=50, unique=True)
    license_expiry_date = models.DateField()
    experience_years = models.PositiveIntegerField(default=0)
    
    # Optional truck assignment (a driver can be assigned to a specific truck)
    assigned_truck = models.ForeignKey(
        Truck, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_driver'
    )
    
    # Driver documents
    license_image = models.ImageField(upload_to='drivers/licenses/', blank=True)
    profile_image = models.ImageField(upload_to='drivers/profiles/', blank=True)
    
    # Status
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.license_number}"


class TruckLocation(models.Model):
    """Track truck location history"""
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.truck.registration_number} at {self.timestamp}"
