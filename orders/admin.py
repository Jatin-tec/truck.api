from django.contrib import admin
from orders.models import Order, OrderStatusHistory, OrderDocument

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'vendor', 'truck', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer__name', 'vendor__name', 'truck__registration_number']
    readonly_fields = ['order_number', 'created_at', 'updated_at']

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'previous_status', 'new_status', 'updated_by', 'timestamp']
    list_filter = ['new_status', 'timestamp']
    readonly_fields = ['timestamp']

@admin.register(OrderDocument)
class OrderDocumentAdmin(admin.ModelAdmin):
    list_display = ['order', 'document_type', 'uploaded_by', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    readonly_fields = ['uploaded_at']
