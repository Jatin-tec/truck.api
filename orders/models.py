from django.db import models
from django.conf import settings
from quotations.models import Quotation
from trucks.models import Truck, Driver


class Order(models.Model):
    STATUS_CHOICES = [
        ('created', 'Order Created'),
        ('confirmed', 'Confirmed'),
        ('driver_assigned', 'Driver Assigned'),
        ('pickup', 'Pickup in Progress'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Order identification
    order_number = models.CharField(max_length=20, unique=True)
    quotation = models.OneToOneField(Quotation, on_delete=models.CASCADE, related_name='order')
    
    # Participants
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        limit_choices_to={'role': 'customer'}
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_orders',
        limit_choices_to={'role': 'vendor'}
    )
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    driver = models.ForeignKey(
        Driver, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='orders'
    )
    
    # Order details (copied from quotation for data integrity)
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    # Scheduling
    scheduled_pickup_date = models.DateTimeField()
    scheduled_delivery_date = models.DateTimeField()
    actual_pickup_date = models.DateTimeField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    
    # Pricing (copied from quotation)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Cargo details
    cargo_description = models.TextField()
    estimated_weight = models.DecimalField(max_digits=8, decimal_places=2)
    actual_weight = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    
    # Special instructions
    special_instructions = models.TextField(blank=True)
    delivery_instructions = models.TextField(blank=True)
    
    # OTP for delivery verification
    delivery_otp = models.CharField(max_length=6, blank=True)
    is_otp_verified = models.BooleanField(default=False)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_number = f"ORD{timestamp}"
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    location_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Order {self.order.order_number}: {self.previous_status} → {self.new_status}"


class OrderDocument(models.Model):
    """Documents related to an order (e.g., pickup receipt, delivery receipt, photos)"""
    DOCUMENT_TYPES = [
        ('pickup_receipt', 'Pickup Receipt'),
        ('delivery_receipt', 'Delivery Receipt'),
        ('cargo_photo', 'Cargo Photo'),
        ('damage_report', 'Damage Report'),
        ('invoice', 'Invoice'),
        ('other', 'Other'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='orders/documents/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} for Order {self.order.order_number}"
