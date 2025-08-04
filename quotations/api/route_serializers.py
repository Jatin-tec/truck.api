from rest_framework import serializers
from quotations.models import (
    Route, RouteStop, RoutePricing, CustomerEnquiry, 
    PriceRange, VendorEnquiryRequest
)
from trucks.models import TruckType
from django.contrib.auth import get_user_model
from django.utils import timezone
import math

User = get_user_model()

# Route Management Serializers (Vendor)
class RouteStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteStop
        fields = [
            'id', 'stop_city', 'stop_state', 'stop_latitude', 'stop_longitude',
            'stop_order', 'distance_from_origin', 'distance_to_destination',
            'estimated_arrival_time', 'can_pickup', 'can_drop'
        ]

class RoutePricingSerializer(serializers.ModelSerializer):
    truck_type_name = serializers.CharField(source='truck_type.name', read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = RoutePricing
        fields = [
            'id', 'truck_type', 'truck_type_name', 'from_city', 'to_city',
            'segment_distance_km', 'base_price', 'price_per_km', 'fuel_charges',
            'toll_charges', 'loading_charges', 'unloading_charges', 'min_price',
            'max_price', 'max_weight_capacity', 'available_vehicles', 'total_price'
        ]

    def get_total_price(self, obj):
        return obj.get_total_price()

class RouteSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, read_only=True)
    pricing = RoutePricingSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'vendor', 'vendor_name', 'route_name', 'origin_city', 'origin_state',
            'origin_latitude', 'origin_longitude', 'destination_city', 'destination_state',
            'destination_latitude', 'destination_longitude', 'total_distance_km',
            'estimated_duration_hours', 'route_frequency', 'is_active',
            'max_vehicles_per_trip', 'notes', 'stops', 'pricing', 'created_at'
        ]
        read_only_fields = ['vendor']

class CreateRouteSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, required=False)
    pricing = RoutePricingSerializer(many=True, required=False)
    
    class Meta:
        model = Route
        fields = [
            'route_name', 'origin_city', 'origin_state', 'origin_latitude',
            'origin_longitude', 'destination_city', 'destination_state',
            'destination_latitude', 'destination_longitude', 'total_distance_km',
            'estimated_duration_hours', 'route_frequency', 'max_vehicles_per_trip',
            'notes', 'stops', 'pricing'
        ]

    def create(self, validated_data):
        stops_data = validated_data.pop('stops', [])
        pricing_data = validated_data.pop('pricing', [])
        
        # Set vendor from context
        validated_data['vendor'] = self.context['request'].user
        
        route = Route.objects.create(**validated_data)
        
        # Create stops
        for stop_data in stops_data:
            RouteStop.objects.create(route=route, **stop_data)
        
        # Create pricing
        for price_data in pricing_data:
            RoutePricing.objects.create(route=route, **price_data)
        
        return route

# Customer Enquiry Serializers
class CustomerEnquirySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    truck_type_name = serializers.CharField(source='truck_type.name', read_only=True)
    assigned_manager_name = serializers.CharField(source='assigned_manager.name', read_only=True)
    
    class Meta:
        model = CustomerEnquiry
        fields = [
            'id', 'customer', 'customer_name', 'pickup_latitude', 'pickup_longitude',
            'pickup_address', 'pickup_city', 'pickup_state', 'pickup_date',
            'delivery_latitude', 'delivery_longitude', 'delivery_address',
            'delivery_city', 'delivery_state', 'expected_delivery_date',
            'truck_type', 'truck_type_name', 'number_of_vehicles', 'total_weight',
            'cargo_description', 'special_instructions', 'estimated_distance_km',
            'is_miscellaneous_route', 'status', 'assigned_manager', 'assigned_manager_name',
            'budget_min', 'budget_max', 'preferred_vendor_size', 'created_at'
        ]
        read_only_fields = ['customer', 'status', 'assigned_manager', 'estimated_distance_km']

class CreateEnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerEnquiry
        fields = [
            'pickup_latitude', 'pickup_longitude', 'pickup_address', 'pickup_city',
            'pickup_state', 'pickup_date', 'delivery_latitude', 'delivery_longitude',
            'delivery_address', 'delivery_city', 'delivery_state', 'expected_delivery_date',
            'truck_type', 'number_of_vehicles', 'total_weight', 'cargo_description',
            'special_instructions', 'budget_min', 'budget_max', 'preferred_vendor_size'
        ]

    def create(self, validated_data):
        # Set customer from context
        validated_data['customer'] = self.context['request'].user
        
        # Calculate distance
        distance = self.calculate_distance(
            float(validated_data['pickup_latitude']),
            float(validated_data['pickup_longitude']),
            float(validated_data['delivery_latitude']),
            float(validated_data['delivery_longitude'])
        )
        validated_data['estimated_distance_km'] = distance
        
        return CustomerEnquiry.objects.create(**validated_data)

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

# Price Range Serializers (Customer View - No Vendor Details)
class PriceRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceRange
        fields = [
            'id', 'min_price', 'max_price', 'recommended_price', 'vehicles_available',
            'vendors_count', 'chance_of_getting_deal', 'route_type',
            'estimated_duration_hours', 'includes_fuel', 'includes_tolls',
            'includes_loading', 'additional_charges_note'
        ]

class EnquiryWithPriceRangesSerializer(serializers.ModelSerializer):
    price_ranges = PriceRangeSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    truck_type_name = serializers.CharField(source='truck_type.name', read_only=True)
    
    class Meta:
        model = CustomerEnquiry
        fields = [
            'id', 'customer_name', 'pickup_city', 'pickup_state', 'delivery_city',
            'delivery_state', 'pickup_date', 'expected_delivery_date', 'truck_type_name',
            'number_of_vehicles', 'total_weight', 'cargo_description', 'status',
            'estimated_distance_km', 'price_ranges', 'created_at'
        ]

# Manager Serializers
class VendorEnquiryRequestSerializer(serializers.ModelSerializer):
    enquiry_details = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    manager_name = serializers.CharField(source='sent_by_manager.name', read_only=True)
    route_name = serializers.CharField(source='route.route_name', read_only=True)
    
    class Meta:
        model = VendorEnquiryRequest
        fields = [
            'id', 'enquiry', 'enquiry_details', 'vendor', 'vendor_name', 'route',
            'route_name', 'sent_by_manager', 'manager_name', 'suggested_price',
            'manager_notes', 'urgency_level', 'status', 'vendor_response_price',
            'vendor_response_notes', 'response_date', 'valid_until', 'created_at'
        ]

    def get_enquiry_details(self, obj):
        return {
            'pickup_city': obj.enquiry.pickup_city,
            'delivery_city': obj.enquiry.delivery_city,
            'pickup_date': obj.enquiry.pickup_date,
            'truck_type': obj.enquiry.truck_type.name,
            'number_of_vehicles': obj.enquiry.number_of_vehicles,
            'total_weight': obj.enquiry.total_weight,
            'cargo_description': obj.enquiry.cargo_description
        }

class CreateVendorEnquiryRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorEnquiryRequest
        fields = [
            'enquiry', 'vendor', 'price_range', 'route', 'suggested_price',
            'manager_notes', 'urgency_level', 'valid_until'
        ]

    def create(self, validated_data):
        # Set manager from context
        validated_data['sent_by_manager'] = self.context['request'].user
        return VendorEnquiryRequest.objects.create(**validated_data)

# Vendor Response Serializers
class VendorResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorEnquiryRequest
        fields = ['vendor_response_price', 'vendor_response_notes']

    def update(self, instance, validated_data):
        instance.vendor_response_price = validated_data.get('vendor_response_price', instance.vendor_response_price)
        instance.vendor_response_notes = validated_data.get('vendor_response_notes', instance.vendor_response_notes)
        instance.status = 'quoted'
        instance.response_date = timezone.now()
        instance.save()
        return instance

# Manager Dashboard Serializers
class ManagerDashboardEnquirySerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    truck_type_name = serializers.CharField(source='truck_type.name', read_only=True)
    price_ranges_count = serializers.SerializerMethodField()
    vendor_requests_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerEnquiry
        fields = [
            'id', 'customer_name', 'pickup_city', 'delivery_city', 'pickup_date',
            'truck_type_name', 'number_of_vehicles', 'status', 'is_miscellaneous_route',
            'price_ranges_count', 'vendor_requests_count', 'created_at'
        ]

    def get_price_ranges_count(self, obj):
        return obj.price_ranges.count()

    def get_vendor_requests_count(self, obj):
        return obj.vendor_requests.count()
