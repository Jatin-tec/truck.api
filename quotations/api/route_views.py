from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Min, Max, Avg
from quotations.models import (
    Route, RouteStop, RoutePricing, CustomerEnquiry, 
    PriceRange, VendorEnquiryRequest
)
from quotations.api.route_serializers import (
    RouteSerializer, CreateRouteSerializer, CustomerEnquirySerializer,
    CreateEnquirySerializer, PriceRangeSerializer, EnquiryWithPriceRangesSerializer,
    VendorEnquiryRequestSerializer, CreateVendorEnquiryRequestSerializer,
    VendorResponseSerializer, ManagerDashboardEnquirySerializer
)
from trucks.models import TruckType
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import math

User = get_user_model()

# Permission Classes
class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'

class IsVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor'

class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'

class IsManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'admin']

# ============ VENDOR ROUTE MANAGEMENT ============

class VendorRoutesView(generics.ListCreateAPIView):
    """Vendor manages their routes"""
    permission_classes = [IsVendor]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateRouteSerializer
        return RouteSerializer
    
    def get_queryset(self):
        return Route.objects.filter(vendor=self.request.user, is_active=True)

class VendorRouteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Vendor views/updates specific route"""
    serializer_class = RouteSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Route.objects.filter(vendor=self.request.user)

# ============ CUSTOMER ENQUIRY SYSTEM ============

class CustomerEnquiryCreateView(generics.CreateAPIView):
    """Customer creates enquiry with pickup/drop details"""
    serializer_class = CreateEnquirySerializer
    permission_classes = [IsCustomer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = serializer.save()
        
        # Generate price ranges automatically
        self.generate_price_ranges(enquiry)
        
        # Return enquiry with price ranges
        response_serializer = EnquiryWithPriceRangesSerializer(enquiry)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def generate_price_ranges(self, enquiry):
        """Generate price ranges based on matching routes"""
        # Find matching routes
        matching_routes = self.find_matching_routes(enquiry)
        
        if matching_routes:
            # Create price ranges from matching routes
            self.create_route_based_price_ranges(enquiry, matching_routes)
        else:
            # Create miscellaneous route price range
            enquiry.is_miscellaneous_route = True
            enquiry.save()
            self.create_miscellaneous_price_range(enquiry)

    def find_matching_routes(self, enquiry):
        """Find routes that match customer's pickup/delivery"""
        matching_routes = []
        
        # Get all routes with pricing for the requested truck type
        routes = Route.objects.filter(
            is_active=True,
            pricing__truck_type=enquiry.truck_type,
            pricing__available_vehicles__gte=enquiry.number_of_vehicles
        ).distinct()
        
        for route in routes:
            # Check if pickup and delivery cities match route segments
            segments = route.pricing.filter(truck_type=enquiry.truck_type)
            
            for segment in segments:
                pickup_match = self.city_matches(enquiry.pickup_city, [segment.from_city, route.origin_city])
                delivery_match = self.city_matches(enquiry.delivery_city, [segment.to_city, route.destination_city])
                
                # Also check intermediate stops
                stops = route.stops.all()
                stop_cities = [stop.stop_city for stop in stops]
                
                pickup_match = pickup_match or self.city_matches(enquiry.pickup_city, stop_cities)
                delivery_match = delivery_match or self.city_matches(enquiry.delivery_city, stop_cities)
                
                if pickup_match and delivery_match:
                    matching_routes.append({
                        'route': route,
                        'segment': segment,
                        'route_type': 'direct' if len(stop_cities) == 0 else 'via_stops'
                    })
                    break
        
        return matching_routes

    def city_matches(self, city1, city_list):
        """Check if city matches any city in the list (case insensitive)"""
        return any(city1.lower() in city.lower() or city.lower() in city1.lower() 
                  for city in city_list)

    def create_route_based_price_ranges(self, enquiry, matching_routes):
        """Create price ranges from matching routes"""
        # Group routes by price range
        price_groups = {}
        
        for match in matching_routes:
            segment = match['segment']
            total_price = segment.get_total_price() * enquiry.number_of_vehicles
            
            # Group by price range (rounded to nearest 500)
            price_key = round(total_price / 500) * 500
            
            if price_key not in price_groups:
                price_groups[price_key] = {
                    'routes': [],
                    'prices': [],
                    'vehicles': 0,
                    'vendors': set(),
                    'route_type': match['route_type']
                }
            
            price_groups[price_key]['routes'].append(match['route'])
            price_groups[price_key]['prices'].append(total_price)
            price_groups[price_key]['vehicles'] += segment.available_vehicles
            price_groups[price_key]['vendors'].add(segment.route.vendor.id)

        # Create price ranges
        for price_key, group in price_groups.items():
            min_price = min(group['prices'])
            max_price = max(group['prices'])
            avg_price = sum(group['prices']) / len(group['prices'])
            
            # Determine chance based on number of vendors and vehicles
            vendors_count = len(group['vendors'])
            vehicles_available = group['vehicles']
            
            if vendors_count >= 3 and vehicles_available >= enquiry.number_of_vehicles * 2:
                chance = 'high'
            elif vendors_count >= 2 and vehicles_available >= enquiry.number_of_vehicles:
                chance = 'medium'
            else:
                chance = 'low'
            
            price_range = PriceRange.objects.create(
                enquiry=enquiry,
                min_price=min_price,
                max_price=max_price,
                recommended_price=avg_price,
                vehicles_available=vehicles_available,
                vendors_count=vendors_count,
                chance_of_getting_deal=chance,
                route_type=group['route_type'],
                estimated_duration_hours=group['routes'][0].estimated_duration_hours
            )
            
            # Add supporting routes (hidden from customer)
            price_range.supporting_routes.set(group['routes'])

    def create_miscellaneous_price_range(self, enquiry):
        """Create price range for miscellaneous routes"""
        # Calculate estimated price based on distance and average market rates
        base_rate_per_km = 25  # Base rate per km for miscellaneous routes
        estimated_price = float(enquiry.estimated_distance_km) * base_rate_per_km * enquiry.number_of_vehicles
        
        # Add markup for miscellaneous routes (20-50% higher)
        min_price = estimated_price * 1.2
        max_price = estimated_price * 1.5
        recommended_price = estimated_price * 1.35
        
        PriceRange.objects.create(
            enquiry=enquiry,
            min_price=min_price,
            max_price=max_price,
            recommended_price=recommended_price,
            vehicles_available=1,  # Conservative estimate
            vendors_count=1,  # Will find vendors when selected
            chance_of_getting_deal='medium',
            route_type='miscellaneous',
            estimated_duration_hours=float(enquiry.estimated_distance_km) / 60  # Assuming 60 km/h
        )

