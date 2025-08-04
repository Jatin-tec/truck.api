"""
Management command to create sample data for the truck rental application
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from trucks.models import TruckType, Truck, Driver
from quotations.models import Route, RouteStop, RoutePricing
from decimal import Decimal
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for the truck rental application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            dest='clear',
            help='Clear existing data before creating new sample data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_existing_data()
        
        self.stdout.write('Creating sample data...')
        
        # Create users
        self.create_users()
        
        # Create truck types
        self.create_truck_types()
        
        # Create routes and route pricing
        self.create_routes()
        
        # Create trucks and drivers
        self.create_trucks_and_drivers()
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        
        # Print sample API endpoints for testing
        self.print_test_endpoints()

    def clear_existing_data(self):
        self.stdout.write('Clearing existing sample data...')
        
        # Clear in reverse order of dependencies
        RoutePricing.objects.all().delete()
        RouteStop.objects.all().delete()
        Route.objects.all().delete()
        Driver.objects.all().delete()
        Truck.objects.all().delete()
        TruckType.objects.all().delete()
        
        # Clear vendor and customer users (keep admin)
        User.objects.filter(role__in=['vendor', 'customer']).delete()
        
        self.stdout.write('Existing data cleared!')

    def create_users(self):
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email='admin@truckrent.com',
            defaults={
                'name': 'Admin User',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'phone_number': '+911234567890'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write("Created admin user")

        # Create vendor users
        vendor_data = [
            {
                'email': 'vendor1@truckrent.com',
                'name': 'Mumbai Transport Co.',
                'phone_number': '+919876543210',
                'password': 'vendor123'
            },
            {
                'email': 'vendor2@truckrent.com', 
                'name': 'Delhi Logistics Ltd.',
                'phone_number': '+919876543211',
                'password': 'vendor123'
            },
            {
                'email': 'vendor3@truckrent.com',
                'name': 'Bangalore Freight Services',
                'phone_number': '+919876543212',
                'password': 'vendor123'
            },
            {
                'email': 'vendor4@truckrent.com',
                'name': 'Chennai Express Transport',
                'phone_number': '+919876543213',
                'password': 'vendor123'
            },
            {
                'email': 'vendor5@truckrent.com',
                'name': 'Kolkata Cargo Movers',
                'phone_number': '+919876543214',
                'password': 'vendor123'
            }
        ]

        for vendor_info in vendor_data:
            vendor, created = User.objects.get_or_create(
                email=vendor_info['email'],
                defaults={
                    'name': vendor_info['name'],
                    'role': 'vendor',
                    'phone_number': vendor_info['phone_number']
                }
            )
            if created:
                vendor.set_password(vendor_info['password'])
                vendor.save()
                self.stdout.write(f"Created vendor: {vendor.name}")

        # Create customer users
        customer_data = [
            {
                'email': 'customer1@example.com',
                'name': 'Rajesh Kumar',
                'phone_number': '+919123456789',
                'password': 'customer123'
            },
            {
                'email': 'customer2@example.com',
                'name': 'Priya Sharma',
                'phone_number': '+919123456788',
                'password': 'customer123'
            },
            {
                'email': 'customer3@example.com',
                'name': 'Amit Patel',
                'phone_number': '+919123456787',
                'password': 'customer123'
            }
        ]

        for customer_info in customer_data:
            customer, created = User.objects.get_or_create(
                email=customer_info['email'],
                defaults={
                    'name': customer_info['name'],
                    'role': 'customer',
                    'phone_number': customer_info['phone_number']
                }
            )
            if created:
                customer.set_password(customer_info['password'])
                customer.save()
                self.stdout.write(f"Created customer: {customer.name}")

    def create_truck_types(self):
        truck_types_data = [
            {
                'name': 'Mini Truck',
                'description': 'Small trucks for local deliveries, capacity up to 1 ton'
            },
            {
                'name': 'Small Truck', 
                'description': 'Compact trucks for city transport, capacity 1-3 tons'
            },
            {
                'name': 'Medium Truck',
                'description': 'Medium-sized trucks for regional transport, capacity 3-7 tons'
            },
            {
                'name': 'Large Truck',
                'description': 'Heavy-duty trucks for long-haul transport, capacity 7+ tons'
            },
            {
                'name': 'Container Truck',
                'description': 'Specialized trucks for container transport'
            }
        ]

        for truck_type_info in truck_types_data:
            truck_type, created = TruckType.objects.get_or_create(
                name=truck_type_info['name'],
                defaults={
                    'description': truck_type_info['description']
                }
            )
            if created:
                self.stdout.write(f"Created truck type: {truck_type.name}")

    def create_routes(self):
        """Create sample routes between major Indian cities"""
        vendors = User.objects.filter(role='vendor')
        truck_types = TruckType.objects.all()
        
        # Define popular routes
        route_data = [
            # Mumbai-Delhi corridor
            {
                'route_name': 'Mumbai to Delhi Express',
                'origin': 'Mumbai',
                'destination': 'Delhi',
                'origin_coords': {'lat': 19.0760, 'lng': 72.8777},
                'dest_coords': {'lat': 28.7041, 'lng': 77.1025},
                'frequency': 'daily',
                'duration': 24,
                'vendor_index': 0,
                'stops': [
                    {'city': 'Nashik', 'lat': 19.9975, 'lng': 73.7898, 'order': 1},
                    {'city': 'Indore', 'lat': 22.7196, 'lng': 75.8577, 'order': 2},
                    {'city': 'Gwalior', 'lat': 26.2183, 'lng': 78.1828, 'order': 3}
                ]
            },
            {
                'route_name': 'Delhi to Mumbai Highway',
                'origin': 'Delhi',
                'destination': 'Mumbai',
                'origin_coords': {'lat': 28.7041, 'lng': 77.1025},
                'dest_coords': {'lat': 19.0760, 'lng': 72.8777},
                'frequency': 'daily',
                'duration': 24,
                'vendor_index': 1,
                'stops': [
                    {'city': 'Jaipur', 'lat': 26.9124, 'lng': 75.7873, 'order': 1},
                    {'city': 'Udaipur', 'lat': 24.5854, 'lng': 73.7125, 'order': 2},
                    {'city': 'Ahmedabad', 'lat': 23.0225, 'lng': 72.5714, 'order': 3}
                ]
            },
            # Bangalore-Chennai corridor
            {
                'route_name': 'Bangalore Chennai Connect',
                'origin': 'Bangalore',
                'destination': 'Chennai',
                'origin_coords': {'lat': 12.9716, 'lng': 77.5946},
                'dest_coords': {'lat': 13.0827, 'lng': 80.2707},
                'frequency': 'daily',
                'duration': 6,
                'vendor_index': 2,
                'stops': [
                    {'city': 'Hosur', 'lat': 12.7409, 'lng': 77.8253, 'order': 1},
                    {'city': 'Krishnagiri', 'lat': 12.5266, 'lng': 78.2150, 'order': 2}
                ]
            },
            {
                'route_name': 'Chennai to Bangalore Route',
                'origin': 'Chennai',
                'destination': 'Bangalore',
                'origin_coords': {'lat': 13.0827, 'lng': 80.2707},
                'dest_coords': {'lat': 12.9716, 'lng': 77.5946},
                'frequency': 'daily',
                'duration': 6,
                'vendor_index': 3,
                'stops': [
                    {'city': 'Vellore', 'lat': 12.9165, 'lng': 79.1325, 'order': 1},
                    {'city': 'Hosur', 'lat': 12.7409, 'lng': 77.8253, 'order': 2}
                ]
            },
            # Mumbai-Pune corridor
            {
                'route_name': 'Mumbai Pune Expressway',
                'origin': 'Mumbai',
                'destination': 'Pune',
                'origin_coords': {'lat': 19.0760, 'lng': 72.8777},
                'dest_coords': {'lat': 18.5204, 'lng': 73.8567},
                'frequency': 'multiple_daily',
                'duration': 3,
                'vendor_index': 0,
                'stops': [
                    {'city': 'Lonavala', 'lat': 18.7537, 'lng': 73.4068, 'order': 1}
                ]
            },
            # Delhi-Kolkata corridor
            {
                'route_name': 'Delhi Kolkata Highway',
                'origin': 'Delhi',
                'destination': 'Kolkata',
                'origin_coords': {'lat': 28.7041, 'lng': 77.1025},
                'dest_coords': {'lat': 22.5726, 'lng': 88.3639},
                'frequency': 'alternate_days',
                'duration': 18,
                'vendor_index': 4,
                'stops': [
                    {'city': 'Kanpur', 'lat': 26.4499, 'lng': 80.3319, 'order': 1},
                    {'city': 'Allahabad', 'lat': 25.4358, 'lng': 81.8463, 'order': 2},
                    {'city': 'Varanasi', 'lat': 25.3176, 'lng': 82.9739, 'order': 3}
                ]
            },
            # Hyderabad routes
            {
                'route_name': 'Hyderabad to Chennai Service',
                'origin': 'Hyderabad',
                'destination': 'Chennai',
                'origin_coords': {'lat': 17.3850, 'lng': 78.4867},
                'dest_coords': {'lat': 13.0827, 'lng': 80.2707},
                'frequency': 'daily',
                'duration': 8,
                'vendor_index': 2,
                'stops': [
                    {'city': 'Kurnool', 'lat': 15.8281, 'lng': 78.0373, 'order': 1},
                    {'city': 'Tirupati', 'lat': 13.6288, 'lng': 79.4192, 'order': 2}
                ]
            },
            # Bangalore-Mumbai corridor
            {
                'route_name': 'Bangalore Mumbai Express',
                'origin': 'Bangalore',
                'destination': 'Mumbai',
                'origin_coords': {'lat': 12.9716, 'lng': 77.5946},
                'dest_coords': {'lat': 19.0760, 'lng': 72.8777},
                'frequency': 'alternate_days',
                'duration': 16,
                'vendor_index': 2,
                'stops': [
                    {'city': 'Hubli', 'lat': 15.3647, 'lng': 75.1240, 'order': 1},
                    {'city': 'Belgaum', 'lat': 15.8497, 'lng': 74.4977, 'order': 2},
                    {'city': 'Kolhapur', 'lat': 16.7050, 'lng': 74.2433, 'order': 3},
                    {'city': 'Pune', 'lat': 18.5204, 'lng': 73.8567, 'order': 4}
                ]
            }
        ]

        for route_info in route_data:
            vendor = list(vendors)[route_info['vendor_index']]
            origin_coords = route_info['origin_coords']
            dest_coords = route_info['dest_coords']
            
            route, created = Route.objects.get_or_create(
                route_name=route_info['route_name'],
                vendor=vendor,
                defaults={
                    'origin_city': route_info['origin'],
                    'destination_city': route_info['destination'],
                    'origin_latitude': Decimal(str(origin_coords['lat'])),
                    'origin_longitude': Decimal(str(origin_coords['lng'])),
                    'destination_latitude': Decimal(str(dest_coords['lat'])),
                    'destination_longitude': Decimal(str(dest_coords['lng'])),
                    'route_frequency': route_info['frequency'],
                    'estimated_duration_hours': Decimal(str(route_info['duration'])),
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(f"Created route: {route.route_name}")
                
                # Create route stops
                for stop_info in route_info.get('stops', []):
                    RouteStop.objects.create(
                        route=route,
                        stop_name=stop_info['city'],
                        stop_latitude=Decimal(str(stop_info['lat'])),
                        stop_longitude=Decimal(str(stop_info['lng'])),
                        stop_order=stop_info['order'],
                        can_pickup=True,
                        can_drop=True,
                        estimated_arrival_time=stop_info['order'] * 2  # Rough estimate
                    )
                
                # Create route pricing for different truck types
                self.create_route_pricing(route, truck_types)

    def create_route_pricing(self, route, truck_types):
        """Create pricing for a route for different truck types"""
        # Calculate rough distance (simplified)
        origin_lat = float(route.origin_latitude)
        origin_lng = float(route.origin_longitude)
        dest_lat = float(route.destination_latitude)
        dest_lng = float(route.destination_longitude)
        
        # Haversine formula for distance
        import math
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(dest_lat - origin_lat)
        dlon = math.radians(dest_lng - origin_lng)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(origin_lat)) \
            * math.cos(math.radians(dest_lat)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        # Pricing based on truck type and distance
        pricing_multipliers = {
            'Mini Truck': {'base': 500, 'per_km': 8, 'capacity': 1},
            'Small Truck': {'base': 800, 'per_km': 12, 'capacity': 3},
            'Medium Truck': {'base': 1200, 'per_km': 18, 'capacity': 7},
            'Large Truck': {'base': 2000, 'per_km': 25, 'capacity': 15},
            'Container Truck': {'base': 3000, 'per_km': 35, 'capacity': 25}
        }
        
        for truck_type in truck_types:
            multiplier = pricing_multipliers.get(truck_type.name, pricing_multipliers['Medium Truck'])
            
            RoutePricing.objects.create(
                route=route,
                truck_type=truck_type,
                base_price=Decimal(str(multiplier['base'])),
                price_per_km=Decimal(str(multiplier['per_km'])),
                fuel_charges=Decimal(str(distance * 2.5)),  # Rough fuel cost
                toll_charges=Decimal(str(max(50, distance * 1.5))),  # Rough toll cost
                loading_charges=Decimal('200'),
                unloading_charges=Decimal('200'),
                max_weight_capacity=Decimal(str(multiplier['capacity'])),
                is_active=True
            )

    def create_trucks_and_drivers(self):
        """Create trucks and drivers for each vendor"""
        vendors = User.objects.filter(role='vendor')
        truck_types = TruckType.objects.all()
        
        # Sample truck data for each vendor
        truck_data = [
            # Mumbai Transport Co. trucks
            {
                'registration_number': 'MH01AB1234',
                'capacity': Decimal('2.5'),
                'make': 'Tata',
                'model': 'Ace Gold',
                'year': 2022,
                'color': 'White',
                'base_price_per_km': Decimal('12.50'),
                'location': {'lat': 19.0760, 'lng': 72.8777, 'address': 'Mumbai, Maharashtra'},
                'vendor_index': 0
            },
            {
                'registration_number': 'MH01AB5678',
                'capacity': Decimal('7.5'),
                'make': 'Mahindra',
                'model': 'Bolero Pickup',
                'year': 2021,
                'color': 'Blue',
                'base_price_per_km': Decimal('18.00'),
                'location': {'lat': 19.0760, 'lng': 72.8777, 'address': 'Mumbai, Maharashtra'},
                'vendor_index': 0
            },
            {
                'registration_number': 'MH01AB9999',
                'capacity': Decimal('0.8'),
                'make': 'Maruti',
                'model': 'Super Carry',
                'year': 2023,
                'color': 'White',
                'base_price_per_km': Decimal('8.50'),
                'location': {'lat': 18.5204, 'lng': 73.8567, 'address': 'Pune, Maharashtra'},
                'vendor_index': 0
            },
            
            # Delhi Logistics Ltd. trucks
            {
                'registration_number': 'DL01CA1111',
                'capacity': Decimal('5.0'),
                'make': 'Ashok Leyland',
                'model': 'Dost',
                'year': 2022,
                'color': 'Yellow',
                'base_price_per_km': Decimal('15.00'),
                'location': {'lat': 28.7041, 'lng': 77.1025, 'address': 'Delhi'},
                'vendor_index': 1
            },
            {
                'registration_number': 'DL01CA2222',
                'capacity': Decimal('12.0'),
                'make': 'Eicher',
                'model': 'Pro 3015',
                'year': 2021,
                'color': 'Red',
                'base_price_per_km': Decimal('22.00'),
                'location': {'lat': 28.7041, 'lng': 77.1025, 'address': 'Delhi'},
                'vendor_index': 1
            },
            {
                'registration_number': 'RJ01AB1234',
                'capacity': Decimal('3.5'),
                'make': 'Tata',
                'model': 'Intra V30',
                'year': 2023,
                'color': 'White',
                'base_price_per_km': Decimal('14.00'),
                'location': {'lat': 26.9124, 'lng': 75.7873, 'address': 'Jaipur, Rajasthan'},
                'vendor_index': 1
            },
            
            # Bangalore Freight Services trucks
            {
                'registration_number': 'KA01AB3333',
                'capacity': Decimal('1.5'),
                'make': 'Tata',
                'model': 'Ace',
                'year': 2022,
                'color': 'White',
                'base_price_per_km': Decimal('10.00'),
                'location': {'lat': 12.9716, 'lng': 77.5946, 'address': 'Bangalore, Karnataka'},
                'vendor_index': 2
            },
            {
                'registration_number': 'KA01AB4444',
                'capacity': Decimal('8.5'),
                'make': 'Mahindra',
                'model': 'Furio 7',
                'year': 2021,
                'color': 'Orange',
                'base_price_per_km': Decimal('19.50'),
                'location': {'lat': 12.9716, 'lng': 77.5946, 'address': 'Bangalore, Karnataka'},
                'vendor_index': 2
            },
            {
                'registration_number': 'AP01AB1234',
                'capacity': Decimal('6.0'),
                'make': 'Ashok Leyland',
                'model': 'Partner',
                'year': 2023,
                'color': 'Blue',
                'base_price_per_km': Decimal('16.50'),
                'location': {'lat': 17.3850, 'lng': 78.4867, 'address': 'Hyderabad, Telangana'},
                'vendor_index': 2
            },
            
            # Chennai Express Transport trucks
            {
                'registration_number': 'TN01AB5555',
                'capacity': Decimal('4.0'),
                'make': 'Force',
                'model': 'Traveller',
                'year': 2022,
                'color': 'Silver',
                'base_price_per_km': Decimal('13.50'),
                'location': {'lat': 13.0827, 'lng': 80.2707, 'address': 'Chennai, Tamil Nadu'},
                'vendor_index': 3
            },
            {
                'registration_number': 'TN01AB6666',
                'capacity': Decimal('10.0'),
                'make': 'Bharat Benz',
                'model': '1214R',
                'year': 2021,
                'color': 'White',
                'base_price_per_km': Decimal('21.00'),
                'location': {'lat': 13.0827, 'lng': 80.2707, 'address': 'Chennai, Tamil Nadu'},
                'vendor_index': 3
            },
            
            # Kolkata Cargo Movers trucks
            {
                'registration_number': 'WB01AB7777',
                'capacity': Decimal('2.0'),
                'make': 'Piaggio',
                'model': 'Porter 700',
                'year': 2023,
                'color': 'Green',
                'base_price_per_km': Decimal('11.00'),
                'location': {'lat': 22.5726, 'lng': 88.3639, 'address': 'Kolkata, West Bengal'},
                'vendor_index': 4
            },
            {
                'registration_number': 'WB01AB8888',
                'capacity': Decimal('15.0'),
                'make': 'Volvo',
                'model': 'FL280',
                'year': 2020,
                'color': 'Blue',
                'base_price_per_km': Decimal('28.00'),
                'location': {'lat': 22.5726, 'lng': 88.3639, 'address': 'Kolkata, West Bengal'},
                'vendor_index': 4
            }
        ]

        # Sample driver data
        driver_data = [
            # Mumbai Transport Co. drivers
            {'name': 'Ravi Sharma', 'phone_number': '+919876543210', 'email': 'ravi@mumbaitransport.com', 'license_number': 'MH0120230001', 'experience_years': 8, 'vendor_index': 0},
            {'name': 'Suresh Patil', 'phone_number': '+919876543211', 'email': 'suresh@mumbaitransport.com', 'license_number': 'MH0120230002', 'experience_years': 12, 'vendor_index': 0},
            {'name': 'Vikram More', 'phone_number': '+919876543212', 'email': 'vikram@mumbaitransport.com', 'license_number': 'MH0120230003', 'experience_years': 5, 'vendor_index': 0},
            
            # Delhi Logistics Ltd. drivers
            {'name': 'Ramesh Kumar', 'phone_number': '+919876543213', 'email': 'ramesh@delhilogistics.com', 'license_number': 'DL0120230001', 'experience_years': 10, 'vendor_index': 1},
            {'name': 'Amit Singh', 'phone_number': '+919876543214', 'email': 'amit@delhilogistics.com', 'license_number': 'DL0120230002', 'experience_years': 7, 'vendor_index': 1},
            {'name': 'Rohit Gupta', 'phone_number': '+919876543215', 'email': 'rohit@delhilogistics.com', 'license_number': 'RJ0120230001', 'experience_years': 9, 'vendor_index': 1},
            
            # Bangalore Freight Services drivers
            {'name': 'Kiran Reddy', 'phone_number': '+919876543216', 'email': 'kiran@bangalorefreight.com', 'license_number': 'KA0120230001', 'experience_years': 6, 'vendor_index': 2},
            {'name': 'Srinivas Rao', 'phone_number': '+919876543217', 'email': 'srinivas@bangalorefreight.com', 'license_number': 'KA0120230002', 'experience_years': 11, 'vendor_index': 2},
            {'name': 'Venkat Kumar', 'phone_number': '+919876543218', 'email': 'venkat@bangalorefreight.com', 'license_number': 'AP0120230001', 'experience_years': 4, 'vendor_index': 2},
            
            # Chennai Express Transport drivers
            {'name': 'Murugan S', 'phone_number': '+919876543219', 'email': 'murugan@chennaiexpress.com', 'license_number': 'TN0120230001', 'experience_years': 13, 'vendor_index': 3},
            {'name': 'Rajesh Tamil', 'phone_number': '+919876543220', 'email': 'rajesh@chennaiexpress.com', 'license_number': 'TN0120230002', 'experience_years': 8, 'vendor_index': 3},
            
            # Kolkata Cargo Movers drivers
            {'name': 'Pradip Das', 'phone_number': '+919876543221', 'email': 'pradip@kolkatacargo.com', 'license_number': 'WB0120230001', 'experience_years': 9, 'vendor_index': 4},
            {'name': 'Subhash Ghosh', 'phone_number': '+919876543222', 'email': 'subhash@kolkatacargo.com', 'license_number': 'WB0120230002', 'experience_years': 15, 'vendor_index': 4}
        ]

        # Create trucks
        for truck_info in truck_data:
            vendor = list(vendors)[truck_info['vendor_index']]
            
            # Determine truck type based on capacity
            if truck_info['capacity'] <= 1:
                truck_type = truck_types.get(name='Mini Truck')
            elif truck_info['capacity'] <= 3:
                truck_type = truck_types.get(name='Small Truck')
            elif truck_info['capacity'] <= 7:
                truck_type = truck_types.get(name='Medium Truck')
            else:
                truck_type = truck_types.get(name='Large Truck')

            truck, created = Truck.objects.get_or_create(
                registration_number=truck_info['registration_number'],
                defaults={
                    'vendor': vendor,
                    'truck_type': truck_type,
                    'capacity': truck_info['capacity'],
                    'make': truck_info['make'],
                    'model': truck_info['model'],
                    'year': truck_info['year'],
                    'color': truck_info['color'],
                    'base_price_per_km': truck_info['base_price_per_km'],
                    'current_location_latitude': truck_info['location']['lat'],
                    'current_location_longitude': truck_info['location']['lng'],
                    'current_location_address': truck_info['location']['address'],
                    'availability_status': 'available'
                }
            )
            if created:
                self.stdout.write(f"Created truck: {truck.registration_number}")

        # Create drivers
        for driver_info in driver_data:
            vendor = list(vendors)[driver_info['vendor_index']]
            
            driver, created = Driver.objects.get_or_create(
                license_number=driver_info['license_number'],
                defaults={
                    'vendor': vendor,
                    'name': driver_info['name'],
                    'phone_number': driver_info['phone_number'],
                    'email': driver_info['email'],
                    'license_expiry_date': date.today() + timedelta(days=365*3),  # 3 years from now
                    'experience_years': driver_info['experience_years'],
                    'is_available': True
                }
            )
            if created:
                self.stdout.write(f"Created driver: {driver.name}")

        self.stdout.write(f"Created {len(truck_data)} trucks and {len(driver_data)} drivers")

    def print_test_endpoints(self):
        """Print sample API endpoints for testing"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SAMPLE API ENDPOINTS FOR TESTING'))
        self.stdout.write('='*60)
        
        self.stdout.write('\n1. Test Truck Search (Mumbai to Delhi):')
        self.stdout.write('   GET /api/trucks/search/?origin_pincode=400001&destination_pincode=110001&weight=2.5&pickup_date=2025-08-15')
        
        self.stdout.write('\n2. Test Truck Search (Bangalore to Chennai):')
        self.stdout.write('   GET /api/trucks/search/?origin_pincode=560001&destination_pincode=600001&weight=1.5&pickup_date=2025-08-15')
        
        self.stdout.write('\n3. Test Truck Search with coordinates (Mumbai to Pune):')
        self.stdout.write('   GET /api/trucks/search/?pickup_latitude=19.0760&pickup_longitude=72.8777&delivery_latitude=18.5204&delivery_longitude=73.8567&weight=3.0&pickup_date=2025-08-15')
        
        self.stdout.write('\n4. Test Truck Search with filters:')
        self.stdout.write('   GET /api/trucks/search/?origin_pincode=400001&destination_pincode=110001&weight=2.5&pickup_date=2025-08-15&truck_type=Medium&capacity_min=2&capacity_max=10')
        
        self.stdout.write('\n5. Login as vendor:')
        self.stdout.write('   POST /api/auth/login/')
        self.stdout.write('   Body: {"email": "vendor1@truckrent.com", "password": "vendor123"}')
        
        self.stdout.write('\n6. Login as customer:')
        self.stdout.write('   POST /api/auth/login/')
        self.stdout.write('   Body: {"email": "customer1@example.com", "password": "customer123"}')
        
        self.stdout.write('\n7. Get all truck types:')
        self.stdout.write('   GET /api/trucks/types/')
        
        self.stdout.write('\n8. Get all trucks:')
        self.stdout.write('   GET /api/trucks/')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Note: Replace dates with current/future dates for testing')
        self.stdout.write('Pin codes: Mumbai(400001), Delhi(110001), Bangalore(560001), Chennai(600001), Pune(411001)')
        self.stdout.write('='*60)
