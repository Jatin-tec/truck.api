from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from django.db.models import Q
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from trucks.models import TruckType, Truck, Driver, TruckImage, TruckLocation
from trucks.api.serializers import (
    TruckTypeSerializer, TruckListSerializer, TruckDetailSerializer,
    DriverSerializer, TruckSearchSerializer, TruckLocationSerializer,
    TruckImageUploadSerializer
)
from quotations.models import Route, RouteStop, RoutePricing
from project.utils import success_response, error_response, validation_error_response, StandardizedResponseMixin
from project.permissions import IsVendor, IsVendorOrReadOnly
from project.location_utils import (
    get_coordinates_from_pincode, calculate_distance, 
    find_nearest_location, get_city_from_pincode
)
import math

# Truck Types
class TruckTypeListView(StandardizedResponseMixin, generics.ListAPIView):
    """List all truck types (public)"""
    queryset = TruckType.objects.all()
    serializer_class = TruckTypeSerializer
    permission_classes = []

# Truck Views
@api_view(['GET'])
@permission_classes([])
def truck_search(request):
    """
    Public API to search trucks based on origin/destination pin codes or coordinates
    Finds trucks available on routes that match the search criteria
    """
    try:
        serializer = TruckSearchSerializer(data=request.GET)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        data = serializer.validated_data
        
        # Get coordinates from pin codes or use provided coordinates
        if data.get('origin_pincode') and data.get('destination_pincode'):
            origin_coords = get_coordinates_from_pincode(data['origin_pincode'])
            dest_coords = get_coordinates_from_pincode(data['destination_pincode'])
            
            if not origin_coords or not dest_coords:
                return error_response("Invalid pin codes or coordinates not found")
            
            pickup_lat, pickup_lng = origin_coords
            delivery_lat, delivery_lng = dest_coords
            origin_city = get_city_from_pincode(data['origin_pincode'])
            dest_city = get_city_from_pincode(data['destination_pincode'])
        else:
            pickup_lat = float(data['pickup_latitude'])
            pickup_lng = float(data['pickup_longitude'])
            delivery_lat = float(data['delivery_latitude'])
            delivery_lng = float(data['delivery_longitude'])
            origin_city = "Unknown"
            dest_city = "Unknown"
        
        # Calculate total distance
        total_distance = calculate_distance(pickup_lat, pickup_lng, delivery_lat, delivery_lng)
        weight = float(data['weight'])
        max_distance = data.get('max_distance', 50)
        number_of_trucks = data.get('number_of_trucks', 1)
        
        # Find matching routes
        matching_routes = find_matching_routes(
            pickup_lat, pickup_lng, delivery_lat, delivery_lng, 
            origin_city, dest_city, max_distance
        )
        
        # Get available trucks from matching routes
        truck_route_combinations = {}  # Dictionary to store best route for each truck
        
        for route_info in matching_routes:
            route = route_info['route']
            vendor = route.vendor
            
            # Get vendor's available trucks
            vendor_trucks = Truck.objects.filter(
                vendor=vendor,
                availability_status='available',
                is_active=True
            )
            
            print(f"Found {vendor_trucks.count()} trucks for vendor {vendor.name or vendor.email} on route {route.route_name}")
            print(f"After filtering, {vendor_trucks.filter(capacity__gte=weight / number_of_trucks).count()} trucks can handle the weight")
            
            # Filter by truck requirements
            if data.get('truck_type'):
                vendor_trucks = vendor_trucks.filter(truck_type__name__icontains=data['truck_type'])
            
            # if data.get('capacity_min'):
            #     vendor_trucks = vendor_trucks.filter(capacity__gte=data['capacity_min'])
            
            # if data.get('capacity_max'):
            #     vendor_trucks = vendor_trucks.filter(capacity__lte=data['capacity_max'])
            
            print(f"data.get('truck_type'): {data.get('truck_type')}, data.get('capacity_min'): {data.get('capacity_min')}, data.get('capacity_max'): {data.get('capacity_max')}")
            
            # Filter trucks that can handle the weight
            vendor_trucks = vendor_trucks.filter(capacity__gte=weight / number_of_trucks)
            
            for truck in vendor_trucks:
                # Get route pricing for this truck type
                route_pricing = RoutePricing.objects.filter(
                    route=route,
                    truck_type=truck.truck_type,
                    is_active=True
                ).first()
                
                # Calculate estimated price
                if route_pricing:
                    estimated_price = calculate_route_price(route_pricing, total_distance, weight)
                else:
                    # Fallback to base price per km
                    estimated_price = float(truck.base_price_per_km) * total_distance
                
                # Check if we already have this truck with a better price
                truck_key = truck.id
                if truck_key in truck_route_combinations:
                    if estimated_price >= truck_route_combinations[truck_key]['estimated_price']:
                        print(f"Skipping truck {truck.registration_number} on route {route.route_name} (price: {estimated_price}) - already have better price: {truck_route_combinations[truck_key]['estimated_price']}")
                        continue  # Skip this route as we have a better price for this truck
                    else:
                        print(f"Updating truck {truck.registration_number} with better route {route.route_name} (price: {estimated_price} vs {truck_route_combinations[truck_key]['estimated_price']})")
                
                # Serialize truck data
                truck_data = TruckListSerializer(truck).data
                truck_data.update({
                    'route_id': route.id,
                    'route_name': route.route_name,
                    'total_distance': round(total_distance, 2),
                    'estimated_price': round(estimated_price, 2),
                    'estimated_price_per_truck': round(estimated_price / number_of_trucks, 2),
                    'can_handle_weight': truck.capacity >= weight / number_of_trucks,
                    'route_frequency': route.route_frequency,
                    'estimated_duration_hours': float(route.estimated_duration_hours),
                    'vendor_id': vendor.id,
                    'origin_city': origin_city,
                    'destination_city': dest_city,
                    'distance_from_origin': route_info.get('origin_distance', 0),
                    'distance_from_destination': route_info.get('dest_distance', 0),
                })
                
                # Add route pricing details if available
                if route_pricing:
                    truck_data.update({
                        'base_price': float(route_pricing.base_price),
                        'fuel_charges': float(route_pricing.fuel_charges),
                        'toll_charges': float(route_pricing.toll_charges),
                        'loading_charges': float(route_pricing.loading_charges),
                        'unloading_charges': float(route_pricing.unloading_charges),
                    })
                
                # Store the best option for this truck
                truck_route_combinations[truck_key] = truck_data
        
        # Convert to list
        available_trucks = list(truck_route_combinations.values())
        
        # Sort by estimated price
        available_trucks.sort(key=lambda x: x['estimated_price'])
        
        # Prepare response
        response_data = {
            'trucks': available_trucks,
            'total_found': len(available_trucks),
            'search_criteria': {
                'origin_city': origin_city,
                'destination_city': dest_city,
                'total_distance_km': round(total_distance, 2),
                'weight_tons': weight,
                'number_of_trucks': number_of_trucks,
                'pickup_date': data['pickup_date'].isoformat(),
                'delivery_date': data.get('delivery_date').isoformat() if data.get('delivery_date') else None,
            },
            'matching_routes': len(matching_routes),
        }
        
        return success_response(
            data=response_data,
            message=f"Found {len(available_trucks)} trucks on {len(matching_routes)} routes"
        )
        
    except Exception as e:
        return error_response(str(e), status.HTTP_400_BAD_REQUEST)


