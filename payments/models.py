from django.db import models
from django.conf import settings
from orders.models import Order

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHODS = [
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Digital Wallet'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    PAYMENT_TYPES = [
        ('advance', 'Advance Payment'),
        ('full', 'Full Payment'),
        ('balance', 'Balance Payment'),
    ]

    # Payment identification
    payment_id = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Gateway details
    gateway_transaction_id = models.CharField(max_length=100, blank=True)
    gateway_name = models.CharField(max_length=50, blank=True)  # e.g., 'razorpay', 'paytm'
    gateway_response = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    initiated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional details
    notes = models.TextField(blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_id} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            # Generate payment ID
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.payment_id = f"PAY{timestamp}{self.order.id}"
        super().save(*args, **kwargs)

class Invoice(models.Model):
    """Invoice generation for completed orders"""
    invoice_number = models.CharField(max_length=30, unique=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    
    # Invoice details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Invoice breakdown
    base_charges = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    toll_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unloading_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Tax details
    cgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    igst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Invoice file
    invoice_file = models.FileField(upload_to='invoices/', blank=True)
    
    # Status
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d')
            count = Invoice.objects.filter(created_at__date=timezone.now().date()).count() + 1
            self.invoice_number = f"INV{timestamp}{count:04d}"
        
        # Calculate totals
        self.subtotal = (
            self.base_charges + self.fuel_charges + self.toll_charges + 
            self.loading_charges + self.unloading_charges + self.additional_charges
        )
        self.tax_amount = self.cgst_amount + self.sgst_amount + self.igst_amount
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        super().save(*args, **kwargs)

class PaymentHistory(models.Model):
    """Track payment status changes"""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Payment {self.payment.payment_id}: {self.previous_status} → {self.new_status}"