class CustomerEnquiriesView(generics.ListAPIView):
    """Customer views their enquiries"""
    serializer_class = EnquiryWithPriceRangesSerializer
    permission_classes = [IsCustomer]
    
    def get_queryset(self):
        return CustomerEnquiry.objects.filter(customer=self.request.user)

class SelectPriceRangeView(APIView):
    """Customer selects a price range to proceed"""
    permission_classes = [IsCustomer]
    
    def post(self, request, enquiry_id, price_range_id):
        try:
            enquiry = CustomerEnquiry.objects.get(
                id=enquiry_id,
                customer=request.user
            )
            price_range = PriceRange.objects.get(
                id=price_range_id,
                enquiry=enquiry
            )
            
            # Update enquiry status
            enquiry.status = 'quote_selected'
            enquiry.save()
            
            # Assign to available manager (round-robin or least loaded)
            manager = self.assign_manager()
            if manager:
                enquiry.assigned_manager = manager
                enquiry.save()
            
            return Response({
                'message': 'Price range selected successfully. Our team will contact vendors and get back to you.',
                'enquiry_id': enquiry.id,
                'selected_price_range': PriceRangeSerializer(price_range).data,
                'assigned_manager': manager.name if manager else None
            })
            
        except (CustomerEnquiry.DoesNotExist, PriceRange.DoesNotExist):
            return Response({
                'error': 'Enquiry or price range not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def assign_manager(self):
        """Assign manager with least workload"""
        managers = User.objects.filter(role='manager', is_active=True)
        if not managers.exists():
            return None
        
        # Find manager with least active enquiries
        manager_workloads = []
        for manager in managers:
            active_count = manager.managed_enquiries.filter(
                status__in=['quote_selected', 'sent_to_vendors', 'vendor_responses']
            ).count()
            manager_workloads.append((manager, active_count))
        
        # Sort by workload and return least loaded manager
        manager_workloads.sort(key=lambda x: x[1])
        return manager_workloads[0][0]

# ============ MANAGER DASHBOARD ============

class ManagerDashboardView(APIView):
    """Manager dashboard with all pending enquiries"""
    permission_classes = [IsManager]
    
    def get(self, request):
        # Get all enquiries assigned to this manager or unassigned
        enquiries = CustomerEnquiry.objects.filter(
            Q(assigned_manager=request.user) | Q(assigned_manager__isnull=True)
        ).exclude(status__in=['confirmed', 'cancelled'])
        
        # Categorize enquiries
        new_enquiries = enquiries.filter(status='quote_selected')
        sent_to_vendors = enquiries.filter(status='sent_to_vendors')
        vendor_responses = enquiries.filter(status='vendor_responses')
        
        return Response({
            'new_enquiries': ManagerDashboardEnquirySerializer(new_enquiries, many=True).data,
            'sent_to_vendors': ManagerDashboardEnquirySerializer(sent_to_vendors, many=True).data,
            'vendor_responses': ManagerDashboardEnquirySerializer(vendor_responses, many=True).data,
            'total_active': enquiries.count()
        })

class SendToVendorsView(APIView):
    """Manager sends enquiry to selected vendors"""
    permission_classes = [IsManager]
    
    def post(self, request, enquiry_id):
        try:
            enquiry = CustomerEnquiry.objects.get(id=enquiry_id)
            price_range_id = request.data.get('price_range_id')
            vendor_ids = request.data.get('vendor_ids', [])
            suggested_price = request.data.get('suggested_price')
            manager_notes = request.data.get('manager_notes', '')
            urgency_level = request.data.get('urgency_level', 'medium')
            
            price_range = PriceRange.objects.get(id=price_range_id, enquiry=enquiry)
            
            # Create vendor enquiry requests
            valid_until = timezone.now() + timedelta(hours=24)  # 24 hour validity
            
            for vendor_id in vendor_ids:
                vendor = User.objects.get(id=vendor_id, role='vendor')
                
                # Find relevant route for this vendor
                route = None
                if price_range.supporting_routes.exists():
                    route = price_range.supporting_routes.filter(vendor=vendor).first()
                
                VendorEnquiryRequest.objects.create(
                    enquiry=enquiry,
                    vendor=vendor,
                    price_range=price_range,
                    route=route,
                    sent_by_manager=request.user,
                    suggested_price=suggested_price,
                    manager_notes=manager_notes,
                    urgency_level=urgency_level,
                    valid_until=valid_until
                )
            
            # Update enquiry status
            enquiry.status = 'sent_to_vendors'
            enquiry.assigned_manager = request.user
            enquiry.save()
            
            return Response({
                'message': f'Enquiry sent to {len(vendor_ids)} vendors successfully',
                'vendor_requests_created': len(vendor_ids)
            })
            
        except CustomerEnquiry.DoesNotExist:
            return Response({'error': 'Enquiry not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ============ VENDOR RESPONSE SYSTEM ============

class VendorEnquiryRequestsView(generics.ListAPIView):
    """Vendor views enquiry requests sent by managers"""
    serializer_class = VendorEnquiryRequestSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return VendorEnquiryRequest.objects.filter(
            vendor=self.request.user,
            valid_until__gt=timezone.now()
        ).exclude(status__in=['expired', 'rejected'])

class VendorRespondToEnquiryView(APIView):
    """Vendor responds to enquiry request"""
    permission_classes = [IsVendor]
    
    def post(self, request, request_id):
        try:
            vendor_request = VendorEnquiryRequest.objects.get(
                id=request_id,
                vendor=request.user
            )
            
            action = request.data.get('action')  # 'accept' or 'renegotiate'
            
            if action == 'accept':
                vendor_request.status = 'accepted'
                vendor_request.vendor_response_price = vendor_request.suggested_price
                vendor_request.vendor_response_notes = request.data.get('notes', 'Accepted as suggested')
                vendor_request.response_date = timezone.now()
                vendor_request.save()
                
                # Update enquiry status
                enquiry = vendor_request.enquiry
                enquiry.status = 'vendor_responses'
                enquiry.save()
                
                return Response({
                    'message': 'Enquiry accepted successfully',
                    'response_price': vendor_request.vendor_response_price
                })
                
            elif action == 'renegotiate':
                new_price = request.data.get('new_price')
                notes = request.data.get('notes', '')
                
                if not new_price:
                    return Response({
                        'error': 'New price is required for renegotiation'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                vendor_request.status = 'quoted'
                vendor_request.vendor_response_price = new_price
                vendor_request.vendor_response_notes = notes
                vendor_request.response_date = timezone.now()
                vendor_request.save()
                
                # Update enquiry status
                enquiry = vendor_request.enquiry
                enquiry.status = 'vendor_responses'
                enquiry.save()
                
                return Response({
                    'message': 'Counter-offer submitted successfully',
                    'response_price': vendor_request.vendor_response_price
                })
            
            else:
                return Response({
                    'error': 'Invalid action. Use "accept" or "renegotiate"'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except VendorEnquiryRequest.DoesNotExist:
            return Response({
                'error': 'Enquiry request not found'
            }, status=status.HTTP_404_NOT_FOUND)

class VendorRejectEnquiryView(APIView):
    """Vendor rejects enquiry request"""
    permission_classes = [IsVendor]
    
    def post(self, request, request_id):
        try:
            vendor_request = VendorEnquiryRequest.objects.get(
                id=request_id,
                vendor=request.user
            )
            
            vendor_request.status = 'rejected'
            vendor_request.vendor_response_notes = request.data.get('reason', 'Not available')
            vendor_request.response_date = timezone.now()
            vendor_request.save()
            
            return Response({
                'message': 'Enquiry rejected successfully'
            })
            
        except VendorEnquiryRequest.DoesNotExist:
            return Response({
                'error': 'Enquiry request not found'
            }, status=status.HTTP_404_NOT_FOUND)

# ============ MANAGER VENDOR SELECTION ============

class ManagerViewVendorResponsesView(APIView):
    """Manager views all vendor responses for an enquiry"""
    permission_classes = [IsManager]
    
    def get(self, request, enquiry_id):
        try:
            enquiry = CustomerEnquiry.objects.get(id=enquiry_id)
            vendor_responses = VendorEnquiryRequest.objects.filter(
                enquiry=enquiry
            ).exclude(status='sent')
            
            return Response({
                'enquiry': CustomerEnquirySerializer(enquiry).data,
                'vendor_responses': VendorEnquiryRequestSerializer(vendor_responses, many=True).data
            })
            
        except CustomerEnquiry.DoesNotExist:
            return Response({
                'error': 'Enquiry not found'
            }, status=status.HTTP_404_NOT_FOUND)

class ManagerConfirmVendorView(APIView):
    """Manager confirms a vendor and notifies customer"""
    permission_classes = [IsManager]
    
    def post(self, request, enquiry_id, vendor_request_id):
        try:
            enquiry = CustomerEnquiry.objects.get(id=enquiry_id)
            selected_vendor_request = VendorEnquiryRequest.objects.get(
                id=vendor_request_id,
                enquiry=enquiry
            )
            
            # Update enquiry status
            enquiry.status = 'confirmed'
            enquiry.save()
            
            # Mark selected vendor request as confirmed
            selected_vendor_request.status = 'accepted'
            selected_vendor_request.save()
            
            # Reject other vendor requests
            VendorEnquiryRequest.objects.filter(
                enquiry=enquiry
            ).exclude(id=vendor_request_id).update(status='rejected')
            
            return Response({
                'message': 'Vendor confirmed successfully. Customer will be notified.',
                'confirmed_vendor': selected_vendor_request.vendor.name,
                'final_price': selected_vendor_request.vendor_response_price
            })
            
        except (CustomerEnquiry.DoesNotExist, VendorEnquiryRequest.DoesNotExist):
            return Response({
                'error': 'Enquiry or vendor request not found'
            }, status=status.HTTP_404_NOT_FOUND)