def find_matching_routes(pickup_lat, pickup_lng, delivery_lat, delivery_lng, origin_city, dest_city, max_distance=50):
    """
    Find routes that match the search criteria
    Returns list of routes with distance information
    """
    matching_routes = []
    
    # Get all active routes
    active_routes = Route.objects.filter(is_active=True)
    
    for route in active_routes:
        route_match = analyze_route_match(
            route, pickup_lat, pickup_lng, delivery_lat, delivery_lng, 
            origin_city, dest_city, max_distance
        )
        
        if route_match['matches']:
            matching_routes.append({
                'route': route,
                'match_type': route_match['match_type'],
                'origin_distance': route_match['origin_distance'],
                'dest_distance': route_match['dest_distance'],
                'route_score': route_match['score']
            })
    
    # Sort by route score (lower is better)
    matching_routes.sort(key=lambda x: x['route_score'])
    
    return matching_routes


def analyze_route_match(route, pickup_lat, pickup_lng, delivery_lat, delivery_lng, origin_city, dest_city, max_distance):
    """
    Analyze how well a route matches the search criteria
    """
    result = {
        'matches': False,
        'match_type': 'none',
        'origin_distance': float('inf'),
        'dest_distance': float('inf'),
        'score': float('inf')
    }
    
    # Check if cities match exactly
    if origin_city and dest_city:
        if (route.origin_city.lower() == origin_city.lower() and 
            route.destination_city.lower() == dest_city.lower()):
            result.update({
                'matches': True,
                'match_type': 'exact_city_match',
                'origin_distance': 0,
                'dest_distance': 0,
                'score': 0
            })
            return result
    
    # Calculate distances to route origin and destination
    origin_distance = calculate_distance(
        pickup_lat, pickup_lng,
        float(route.origin_latitude), float(route.origin_longitude)
    )
    
    dest_distance = calculate_distance(
        delivery_lat, delivery_lng,
        float(route.destination_latitude), float(route.destination_longitude)
    )
    
    # Check if both origin and destination are within acceptable distance
    if origin_distance <= max_distance and dest_distance <= max_distance:
        result.update({
            'matches': True,
            'match_type': 'direct_route',
            'origin_distance': origin_distance,
            'dest_distance': dest_distance,
            'score': origin_distance + dest_distance
        })
        return result
    
    # Check if route passes through the pickup/delivery locations via stops
    stop_match = check_route_stops_match(
        route, pickup_lat, pickup_lng, delivery_lat, delivery_lng, max_distance
    )
    
    if stop_match['matches']:
        result.update({
            'matches': True,
            'match_type': 'via_stops',
            'origin_distance': stop_match['pickup_distance'],
            'dest_distance': stop_match['delivery_distance'],
            'score': stop_match['total_distance']
        })
        return result
    
    # Check if it's a partial match (one end matches)
    if origin_distance <= max_distance or dest_distance <= max_distance:
        result.update({
            'matches': True,
            'match_type': 'partial_match',
            'origin_distance': origin_distance,
            'dest_distance': dest_distance,
            'score': min(origin_distance, dest_distance) + 100  # Higher score for partial matches
        })
    
    return result


