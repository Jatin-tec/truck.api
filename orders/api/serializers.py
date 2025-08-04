from rest_framework import serializers
from orders.models import Order, OrderStatusHistory, OrderTracking, OrderDocument
from django.contrib.auth import get_user_model
import random
import string

User = get_user_model()

class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.phone_number', read_only=True)
    truck_info = serializers.SerializerMethodField()
    driver_info = serializers.SerializerMethodField()
    quotation_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'quotation', 'quotation_info',
            'customer_name', 'customer_phone', 'vendor_name', 'vendor_phone',
            'truck_info', 'driver_info', 'pickup_address', 'delivery_address',
            'pickup_latitude', 'pickup_longitude', 'delivery_latitude', 'delivery_longitude',
            'scheduled_pickup_date', 'scheduled_delivery_date', 
            'actual_pickup_date', 'actual_delivery_date', 'total_amount',
            'cargo_description', 'estimated_weight', 'actual_weight',
            'status', 'special_instructions', 'delivery_instructions',
            'delivery_otp', 'is_otp_verified', 'created_at', 'updated_at'
        ]

    def get_truck_info(self, obj):
        return {
            'id': obj.truck.id,
            'registration_number': obj.truck.registration_number,
            'truck_type': obj.truck.truck_type.name,
            'capacity': obj.truck.capacity,
            'make': obj.truck.make,
            'model': obj.truck.model
        }

    def get_driver_info(self, obj):
        if obj.driver:
            return {
                'id': obj.driver.id,
                'name': obj.driver.name,
                'phone_number': obj.driver.phone_number,
                'license_number': obj.driver.license_number
            }
        return None

    def get_quotation_info(self, obj):
        return {
            'id': obj.quotation.id,
            'base_price': obj.quotation.base_price,
            'fuel_charges': obj.quotation.fuel_charges,
            'toll_charges': obj.quotation.toll_charges,
            'loading_charges': obj.quotation.loading_charges,
            'unloading_charges': obj.quotation.unloading_charges,
            'additional_charges': obj.quotation.additional_charges,
            'total_amount': obj.quotation.total_amount
        }

class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating order from accepted quotation"""
    quotation_id = serializers.IntegerField()
    delivery_instructions = serializers.CharField(required=False, allow_blank=True)
    special_instructions = serializers.CharField(required=False, allow_blank=True)

    def validate_quotation_id(self, value):
        from quotations.models import Quotation
        try:
            quotation = Quotation.objects.get(id=value, status='accepted')
            # Ensure customer owns this quotation
            if quotation.quotation_request.customer != self.context['request'].user:
                raise serializers.ValidationError("You are not authorized to create order for this quotation")
            # Check if order already exists for this quotation
            if hasattr(quotation, 'order'):
                raise serializers.ValidationError("Order already exists for this quotation")
            return quotation
        except Quotation.DoesNotExist:
            raise serializers.ValidationError("Quotation not found or not accepted")

    def create(self, validated_data):
        quotation = validated_data['quotation_id']
        
        # Generate delivery OTP
        delivery_otp = ''.join(random.choices(string.digits, k=6))
        
        # Create order from quotation data
        order = Order.objects.create(
            quotation=quotation,
            customer=quotation.quotation_request.customer,
            vendor=quotation.vendor,
            truck=quotation.quotation_request.truck,
            pickup_address=quotation.quotation_request.pickup_address,
            delivery_address=quotation.quotation_request.delivery_address,
            pickup_latitude=quotation.quotation_request.pickup_latitude,
            pickup_longitude=quotation.quotation_request.pickup_longitude,
            delivery_latitude=quotation.quotation_request.delivery_latitude,
            delivery_longitude=quotation.quotation_request.delivery_longitude,
            scheduled_pickup_date=quotation.quotation_request.pickup_date,
            scheduled_delivery_date=quotation.quotation_request.expected_delivery_date,
            total_amount=quotation.total_amount,
            cargo_description=quotation.quotation_request.cargo_description,
            estimated_weight=quotation.quotation_request.estimated_weight,
            special_instructions=validated_data.get('special_instructions', ''),
            delivery_instructions=validated_data.get('delivery_instructions', ''),
            delivery_otp=delivery_otp,
            status='created'
        )
        
        # Update truck status to busy
        quotation.quotation_request.truck.availability_status = 'busy'
        quotation.quotation_request.truck.save()
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            new_status='created',
            updated_by=self.context['request'].user,
            notes='Order created from accepted quotation'
        )
        
        return order

class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('driver_assigned', 'Driver Assigned'),
        ('pickup', 'Pickup in Progress'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    driver_id = serializers.IntegerField(required=False)
    actual_weight = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)

class OrderTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTracking
        fields = ['id', 'latitude', 'longitude', 'address', 'speed', 'heading', 'timestamp']

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'previous_status', 'new_status', 'updated_by_name', 
            'notes', 'location_latitude', 'location_longitude', 'timestamp'
        ]

class OrderDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True)
    
    class Meta:
        model = OrderDocument
        fields = [
            'id', 'order', 'document_type', 'file', 'description', 
            'uploaded_by_name', 'uploaded_at'
        ]

class OrderDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDocument
        fields = ['order', 'document_type', 'file', 'description']

    def create(self, validated_data):
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)

class DeliveryVerificationSerializer(serializers.Serializer):
    """Serializer for delivery OTP verification"""
    otp = serializers.CharField(max_length=6)
    actual_weight = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)

class AssignDriverSerializer(serializers.Serializer):
    """Serializer for assigning driver to order"""
    driver_id = serializers.IntegerField()

    def validate_driver_id(self, value):
        from trucks.models import Driver
        try:
            driver = Driver.objects.get(
                id=value,
                vendor=self.context['request'].user,
                is_available=True,
                is_active=True
            )
            return driver
        except Driver.DoesNotExist:
            raise serializers.ValidationError("Driver not found or not available")

class OrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for order listing"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    truck_registration = serializers.CharField(source='truck.registration_number', read_only=True)
    driver_name = serializers.CharField(source='driver.name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer_name', 'vendor_name', 
            'truck_registration', 'driver_name', 'pickup_address', 
            'delivery_address', 'scheduled_pickup_date', 'scheduled_delivery_date',
            'total_amount', 'status', 'created_at'
        ]
