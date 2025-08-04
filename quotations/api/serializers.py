from rest_framework import serializers
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation, 
    QuotationRequestItem, Cart, CartItem, QuotationItem
)
from trucks.models import Truck
from django.contrib.auth import get_user_model
import math

User = get_user_model()

# Cart Management Serializers
class CartItemSerializer(serializers.ModelSerializer):
    truck_info = serializers.SerializerMethodField()
    estimated_price = serializers.SerializerMethodField()
    total_capacity = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'truck', 'truck_info', 'quantity', 'item_weight', 
            'item_special_instructions', 'estimated_price', 'total_capacity', 'created_at'
        ]

    def get_truck_info(self, obj):
        return {
            'id': obj.truck.id,
            'registration_number': obj.truck.registration_number,
            'truck_type': obj.truck.truck_type.name,
            'capacity': obj.truck.capacity,
            'make': obj.truck.make,
            'model': obj.truck.model,
            'base_price_per_km': obj.truck.base_price_per_km,
            'availability_status': obj.truck.availability_status,
        }

    def get_estimated_price(self, obj):
        return obj.get_estimated_price()

    def get_total_capacity(self, obj):
        return obj.get_total_capacity()

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    vendor_info = serializers.SerializerMethodField()
    total_trucks = serializers.SerializerMethodField()
    total_capacity = serializers.SerializerMethodField()
    estimated_total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'vendor', 'vendor_info', 'items', 'total_trucks', 
            'total_capacity', 'estimated_total_price', 'created_at', 'updated_at'
        ]

    def get_vendor_info(self, obj):
        return {
            'id': obj.vendor.id,
            'name': obj.vendor.name,
            'phone_number': obj.vendor.phone_number,
        }

    def get_total_trucks(self, obj):
        return obj.get_total_trucks()

    def get_total_capacity(self, obj):
        return obj.get_total_capacity()

    def get_estimated_total_price(self, obj):
        total = 0
        for item in obj.items.all():
            total += item.get_estimated_price()
        return total

class AddToCartSerializer(serializers.Serializer):
    truck_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=10)
    item_weight = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.1)
    item_special_instructions = serializers.CharField(required=False, allow_blank=True)

    def validate_truck_id(self, value):
        try:
            truck = Truck.objects.get(id=value, is_active=True, availability_status='available')
            return truck
        except Truck.DoesNotExist:
            raise serializers.ValidationError("Truck not found or not available")

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=10)
    item_weight = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.1)
    item_special_instructions = serializers.CharField(required=False, allow_blank=True)

# Quotation Request Serializers  
class QuotationRequestItemSerializer(serializers.ModelSerializer):
    truck_info = serializers.SerializerMethodField()
    total_capacity = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationRequestItem
        fields = [
            'id', 'truck', 'truck_info', 'quantity', 'item_weight', 
            'item_special_instructions', 'total_capacity'
        ]

    def get_truck_info(self, obj):
        return {
            'id': obj.truck.id,
            'registration_number': obj.truck.registration_number,
            'truck_type': obj.truck.truck_type.name,
            'capacity': obj.truck.capacity,
            'make': obj.truck.make,
            'model': obj.truck.model,
        }

    def get_total_capacity(self, obj):
        return obj.get_total_capacity()

class QuotationRequestSerializer(serializers.ModelSerializer):
    items = QuotationRequestItemSerializer(many=True, read_only=True)
    vendor_info = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    total_trucks = serializers.SerializerMethodField()
    total_capacity = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationRequest
        fields = [
            'id', 'vendor', 'vendor_info', 'customer_name', 'items',
            'pickup_latitude', 'pickup_longitude', 'pickup_address', 'pickup_date',
            'delivery_latitude', 'delivery_longitude', 'delivery_address', 'expected_delivery_date',
            'cargo_description', 'estimated_total_weight', 'special_instructions', 
            'suggested_total_price', 'suggested_price_notes',
            'distance_km', 'total_trucks', 'total_capacity', 'is_active', 'created_at'
        ]

    def get_vendor_info(self, obj):
        return {
            'id': obj.vendor.id,
            'name': obj.vendor.name,
            'phone_number': obj.vendor.phone_number,
        }

    def get_total_trucks(self, obj):
        return obj.get_total_trucks()

    def get_total_capacity(self, obj):
        return obj.get_total_capacity()

