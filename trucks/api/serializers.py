from rest_framework import serializers
from trucks.models import TruckType, Truck, TruckImage, Driver, TruckLocation
from django.contrib.auth import get_user_model

User = get_user_model()

class TruckTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TruckType
        fields = ['id', 'name', 'description', 'created_at']

class TruckImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TruckImage
        fields = ['id', 'image', 'caption', 'is_primary', 'created_at']

class TruckListSerializer(serializers.ModelSerializer):
    """Serializer for listing trucks (basic info)"""
    truck_type = serializers.CharField(source='truck_type.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.phone_number', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Truck
        fields = [
            'id', 'registration_number', 'truck_type', 'capacity', 'make', 'model', 
            'year', 'availability_status', 'base_price_per_km', 'current_location_address',
            'vendor_name', 'vendor_phone', 'primary_image'
        ]

    def get_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return primary_image.image.url if primary_image.image else None
        return None

class TruckDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed truck view"""
    truck_type = TruckTypeSerializer(read_only=True)
    truck_type_id = serializers.IntegerField(write_only=True)
    images = TruckImageSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.phone_number', read_only=True)

    class Meta:
        model = Truck
        fields = [
            'id', 'truck_type', 'truck_type_id', 'registration_number', 'capacity', 
            'make', 'model', 'year', 'color', 'availability_status', 'base_price_per_km',
            'current_location_latitude', 'current_location_longitude', 'current_location_address',
            'vendor_name', 'vendor_phone', 'images', 'is_active', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        validated_data['vendor'] = self.context['request'].user
        return super().create(validated_data)

class DriverSerializer(serializers.ModelSerializer):
    assigned_truck_info = serializers.SerializerMethodField()
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'name', 'phone_number', 'email', 'license_number', 
            'license_expiry_date', 'experience_years', 'assigned_truck',
            'assigned_truck_info', 'profile_image', 'is_available', 
            'vendor_name', 'created_at', 'updated_at'
        ]

    def get_assigned_truck_info(self, obj):
        if obj.assigned_truck:
            return {
                'id': obj.assigned_truck.id,
                'registration_number': obj.assigned_truck.registration_number,
                'truck_type': obj.assigned_truck.truck_type.name
            }
        return None

    def create(self, validated_data):
        validated_data['vendor'] = self.context['request'].user
        return super().create(validated_data)

class TruckSearchSerializer(serializers.Serializer):
    """Serializer for truck search parameters"""
    # Pin code based search (primary)
    origin_pincode = serializers.CharField(max_length=6, required=False, help_text="Origin pin code (6 digits)")
    destination_pincode = serializers.CharField(max_length=6, required=False, help_text="Destination pin code (6 digits)")
    
    # Coordinates based search (fallback)
    pickup_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    pickup_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    delivery_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    delivery_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    
    # Trip details
    pickup_date = serializers.DateTimeField()
    delivery_date = serializers.DateTimeField(required=False)
    weight = serializers.DecimalField(max_digits=8, decimal_places=2, help_text="Weight in tons")
    
    # Truck requirements
    truck_type = serializers.CharField(required=False, help_text="Truck type name")
    capacity_min = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    capacity_max = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    number_of_trucks = serializers.IntegerField(default=1, min_value=1)
    
    # Search parameters
    max_distance = serializers.IntegerField(default=50, help_text="Maximum distance from pickup location in km")
    
    def validate(self, data):
        """Validate that either pin codes or coordinates are provided"""
        has_pincodes = data.get('origin_pincode') and data.get('destination_pincode')
        has_coordinates = (
            data.get('pickup_latitude') and data.get('pickup_longitude') and
            data.get('delivery_latitude') and data.get('delivery_longitude')
        )
        
        if not has_pincodes and not has_coordinates:
            raise serializers.ValidationError(
                "Either provide origin_pincode & destination_pincode or complete coordinates"
            )
        
        # Validate pin codes if provided
        if data.get('origin_pincode'):
            from project.location_utils import validate_pincode
            if not validate_pincode(data['origin_pincode']):
                raise serializers.ValidationError("Invalid origin pin code format")
                
        if data.get('destination_pincode'):
            from project.location_utils import validate_pincode
            if not validate_pincode(data['destination_pincode']):
                raise serializers.ValidationError("Invalid destination pin code format")
        
        return data

class TruckLocationSerializer(serializers.ModelSerializer):
    truck_registration = serializers.CharField(source='truck.registration_number', read_only=True)
    
    class Meta:
        model = TruckLocation
        fields = ['id', 'truck', 'truck_registration', 'latitude', 'longitude', 'address', 'timestamp']

class TruckImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TruckImage
        fields = ['truck', 'image', 'caption', 'is_primary']

    def create(self, validated_data):
        # Ensure only one primary image per truck
        if validated_data.get('is_primary', False):
            TruckImage.objects.filter(truck=validated_data['truck'], is_primary=True).update(is_primary=False)
        return super().create(validated_data)
