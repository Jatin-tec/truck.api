from rest_framework import serializers
from quotations.models import QuotationRequest, Quotation
from django.contrib.auth import get_user_model
from django.db import models
from decimal import Decimal

User = get_user_model()


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
            'urgency_level', 'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'delivery_latitude', 'delivery_longitude', 'delivery_address',
            'cargo_description', 'special_instructions', 'distance_km', 
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
            'urgency_level', 'pickup_latitude', 'pickup_longitude', 'pickup_address',
            'delivery_latitude', 'delivery_longitude', 'delivery_address',
            'cargo_description', 'special_instructions', 'distance_km', 
            'quotations_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer', 'customer_name', 'quotations_count', 'status', 'total_amount_range', 'created_at', 'updated_at']
    
    def get_quotations(self, obj):
        quotations = Quotation.objects.filter(quotation_request=obj)
        serializer = QuotationSerializer(quotations, many=True)
        return serializer.data


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


class VehicleItemV2Serializer(serializers.Serializer):
    """Serializer for vehicle item in the new format"""
    vehicle_id = serializers.IntegerField()
    vehicle_model = serializers.CharField()
    vehicle_type = serializers.CharField()
    max_weight = serializers.CharField()
    gps_number = serializers.CharField()
    unit_price = serializers.CharField()
    quantity = serializers.IntegerField()
    estimated_delivery = serializers.CharField()

    def validate_vehicle_id(self, value):
        """Validate vehicle exists in trucks"""
        from trucks.models import Truck
        try:
            truck = Truck.objects.get(id=value, is_active=True)
            return value
        except Truck.DoesNotExist:
            raise serializers.ValidationError(f"Truck with ID {value} not found or inactive")


class QuotationCreateV2Serializer(serializers.Serializer):
    """New serializer for exact request format provided by user"""
    vendor_id = serializers.CharField()  # Can be string ID or username
    vendor_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=3)
    origin_pincode = serializers.CharField(max_length=10)
    destination_pincode = serializers.CharField(max_length=10)
    pickup_date = serializers.DateTimeField()
    drop_date = serializers.DateTimeField()
    weight = serializers.CharField()  # Can be "3" or "3.5"
    weight_unit = serializers.CharField()
    urgency_level = serializers.CharField(default='medium')
    items = VehicleItemV2Serializer(many=True)

    def validate_vendor_id(self, value):
        """Validate vendor exists - support both ID and string identifiers"""
        try:
            # Try to find by ID first
            if value.isdigit():
                vendor = User.objects.get(id=int(value), role='vendor', is_active=True)
            else:
                # Try to find by email or phone
                vendor = User.objects.filter(
                    role='vendor', 
                    is_active=True
                ).filter(
                    models.Q(email=value) | models.Q(phone_number=value)
                ).first()
                
                if not vendor:
                    raise User.DoesNotExist()
                    
            return vendor
        except User.DoesNotExist:
            raise serializers.ValidationError(f"Vendor '{value}' not found or inactive")

    def validate_weight(self, value):
        """Convert weight string to decimal"""
        try:
            # Remove any non-numeric characters except decimal point
            clean_value = ''.join(c for c in value if c.isdigit() or c == '.')
            return Decimal(clean_value)
        except:
            raise serializers.ValidationError("Invalid weight format")

    def validate_weight_unit(self, value):
        """Normalize weight unit"""
        unit_mapping = {
            'tonnes': 'ton',
            'tonne': 'ton',
            'tons': 'ton',
            'ton': 'ton',
            'kg': 'kg',
            'kgs': 'kg',
            'kilogram': 'kg',
            'kilograms': 'kg',
            'lbs': 'lbs',
            'pounds': 'lbs'
        }
        normalized = unit_mapping.get(value.lower(), value.lower())
        if normalized not in ['kg', 'ton', 'lbs']:
            raise serializers.ValidationError("Weight unit must be 'kg', 'ton', or 'lbs'")
        return normalized

    def validate_urgency_level(self, value):
        """Normalize urgency level"""
        urgency_mapping = {
            'standard': 'medium',
            'normal': 'medium',
            'low': 'low',
            'medium': 'medium',
            'high': 'high',
            'urgent': 'urgent',
            'emergency': 'urgent'
        }
        normalized = urgency_mapping.get(value.lower(), 'medium')
        return normalized

    def validate(self, data):
        """Additional validation"""
        pickup_date = data.get('pickup_date')
        drop_date = data.get('drop_date')
        
        if pickup_date and drop_date:
            if pickup_date.date() >= drop_date.date():
                raise serializers.ValidationError("Drop date must be after pickup date")
        
        items = data.get('items', [])
        if not items:
            raise serializers.ValidationError("At least one vehicle item is required")
            
        return data

    def create(self, validated_data):
        """Create or get quotation request and add quotation"""
        vendor = validated_data['vendor_id']
        customer = self.context['request'].user
        
        # Prepare quotation request data
        quotation_request_data = {
            'customer': customer,
            'origin_pincode': validated_data['origin_pincode'],
            'destination_pincode': validated_data['destination_pincode'],
            'pickup_date': validated_data['pickup_date'].date(),
            'drop_date': validated_data['drop_date'].date(),
            'weight': validated_data['weight'],
            'weight_unit': validated_data['weight_unit'],
            'urgency_level': validated_data['urgency_level'],
        }
        
        # Try to determine vehicle type from items
        vehicle_types = list(set(item['vehicle_type'] for item in validated_data['items']))
        vehicle_type = vehicle_types[0] if vehicle_types else 'Truck'
        quotation_request_data['vehicle_type'] = vehicle_type
        
        # Get or create quotation request based on unique constraints
        quotation_request, created = QuotationRequest.objects.get_or_create(
            customer=customer,
            origin_pincode=validated_data['origin_pincode'],
            destination_pincode=validated_data['destination_pincode'],
            pickup_date=validated_data['pickup_date'].date(),
            drop_date=validated_data['drop_date'].date(),
            defaults=quotation_request_data
        )
        
        # Check if vendor already has a quotation for this request
        existing_quotation = Quotation.objects.filter(
            quotation_request=quotation_request,
            vendor=vendor
        ).first()
        
        if existing_quotation:
            # Update existing quotation
            existing_quotation.vendor_name = validated_data['vendor_name']
            existing_quotation.items = validated_data['items']
            existing_quotation.total_amount = validated_data['total_amount']
            existing_quotation.status = 'pending'
            existing_quotation.save()
            quotation = existing_quotation
            quotation_updated = True
        else:
            # Create new quotation
            quotation = Quotation.objects.create(
                quotation_request=quotation_request,
                vendor=vendor,
                vendor_name=validated_data['vendor_name'],
                items=validated_data['items'],
                total_amount=validated_data['total_amount'],
                status='pending'
            )
            quotation_updated = False
        
        return {
            'quotation_request': quotation_request,
            'quotation': quotation,
            'created_new_request': created,
            'quotation_updated': quotation_updated
        }
