from rest_framework import serializers
from payments.models import Payment, Invoice, PaymentHistory
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class PaymentSerializer(serializers.ModelSerializer):
    order_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'order', 'order_info', 'amount', 'payment_type',
            'payment_method', 'gateway_transaction_id', 'gateway_name', 'status',
            'initiated_at', 'completed_at', 'failed_at', 'notes', 'failure_reason',
            'created_at', 'updated_at'
        ]

    def get_order_info(self, obj):
        return {
            'id': obj.order.id,
            'order_number': obj.order.order_number,
            'customer_name': obj.order.customer.name,
            'vendor_name': obj.order.vendor.name,
            'total_amount': obj.order.total_amount
        }

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['order', 'amount', 'payment_type', 'payment_method']

    def validate_order(self, value):
        # Ensure customer owns this order
        if value.customer != self.context['request'].user:
            raise serializers.ValidationError("You can only create payments for your own orders")
        # Check if order is in valid state for payment
        if value.status not in ['created', 'confirmed', 'completed']:
            raise serializers.ValidationError("Order is not in a valid state for payment")
        return value

    def validate(self, data):
        order = data['order']
        amount = data['amount']
        payment_type = data['payment_type']
        
        # Validate payment amount
        if payment_type == 'full' and amount != order.total_amount:
            raise serializers.ValidationError("Full payment amount must equal order total amount")
        elif payment_type == 'advance' and amount >= order.total_amount:
            raise serializers.ValidationError("Advance payment must be less than total amount")
        
        # Check for existing payments
        existing_payments = Payment.objects.filter(
            order=order,
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        if existing_payments + amount > order.total_amount:
            raise serializers.ValidationError("Payment amount exceeds remaining balance")
        
        return data

class PaymentStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['status', 'gateway_transaction_id', 'gateway_response', 'failure_reason']

class InvoiceSerializer(serializers.ModelSerializer):
    order_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'order', 'order_info', 'subtotal', 'tax_amount',
            'discount_amount', 'total_amount', 'base_charges', 'fuel_charges',
            'toll_charges', 'loading_charges', 'unloading_charges', 'additional_charges',
            'cgst_rate', 'sgst_rate', 'igst_rate', 'cgst_amount', 'sgst_amount',
            'igst_amount', 'invoice_file', 'is_generated', 'generated_at',
            'created_at', 'updated_at'
        ]

    def get_order_info(self, obj):
        return {
            'id': obj.order.id,
            'order_number': obj.order.order_number,
            'customer_name': obj.order.customer.name,
            'vendor_name': obj.order.vendor.name
        }

class InvoiceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'order', 'base_charges', 'fuel_charges', 'toll_charges',
            'loading_charges', 'unloading_charges', 'additional_charges',
            'cgst_rate', 'sgst_rate', 'igst_rate', 'discount_amount'
        ]

    def validate_order(self, value):
        # Ensure order belongs to vendor
        if value.vendor != self.context['request'].user:
            raise serializers.ValidationError("You can only create invoices for your own orders")
        # Check if order is completed
        if value.status != 'completed':
            raise serializers.ValidationError("Invoice can only be created for completed orders")
        # Check if invoice already exists
        if hasattr(value, 'invoice'):
            raise serializers.ValidationError("Invoice already exists for this order")
        return value

class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ['id', 'previous_status', 'new_status', 'notes', 'timestamp']

class PaymentInitiateSerializer(serializers.Serializer):
    """Serializer for initiating payment"""
    payment_id = serializers.CharField()
    gateway = serializers.ChoiceField(choices=['razorpay', 'paytm', 'cashfree'])

class PaymentCompleteSerializer(serializers.Serializer):
    """Serializer for completing payment"""
    payment_id = serializers.CharField()
    gateway_transaction_id = serializers.CharField()
    gateway_response = serializers.JSONField()
    status = serializers.ChoiceField(choices=['completed', 'failed'])
    failure_reason = serializers.CharField(required=False, allow_blank=True)
