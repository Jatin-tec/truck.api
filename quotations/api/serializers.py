from rest_framework import serializers
from quotations.models import QuotationRequest, Quotation, QuotationNegotiation, QuotationItem
from quotations.services import QuotationService
from django.contrib.auth import get_user_model
from django.db import models
from decimal import Decimal

User = get_user_model()


class QuotationItemSerializer(serializers.ModelSerializer):
    """Serializer for QuotationItem model"""
    total_price = serializers.SerializerMethodField()
    vehicle_details = serializers.SerializerMethodField()
    truck_name = serializers.SerializerMethodField()
    truck_type_name = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationItem
        fields = [
            'id', 'truck', 'truck_type', 'truck_name', 'truck_type_name', 'vehicle_details',
            'quantity', 'unit_price', 'total_price', 'estimated_delivery', 
            'pickup_locations', 'drop_locations', 'special_instructions'
        ]
        read_only_fields = ['id', 'total_price', 'vehicle_details', 'truck_name', 'truck_type_name']
    
    def get_total_price(self, obj):
        return obj.get_total_price()
    
    def get_vehicle_details(self, obj):
        return obj.get_vehicle_details()
    
    def get_truck_name(self, obj):
        if obj.truck:
            return f"{obj.truck.make} {obj.truck.model} ({obj.truck.registration_number})"
        return None
    
    def get_truck_type_name(self, obj):
        if obj.truck_type:
            return obj.truck_type.name
        elif obj.truck:
            return obj.truck.truck_type.name
        return None


