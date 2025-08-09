#!/usr/bin/env python
import os
import django
import sys
import json

# Add the project directory to the path
sys.path.append('/home/jatin/WorkSpace/personal/TruckRent/truck.api')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from authentication.models import CustomUser
from trucks.models import Truck

def test_quotation_api():
    """Test the quotation creation API with sample data"""
    
    # Check available test data
    print('=== AVAILABLE TEST DATA ===')
    customers = CustomUser.objects.filter(role='customer')
    vendors = CustomUser.objects.filter(role='vendor')
    trucks = Truck.objects.filter(is_active=True)
    
    print(f"Customers: {customers.count()}")
    if customers.exists():
        customer = customers.first()
        print(f"Sample customer: {customer.email} (ID: {customer.id})")
    
    print(f"Vendors: {vendors.count()}")
    if vendors.exists():
        vendor = vendors.first()
        print(f"Sample vendor: {vendor.email} (ID: {vendor.id})")
        
    print(f"Trucks: {trucks.count()}")
    if trucks.exists():
        truck = trucks.first()
        print(f"Sample truck: {truck.id} - {truck.make} {truck.model}")
    
    # Generate a sample request body for testing
    if customers.exists() and vendors.exists() and trucks.exists():
        sample_request = {
            "vendor_id": str(vendor.id),
            "vendor_name": vendor.name or "Test Vendor",
            "total_amount": 12131.295,
            "origin_pincode": "560001",
            "destination_pincode": "411001", 
            "pickup_date": "2025-08-09T10:45:05.333Z",
            "drop_date": "2025-08-10T10:45:05.333Z",
            "weight": "3",
            "weight_unit": "tonnes",
            "urgency_level": "standard",
            "items": [
                {
                    "vehicle_id": truck.id,
                    "vehicle_model": f"{truck.make} {truck.model}",
                    "vehicle_type": truck.truck_type.name if truck.truck_type else "Medium Truck",
                    "max_weight": str(truck.capacity),
                    "gps_number": truck.registration_number,
                    "unit_price": "₹12,131.295",
                    "quantity": 1,
                    "estimated_delivery": "13 August 2025"
                }
            ]
        }
        
        print('\n=== SAMPLE REQUEST BODY ===')
        print(json.dumps(sample_request, indent=2))
        
        print('\n=== API ENDPOINT ===')
        print('POST /api/quotations/requests/create/')
        print('Authorization: Bearer <customer_jwt_token>')
        print('Content-Type: application/json')

if __name__ == '__main__':
    test_quotation_api()
