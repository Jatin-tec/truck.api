from rest_framework import serializers
from quotations.models import QuotationRequest, Quotation, QuotationNegotiation
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


class ActualVehicleItemSerializer(serializers.Serializer):
    """Serializer for the actual vehicle item structure from frontend"""
    vehicle_id = serializers.IntegerField()
    vehicle_model = serializers.CharField()
    vehicle_type = serializers.CharField()
    max_weight = serializers.CharField()
    gps_number = serializers.CharField()
    unit_price = serializers.CharField()
    quantity = serializers.IntegerField()
    estimated_delivery = serializers.CharField()


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
        """Create or get quotation request and add quotation"""
        vendor = validated_data['vendor_id']
        
        # Extract search parameters for QuotationRequest
        quotation_request_data = {
            'customer': self.context['request'].user,
            'origin_pincode': validated_data['origin_pincode'],
            'destination_pincode': validated_data['destination_pincode'],
            'pickup_date': validated_data['pickup_date'].date(),
            'drop_date': validated_data['drop_date'].date(),
            'weight': Decimal(validated_data['weight']),
            'weight_unit': validated_data['weight_unit'],
            'vehicle_type': validated_data.get('vehicle_type', 'Mixed'),
            'urgency_level': validated_data['urgency_level'],
        }
        
        # Get or create quotation request
        quotation_request, created = QuotationRequest.objects.get_or_create(
            **quotation_request_data,
            defaults={'is_active': True}
        )
        
        # Transform items to the expected format for storage
        transformed_items = []
        for item in validated_data['items']:
            transformed_item = {
                'vehicle': {
                    'id': str(item['vehicle_id']),
                    'model': item['vehicle_model'],
                    'vehicleType': item['vehicle_type'],
                    'maxWeight': item['max_weight'],
                    'gpsNumber': item['gps_number'],
                    'total': item['unit_price'],
                    'estimatedDelivery': item['estimated_delivery']
                },
                'quantity': item['quantity']
            }
            transformed_items.append(transformed_item)
        
        # Create quotation for this request
        quotation = Quotation.objects.create(
            quotation_request=quotation_request,
            vendor=vendor,
            vendor_name=validated_data['vendor_name'],
            items=transformed_items,
            total_amount=validated_data['total_amount'],
            status='pending'  # Customer request pending vendor confirmation
        )
        
        # ALWAYS create initial customer negotiation to track the quotation request
        customer_proposed_amount = validated_data.get('customer_proposed_amount')
        
        if customer_proposed_amount:
            # Customer has provided a different proposed amount
            negotiation_amount = customer_proposed_amount
            negotiation_message = validated_data.get('customer_negotiation_message', 'Customer price proposal')
            quotation.status = 'negotiating'  # Mark as negotiating since customer proposed different amount
        else:
            # Customer is requesting the vendor's price, create initial negotiation with vendor's amount
            negotiation_amount = validated_data['total_amount']
            negotiation_message = f'Initial quotation request for {validated_data["vendor_name"]} vehicles'
        
        # Create the initial customer negotiation instance
        customer_negotiation = QuotationNegotiation.objects.create(
            quotation=quotation,
            initiated_by='customer',
            proposed_amount=negotiation_amount,
            message=negotiation_message
        )
        
        # Save quotation with updated status
        quotation.save()
        
        return {
            'quotation_request': quotation_request,
            'quotation': quotation,
            'created_new_request': created,
            'customer_negotiation': customer_negotiation
        }


class QuotationCreateLegacySerializer(serializers.Serializer):
    """Legacy serializer for creating quotations with nested searchParams"""
    vendorId = serializers.IntegerField()
    vendorName = serializers.CharField()
    items = QuotationItemSerializer(many=True)
    totalAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    searchParams = SearchParamsSerializer()
    
    # Optional initial negotiation from customer
    customerProposedAmount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    customerNegotiationMessage = serializers.CharField(required=False, allow_blank=True)

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
            status='pending'  # Customer request pending vendor confirmation
        )
        
        # ALWAYS create initial customer negotiation to track the quotation request
        customer_proposed_amount = validated_data.get('customerProposedAmount')
        
        if customer_proposed_amount:
            # Customer has provided a different proposed amount
            negotiation_amount = customer_proposed_amount
            negotiation_message = validated_data.get('customerNegotiationMessage', 'Customer price proposal')
            quotation.status = 'negotiating'  # Mark as negotiating since customer proposed different amount
        else:
            # Customer is requesting the vendor's price, create initial negotiation with vendor's amount
            negotiation_amount = validated_data['totalAmount']
            negotiation_message = f'Initial quotation request for {validated_data["vendorName"]} vehicles'
        
        # Create the initial customer negotiation instance
        customer_negotiation = QuotationNegotiation.objects.create(
            quotation=quotation,
            initiated_by='customer',
            proposed_amount=negotiation_amount,
            message=negotiation_message
        )
        
        # Save quotation with updated status
        quotation.save()
        
        return {
            'quotation_request': quotation_request,
            'quotation': quotation,
            'created_new_request': created,
            'customer_negotiation': customer_negotiation
        }


class QuotationSerializer(serializers.ModelSerializer):
    """Serializer for Quotation model"""
    vendor_name = serializers.CharField(read_only=True)
    quotation_request_id = serializers.IntegerField(source='quotation_request.id', read_only=True)
    negotiations = serializers.SerializerMethodField()
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_request_id', 'vendor', 'vendor_name', 'items',
            'total_amount', 'terms_and_conditions', 'validity_hours', 'negotiations',
            'customer_suggested_price', 'vendor_response_to_suggestion',
            'status', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'vendor', 'vendor_name', 'quotation_request_id', 'created_at', 'updated_at', 'negotiations']

    def get_negotiations(self, obj):
        """Get all negotiations for this quotation"""
        negotiations = QuotationNegotiation.objects.filter(quotation=obj).order_by('created_at')
        serializer = QuotationNegotiationSerializer(negotiations, many=True)
        return serializer.data


class QuotationResponseSerializer(serializers.Serializer):
    """Serializer for quotation creation response"""
    quotation_request = QuotationRequestSerializer()
    quotation = QuotationSerializer()
    created_new_request = serializers.BooleanField()
    message = serializers.CharField()


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