def check_route_stops_match(route, pickup_lat, pickup_lng, delivery_lat, delivery_lng, max_distance):
    """
    Check if route stops can serve as pickup/delivery points
    """
    route_stops = RouteStop.objects.filter(route=route).order_by('stop_order')
    
    pickup_stop = None
    delivery_stop = None
    pickup_distance = float('inf')
    delivery_distance = float('inf')
    
    # Check route origin and destination
    all_points = [
        {
            'lat': float(route.origin_latitude),
            'lng': float(route.origin_longitude),
            'order': 0,
            'type': 'origin'
        },
        {
            'lat': float(route.destination_latitude),
            'lng': float(route.destination_longitude),
            'order': 999,
            'type': 'destination'
        }
    ]
    
    # Add route stops
    for stop in route_stops:
        all_points.append({
            'lat': float(stop.stop_latitude),
            'lng': float(stop.stop_longitude),
            'order': stop.stop_order,
            'type': 'stop',
            'can_pickup': stop.can_pickup,
            'can_drop': stop.can_drop
        })
    
    # Find best pickup point
    for point in all_points:
        if point['type'] == 'origin' or (point['type'] == 'stop' and point.get('can_pickup', True)):
            distance = calculate_distance(pickup_lat, pickup_lng, point['lat'], point['lng'])
            if distance <= max_distance and distance < pickup_distance:
                pickup_distance = distance
                pickup_stop = point
    
    # Find best delivery point (must be after pickup point)
    for point in all_points:
        if point['type'] == 'destination' or (point['type'] == 'stop' and point.get('can_drop', True)):
            if pickup_stop and point['order'] > pickup_stop['order']:
                distance = calculate_distance(delivery_lat, delivery_lng, point['lat'], point['lng'])
                if distance <= max_distance and distance < delivery_distance:
                    delivery_distance = distance
                    delivery_stop = point
    
    return {
        'matches': pickup_stop is not None and delivery_stop is not None,
        'pickup_distance': pickup_distance if pickup_stop else float('inf'),
        'delivery_distance': delivery_distance if delivery_stop else float('inf'),
        'total_distance': (pickup_distance + delivery_distance) if (pickup_stop and delivery_stop) else float('inf')
    }


