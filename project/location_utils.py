"""
Utility functions for handling pin codes and location services
"""
import requests
from django.conf import settings
from typing import Tuple, Optional
import re


def validate_pincode(pincode: str) -> bool:
    """Validate Indian pin code format (6 digits)"""
    return bool(re.match(r'^\d{6}$', pincode))


def get_coordinates_from_pincode(pincode: str) -> Optional[Tuple[float, float]]:
    """
    Get latitude and longitude from Indian pin code
    Using a free API service for demonstration
    """
    if not validate_pincode(pincode):
        return None
    
    try:
        # Using positionstack API (free tier available)
        # You can replace this with any other geocoding service
        # For production, consider using Google Maps API or similar
        
        # Mock data for common pin codes - replace with actual API call
        pincode_mock_data = {
            '110001': (28.6139, 77.2090),  # New Delhi
            '400001': (18.9322, 72.8264),  # Mumbai
            '560001': (12.9716, 77.5946),  # Bangalore
            '600001': (13.0827, 80.2707),  # Chennai
            '700001': (22.5726, 88.3639),  # Kolkata
            '500001': (17.3850, 78.4867),  # Hyderabad
            '411001': (18.5204, 73.8567),  # Pune
            '380001': (23.0225, 72.5714),  # Ahmedabad
            '302001': (26.9124, 75.7873),  # Jaipur
            '226001': (26.8467, 80.9462),  # Lucknow
        }
        
        if pincode in pincode_mock_data:
            return pincode_mock_data[pincode]
        
        # For production, implement actual API call:
        # url = f"http://api.positionstack.com/v1/forward"
        # params = {
        #     'access_key': settings.POSITIONSTACK_API_KEY,
        #     'query': f"{pincode}, India",
        #     'limit': 1
        # }
        # response = requests.get(url, params=params)
        # if response.status_code == 200:
        #     data = response.json()
        #     if data.get('data') and len(data['data']) > 0:
        #         location = data['data'][0]
        #         return (location['latitude'], location['longitude'])
        
        return None
        
    except Exception as e:
        print(f"Error getting coordinates for pincode {pincode}: {e}")
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    import math
    
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def find_nearest_location(target_lat: float, target_lon: float, locations: list, max_distance: float = 50) -> list:
    """
    Find locations within max_distance from target coordinates
    Returns list of locations with distance information
    """
    nearby_locations = []
    
    for location in locations:
        if hasattr(location, 'latitude') and hasattr(location, 'longitude'):
            if location.latitude and location.longitude:
                distance = calculate_distance(
                    target_lat, target_lon,
                    float(location.latitude), float(location.longitude)
                )
                if distance <= max_distance:
                    location_data = {
                        'object': location,
                        'distance': round(distance, 2)
                    }
                    nearby_locations.append(location_data)
    
    # Sort by distance
    nearby_locations.sort(key=lambda x: x['distance'])
    return nearby_locations


def get_city_from_pincode(pincode: str) -> Optional[str]:
    """Get city name from pin code (mock implementation)"""
    if not validate_pincode(pincode):
        return None
    
    # Mock data - replace with actual API call
    pincode_to_city = {
        '110001': 'New Delhi',
        '400001': 'Mumbai',
        '560001': 'Bangalore',
        '600001': 'Chennai',
        '700001': 'Kolkata',
        '500001': 'Hyderabad',
        '411001': 'Pune',
        '380001': 'Ahmedabad',
        '302001': 'Jaipur',
        '226001': 'Lucknow',
    }
    
    return pincode_to_city.get(pincode)
