from rest_framework import serializers
from quotations.models import QuotationRequest, Quotation
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()


class QuotationRequestSerializer(serializers.ModelSerializer):
    """Serializer for QuotationRequest model"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    total_quotations = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationRequest
        fields = [
            'id', 'customer', 'customer_name', 'origin_pincode', 'destination_pincode',
            'pickup_date', 'drop_date', 'weight', 'weight_unit', 'vehicle_type', 
            'urgency_level', 'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'delivery_latitude', 'delivery_longitude', 'delivery_address',
            'cargo_description', 'special_instructions', 'distance_km', 
            'total_quotations', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'customer_name', 'total_quotations', 'created_at', 'updated_at']

    def get_total_quotations(self, obj):
        return obj.get_total_quotations()


class VehicleItemSerializer(serializers.Serializer):
    """Serializer for vehicle item in quotation"""
    id = serializers.CharField()
    model = serializers.CharField()
    vehicleType = serializers.CharField()
    maxWeight = serializers.CharField()
    gpsNumber = serializers.CharField()
    total = serializers.CharField()
    estimatedDelivery = serializers.CharField()


class QuotationItemSerializer(serializers.Serializer):
    """Serializer for quotation item"""
    vehicle = VehicleItemSerializer()
    quantity = serializers.IntegerField()


class SearchParamsSerializer(serializers.Serializer):
    """Serializer for search parameters"""
    originPinCode = serializers.CharField()
    destinationPinCode = serializers.CharField()
    pickupDate = serializers.DateTimeField()
    dropDate = serializers.DateTimeField()
    weight = serializers.DecimalField(max_digits=8, decimal_places=2)
    weightUnit = serializers.CharField()
    vehicleType = serializers.CharField()
    urgencyLevel = serializers.CharField()


class QuotationCreateSerializer(serializers.Serializer):
    """Serializer for creating quotations"""
    vendorId = serializers.IntegerField()
    vendorName = serializers.CharField()
    items = QuotationItemSerializer(many=True)
    totalAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    searchParams = SearchParamsSerializer()

    def validate_vendorId(self, value):
        """Validate vendor exists and has vendor role"""
        try:
            vendor = User.objects.get(id=value, role='vendor')
            return vendor
        except User.DoesNotExist:
            raise serializers.ValidationError("Vendor not found or invalid role")

    def validate(self, data):
        """Additional validation for the data"""
        search_params = data.get('searchParams')
        
        # Validate dates
        pickup_date = search_params.get('pickupDate')
        drop_date = search_params.get('dropDate')
        
        if pickup_date and drop_date:
            if pickup_date.date() >= drop_date.date():
                raise serializers.ValidationError("Drop date must be after pickup date")
        
        # Validate items
        items = data.get('items', [])
        if not items:
            raise serializers.ValidationError("At least one vehicle item is required")
            
        return data

    def create(self, validated_data):
        """Create or get quotation request and add quotation"""
        search_params = validated_data['searchParams']
        vendor = validated_data['vendorId']
        
        # Extract search parameters for QuotationRequest
        quotation_request_data = {
            'customer': self.context['request'].user,
            'origin_pincode': search_params['originPinCode'],
            'destination_pincode': search_params['destinationPinCode'],
            'pickup_date': search_params['pickupDate'].date(),
            'drop_date': search_params['dropDate'].date(),
            'weight': search_params['weight'],
            'weight_unit': search_params['weightUnit'],
            'vehicle_type': search_params['vehicleType'],
            'urgency_level': search_params['urgencyLevel'],
        }
        
        # Get or create quotation request
        quotation_request, created = QuotationRequest.objects.get_or_create(
            **quotation_request_data,
            defaults={'is_active': True}
        )
        
        # Create quotation for this request
        quotation = Quotation.objects.create(
            quotation_request=quotation_request,
            vendor=vendor,
            vendor_name=validated_data['vendorName'],
            items=validated_data['items'],
            total_amount=validated_data['totalAmount'],
            status='pending'
        )
        
        return {
            'quotation_request': quotation_request,
            'quotation': quotation,
            'created_new_request': created
        }


class QuotationSerializer(serializers.ModelSerializer):
    """Serializer for Quotation model"""
    vendor_name = serializers.CharField(read_only=True)
    quotation_request_id = serializers.IntegerField(source='quotation_request.id', read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_request_id', 'vendor', 'vendor_name', 'items',
            'total_amount', 'terms_and_conditions', 'validity_hours',
            'customer_suggested_price', 'vendor_response_to_suggestion',
            'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'vendor', 'vendor_name', 'quotation_request_id', 'created_at', 'updated_at']


class QuotationResponseSerializer(serializers.Serializer):
    """Serializer for quotation creation response"""
    quotation_request = QuotationRequestSerializer()
    quotation = QuotationSerializer()
    created_new_request = serializers.BooleanField()
    message = serializers.CharField()