def calculate_route_price(route_pricing, distance_km, weight_tons):
    """
    Calculate estimated price based on route pricing
    """
    base_price = float(route_pricing.base_price)
    price_per_km = float(route_pricing.price_per_km)
    fuel_charges = float(route_pricing.fuel_charges)
    toll_charges = float(route_pricing.toll_charges)
    loading_charges = float(route_pricing.loading_charges)
    unloading_charges = float(route_pricing.unloading_charges)
    
    # Calculate total price
    distance_price = price_per_km * distance_km
    total_price = (
        base_price + 
        distance_price + 
        fuel_charges + 
        toll_charges + 
        loading_charges + 
        unloading_charges
    )
    
    # Apply weight factor if weight exceeds standard capacity
    max_weight = float(route_pricing.max_weight_capacity)
    if weight_tons > max_weight:
        weight_factor = weight_tons / max_weight
        total_price *= weight_factor
    
    return total_price


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

class TruckListCreateView(StandardizedResponseMixin, generics.ListCreateAPIView):
    """
    List all trucks or create a new truck
    GET: Public (anyone can list trucks)
    POST: Vendor only
    """
    serializer_class = TruckListSerializer
    permission_classes = [IsVendorOrReadOnly]
    
    def get_queryset(self):
        queryset = Truck.objects.filter(is_active=True)
        vendor_id = self.request.query_params.get('vendor', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TruckDetailSerializer
        return TruckListSerializer

class TruckDetailView(StandardizedResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a truck
    GET: Public
    PUT/PATCH/DELETE: Vendor owner only
    """
    queryset = Truck.objects.filter(is_active=True)
    serializer_class = TruckDetailSerializer
    permission_classes = [IsVendorOrReadOnly]

class VendorTrucksView(StandardizedResponseMixin, generics.ListAPIView):
    """List trucks for authenticated vendor"""
    serializer_class = TruckDetailSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Truck.objects.filter(vendor=self.request.user, is_active=True)

# Driver Views
class DriverListCreateView(StandardizedResponseMixin, generics.ListCreateAPIView):
    """
    List drivers or create a new driver
    Vendor only
    """
    serializer_class = DriverSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Driver.objects.filter(vendor=self.request.user, is_active=True)

class DriverDetailView(StandardizedResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a driver
    Vendor owner only
    """
    serializer_class = DriverSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Driver.objects.filter(vendor=self.request.user, is_active=True)

# Truck Images
class TruckImageUploadView(StandardizedResponseMixin, generics.CreateAPIView):
    """Upload images for a truck"""
    serializer_class = TruckImageUploadSerializer
    permission_classes = [IsVendor]

    def perform_create(self, serializer):
        truck = serializer.validated_data['truck']
        # Ensure vendor owns the truck
        if truck.vendor != self.request.user:
            raise permissions.PermissionDenied("You can only upload images for your own trucks")
        serializer.save()

class TruckImageListView(StandardizedResponseMixin, generics.ListAPIView):
    """List images for a specific truck"""
    serializer_class = TruckImageUploadSerializer
    permission_classes = []
    
    def get_queryset(self):
        truck_id = self.kwargs['truck_id']
        return TruckImage.objects.filter(truck_id=truck_id)

# Location Tracking
class UpdateTruckLocationView(APIView):
    """Update truck location (for real-time tracking)"""
    permission_classes = [IsVendor]
    
    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def post(self, request, truck_id):
        try:
            truck = Truck.objects.get(id=truck_id, vendor=request.user)
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            address = request.data.get('address', '')
            
            if not latitude or not longitude:
                return error_response(
                    'Latitude and longitude are required', 
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Update truck's current location
            truck.current_location_latitude = latitude
            truck.current_location_longitude = longitude
            truck.current_location_address = address
            truck.save()
            
            # Create location history entry
            TruckLocation.objects.create(
                truck=truck,
                latitude=latitude,
                longitude=longitude,
                address=address
            )
            
            return success_response(message='Location updated successfully')
            
        except Truck.DoesNotExist:
            return error_response(
                'Truck not found or not owned by you', 
                status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

class TruckLocationHistoryView(StandardizedResponseMixin, generics.ListAPIView):
    """Get location history for a truck"""
    serializer_class = TruckLocationSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        truck_id = self.kwargs['truck_id']
        return TruckLocation.objects.filter(
            truck_id=truck_id, 
            truck__vendor=self.request.user
        )[:50]  # Last 50 locations