class CreateQuotationRequestSerializer(serializers.Serializer):
    """Serializer for creating quotation request from cart"""
    cart_id = serializers.IntegerField()
    pickup_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    pickup_address = serializers.CharField()
    pickup_date = serializers.DateTimeField()
    delivery_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    delivery_address = serializers.CharField()
    expected_delivery_date = serializers.DateTimeField()
    cargo_description = serializers.CharField(required=False, allow_blank=True)
    estimated_total_weight = serializers.DecimalField(max_digits=8, decimal_places=2)
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    suggested_total_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    suggested_price_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_cart_id(self, value):
        try:
            cart = Cart.objects.get(
                id=value, 
                customer=self.context['request'].user,
                is_active=True
            )
            if cart.items.count() == 0:
                raise serializers.ValidationError("Cart is empty")
            return cart
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart not found")

    def create(self, validated_data):
        cart = validated_data['cart_id']
        
        # Calculate distance
        distance = self.calculate_distance(
            float(validated_data['pickup_latitude']),
            float(validated_data['pickup_longitude']),
            float(validated_data['delivery_latitude']),
            float(validated_data['delivery_longitude'])
        )
        
        # Create quotation request
        quotation_request = QuotationRequest.objects.create(
            customer=self.context['request'].user,
            vendor=cart.vendor,
            pickup_latitude=validated_data['pickup_latitude'],
            pickup_longitude=validated_data['pickup_longitude'],
            pickup_address=validated_data['pickup_address'],
            pickup_date=validated_data['pickup_date'],
            delivery_latitude=validated_data['delivery_latitude'],
            delivery_longitude=validated_data['delivery_longitude'],
            delivery_address=validated_data['delivery_address'],
            expected_delivery_date=validated_data['expected_delivery_date'],
            cargo_description=validated_data.get('cargo_description', ''),
            estimated_total_weight=validated_data['estimated_total_weight'],
            special_instructions=validated_data.get('special_instructions', ''),
            suggested_total_price=validated_data.get('suggested_total_price'),
            suggested_price_notes=validated_data.get('suggested_price_notes', ''),
            distance_km=distance
        )
        
        # Create quotation request items from cart items
        for cart_item in cart.items.all():
            QuotationRequestItem.objects.create(
                quotation_request=quotation_request,
                truck=cart_item.truck,
                quantity=cart_item.quantity,
                item_weight=cart_item.item_weight,
                item_special_instructions=cart_item.item_special_instructions
            )
        
        # Clear the cart
        cart.clear()
        cart.is_active = False
        cart.save()
        
        return quotation_request

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

class QuotationItemSerializer(serializers.ModelSerializer):
    truck_info = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationItem
        fields = [
            'id', 'truck', 'truck_info', 'quantity',
            'unit_base_price', 'unit_fuel_charges', 'unit_toll_charges',
            'unit_loading_charges', 'unit_unloading_charges', 'unit_additional_charges',
            'total_price', 'item_notes'
        ]

    def get_truck_info(self, obj):
        return {
            'id': obj.truck.id,
            'registration_number': obj.truck.registration_number,
            'truck_type': obj.truck.truck_type.name,
            'capacity': obj.truck.capacity,
            'make': obj.truck.make,
            'model': obj.truck.model,
        }

class QuotationSerializer(serializers.ModelSerializer):
    quotation_request_info = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.phone_number', read_only=True)
    customer_name = serializers.CharField(source='quotation_request.customer.name', read_only=True)
    items = QuotationItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_request', 'quotation_request_info', 'vendor_name', 'vendor_phone',
            'customer_name', 'items', 'total_base_price', 'total_fuel_charges', 'total_toll_charges',
            'total_loading_charges', 'total_unloading_charges', 'total_additional_charges', 'total_amount',
            'terms_and_conditions', 'validity_hours', 'customer_suggested_price', 
            'vendor_response_to_suggestion', 'status', 'created_at', 'updated_at'
        ]

    def get_quotation_request_info(self, obj):
        return {
            'id': obj.quotation_request.id,
            'pickup_address': obj.quotation_request.pickup_address,
            'delivery_address': obj.quotation_request.delivery_address,
            'pickup_date': obj.quotation_request.pickup_date,
            'expected_delivery_date': obj.quotation_request.expected_delivery_date,
            'cargo_description': obj.quotation_request.cargo_description,
            'estimated_total_weight': obj.quotation_request.estimated_total_weight,
            'distance_km': obj.quotation_request.distance_km,
            'suggested_total_price': obj.quotation_request.suggested_total_price,
            'suggested_price_notes': obj.quotation_request.suggested_price_notes,
        }

    def create(self, validated_data):
        validated_data['vendor'] = self.context['request'].user
        return super().create(validated_data)

class QuotationNegotiationSerializer(serializers.ModelSerializer):
    initiator_name = serializers.SerializerMethodField()
    
    class Meta:
        model = QuotationNegotiation
        fields = [
            'id', 'quotation', 'initiated_by', 'initiator_name', 'proposed_amount', 'message',
            'proposed_base_price', 'proposed_fuel_charges', 'proposed_toll_charges',
            'proposed_loading_charges', 'proposed_unloading_charges', 'proposed_additional_charges',
            'created_at'
        ]

    def get_initiator_name(self, obj):
        if obj.initiated_by == 'customer':
            return obj.quotation.quotation_request.customer.name
        else:
            return obj.quotation.vendor.name

class QuotationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating quotations"""
    class Meta:
        model = Quotation
        fields = [
            'quotation_request', 'base_price', 'fuel_charges', 'toll_charges',
            'loading_charges', 'unloading_charges', 'additional_charges',
            'terms_and_conditions', 'validity_hours'
        ]

    def create(self, validated_data):
        validated_data['vendor'] = self.context['request'].user
        return super().create(validated_data)

class QuotationUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating quotation status"""
    class Meta:
        model = Quotation
        fields = ['status']

class NegotiationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating negotiations"""
    class Meta:
        model = QuotationNegotiation
        fields = [
            'quotation', 'proposed_amount', 'message',
            'proposed_base_price', 'proposed_fuel_charges', 'proposed_toll_charges',
            'proposed_loading_charges', 'proposed_unloading_charges', 'proposed_additional_charges'
        ]

    def create(self, validated_data):
        # Determine initiator based on user role
        user = self.context['request'].user
        quotation = validated_data['quotation']
        
        if user.role == 'customer' and user == quotation.quotation_request.customer:
            validated_data['initiated_by'] = 'customer'
        elif user.role == 'vendor' and user == quotation.vendor:
            validated_data['initiated_by'] = 'vendor'
        else:
            raise serializers.ValidationError("You are not authorized to negotiate this quotation")
        
        # Update quotation status to negotiating
        quotation.status = 'negotiating'
        quotation.save()
        
        return super().create(validated_data)