class QuotationRequestSerializer(serializers.ModelSerializer):
    """Serializer for QuotationRequest model"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    quotations_count = serializers.SerializerMethodField()
    status = serializers.CharField(source='is_active', read_only=True)
    total_amount_range = serializers.SerializerMethodField()
    origin_city = serializers.CharField(source='pickup_address', read_only=True)
    destination_city = serializers.CharField(source='delivery_address', read_only=True)
    
    class Meta:
        model = QuotationRequest
        fields = [
            'id', 'customer', 'customer_name', 'origin_pincode', 'destination_pincode',
            'origin_city', 'destination_city', 'status', 'total_amount_range',
            'pickup_date', 'drop_date', 'weight', 'weight_unit', 'vehicle_type', 
            'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'delivery_latitude', 'delivery_longitude', 'delivery_address', 
            'quotations_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'customer_name', 'quotations_count', 'status', 'total_amount_range', 'created_at', 'updated_at']

    def get_quotations_count(self, obj):
        return obj.get_total_quotations()

    def get_total_amount_range(self, obj):
        quotations = Quotation.objects.filter(quotation_request=obj)
        if not quotations.exists():
            return {"min": "0.00", "max": "0.00"}
        return {"min": str(min(quotations.values_list('total_amount', flat=True))), "max": str(max(quotations.values_list('total_amount', flat=True)))}


class QuotationRequestDetailSerializer(QuotationRequestSerializer):
    quotations = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationRequest
        fields = [
            'id', 'customer', 'customer_name', 'origin_pincode', 'destination_pincode', 'quotations',
            'origin_city', 'destination_city', 'status', 'total_amount_range',
            'pickup_date', 'drop_date', 'weight', 'weight_unit', 'vehicle_type', 
            'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'delivery_latitude', 'delivery_longitude', 'delivery_address',
            'quotations_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'customer_name', 'quotations_count', 'status', 'total_amount_range', 'created_at', 'updated_at']
    
    def get_quotations(self, obj):
        quotations = Quotation.objects.filter(quotation_request=obj)
        serializer = QuotationSerializer(quotations, many=True)
        return serializer.data


class ActualVehicleItemSerializer(serializers.Serializer):
    """Serializer for the actual vehicle item structure from frontend"""
    vehicle_id = serializers.CharField(required=False, allow_blank=True)  # Optional frontend identifier
    vehicle_model = serializers.CharField(required=False, allow_blank=True)
    vehicle_type = serializers.CharField()
    max_weight = serializers.CharField(required=False, allow_blank=True)
    unit_price = serializers.CharField()
    quantity = serializers.IntegerField(default=1)
    estimated_delivery = serializers.CharField(required=False, allow_blank=True)
    
    # Optional fields for quote-specific details
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    pickup_locations = serializers.ListField(required=False, default=list)
    drop_locations = serializers.ListField(required=False, default=list)


class QuotationCreateSerializer(serializers.Serializer):
    """Serializer for creating quotations - handles the actual frontend structure"""
    vendor_id = serializers.IntegerField()
    vendor_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    origin_pincode = serializers.CharField(max_length=10)
    destination_pincode = serializers.CharField(max_length=10)
    pickup_date = serializers.DateTimeField()
    drop_date = serializers.DateTimeField()
    weight = serializers.CharField()  # Can be "3" or "3.5"
    weight_unit = serializers.CharField()
    urgency_level = serializers.CharField(default='standard')
    items = ActualVehicleItemSerializer(many=True)
    
    # Optional fields
    vehicle_type = serializers.CharField(required=False, allow_blank=True)
    customer_proposed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    customer_negotiation_message = serializers.CharField(required=False, allow_blank=True)

    def validate_vendor_id(self, value):
        """Validate vendor exists and has vendor role"""
        try:
            vendor = User.objects.get(id=value, role='vendor')
            return vendor
        except User.DoesNotExist:
            raise serializers.ValidationError("Vendor not found or invalid role")

    def validate(self, data):
        """Additional validation for the data"""
        pickup_date = data.get('pickup_date')
        drop_date = data.get('drop_date')
        
        if pickup_date and drop_date:
            if pickup_date.date() >= drop_date.date():
                raise serializers.ValidationError("Drop date must be after pickup date")
        
        # Validate items
        items = data.get('items', [])
        if not items:
            raise serializers.ValidationError("At least one vehicle item is required")
            
        return data

    def create(self, validated_data):
        """Create or get quotation request and add quotation using service layer"""
        customer = self.context['request'].user
        
        # Use service layer for business logic
        return QuotationService.create_quotation_request_and_quotation(
            customer=customer,
            quotation_data=validated_data
        )


class QuotationSerializer(serializers.ModelSerializer):
    """Serializer for Quotation model"""
    vendor_name = serializers.CharField(read_only=True)
    quotation_request_id = serializers.IntegerField(source='quotation_request.id', read_only=True)
    negotiations = serializers.SerializerMethodField()
    items = QuotationItemSerializer(many=True, read_only=True)
    total_items_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_request_id', 'vendor', 'vendor_name', 'items', 'total_items_price',
            'total_amount', 'terms_and_conditions', 'validity_hours', 'negotiations', 
            'urgency_level', 'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'vendor', 'vendor_name', 'quotation_request_id', 'items', 'total_items_price', 'created_at', 'updated_at', 'negotiations']

    def get_negotiations(self, obj):
        """Get all negotiations for this quotation"""
        negotiations = QuotationNegotiation.objects.filter(quotation=obj).order_by('created_at')
        serializer = QuotationNegotiationSerializer(negotiations, many=True)
        return serializer.data
    
    def get_total_items_price(self, obj):
        """Calculate total price from all items"""
        return sum(item.get_total_price() for item in obj.items.all())


class NegotiationCreateSerializer(serializers.Serializer):
    """Serializer for creating negotiation offers"""
    proposed_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    message = serializers.CharField(required=False, allow_blank=True)
    
    # Optional breakdown fields
    proposed_base_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    proposed_fuel_charges = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    proposed_toll_charges = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    proposed_loading_charges = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    proposed_unloading_charges = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    proposed_additional_charges = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    def validate_proposed_amount(self, value):
        """Validate proposed amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Proposed amount must be positive")
        return value

    def validate(self, data):
        """Validate breakdown fields sum to total if provided"""
        breakdown_fields = [
            'proposed_base_price',
            'proposed_fuel_charges', 
            'proposed_toll_charges',
            'proposed_loading_charges',
            'proposed_unloading_charges',
            'proposed_additional_charges'
        ]
        
        # Check if any breakdown fields are provided
        breakdown_values = [data.get(field) for field in breakdown_fields if data.get(field) is not None]
        
        if breakdown_values:
            # If breakdown is provided, ensure it sums to proposed_amount
            total_breakdown = sum(breakdown_values)
            if abs(total_breakdown - data['proposed_amount']) > 0.01:  # Allow small rounding differences
                raise serializers.ValidationError(
                    f"Breakdown sum ({total_breakdown}) does not match proposed amount ({data['proposed_amount']})"
                )
        
        return data


class QuotationNegotiationSerializer(serializers.ModelSerializer):
    """Serializer for QuotationNegotiation model"""
    
    class Meta:
        model = QuotationNegotiation
        fields = [
            'id', 'quotation', 'initiated_by', 'proposed_amount', 'message',
            'proposed_base_price', 'proposed_fuel_charges', 'proposed_toll_charges',
            'proposed_loading_charges', 'proposed_unloading_charges', 'proposed_additional_charges',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
