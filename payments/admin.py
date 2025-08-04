from django.contrib import admin
from payments.models import Payment, Invoice, PaymentHistory

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'order', 'amount', 'payment_type', 'payment_method', 'status', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'status', 'created_at']
    search_fields = ['payment_id', 'order__order_number']
    readonly_fields = ['payment_id', 'created_at', 'updated_at']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'order', 'total_amount', 'is_generated', 'created_at']
    list_filter = ['is_generated', 'created_at']
    search_fields = ['invoice_number', 'order__order_number']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['payment', 'previous_status', 'new_status', 'timestamp']
    list_filter = ['new_status', 'timestamp']
    readonly_fields = ['timestamp']
