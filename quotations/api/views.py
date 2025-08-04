from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from quotations.models import (
    QuotationRequest, Quotation, QuotationNegotiation, 
    Cart, CartItem, QuotationItem, QuotationRequestItem
)
from quotations.api.serializers import (
    QuotationRequestSerializer, QuotationSerializer, QuotationNegotiationSerializer,
    QuotationCreateSerializer, QuotationUpdateStatusSerializer, NegotiationCreateSerializer,
    CartSerializer, CartItemSerializer, AddToCartSerializer, UpdateCartItemSerializer,
    CreateQuotationRequestSerializer
)
from trucks.models import Truck
from project.utils import success_response, error_response, validation_error_response, StandardizedResponseMixin

class IsCustomer(permissions.BasePermission):
    """Permission for customer-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'

class IsVendor(permissions.BasePermission):
    """Permission for vendor-only endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'vendor'

class IsCustomerOrVendor(permissions.BasePermission):
    """Permission for customer or vendor endpoints"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['customer', 'vendor']

class CartView(APIView):
    """Manage customer's cart"""
    permission_classes = [IsCustomer]
    
    def get(self, request):
        """Get customer's active cart"""
        try:
            cart = Cart.objects.get(customer=request.user, is_active=True)
            serializer = CartSerializer(cart)
            return success_response(data=serializer.data, message="Cart retrieved successfully")
        except Cart.DoesNotExist:
            return success_response(
                data={'cart': None},
                message='No active cart found'
            )

class AddToCartView(APIView):
    """Add truck to cart"""
    permission_classes = [IsCustomer]
    
    def post(self, request):
        try:
            serializer = AddToCartSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)
            
            truck = serializer.validated_data['truck_id']
            quantity = serializer.validated_data['quantity']
            item_weight = serializer.validated_data['item_weight']
            item_special_instructions = serializer.validated_data.get('item_special_instructions', '')
            
            # Get or create cart for this vendor
            cart, created = Cart.objects.get_or_create(
                customer=request.user,
                vendor=truck.vendor,
                is_active=True
            )
            
            # Check if customer already has a cart with a different vendor
            existing_carts = Cart.objects.filter(
                customer=request.user,
                is_active=True
            ).exclude(vendor=truck.vendor)
            
            if existing_carts.exists():
                return error_response(
                    f'You already have items from {existing_carts.first().vendor.name} in your cart. Please checkout or clear your current cart first.',
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Add or update cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                truck=truck,
                defaults={
                    'quantity': quantity,
                    'item_weight': item_weight,
                    'item_special_instructions': item_special_instructions
                }
            )
            
            if not created:
                # Update existing item
                cart_item.quantity += quantity
                cart_item.item_weight += item_weight
                cart_item.save()
            
            # Return updated cart
            cart_serializer = CartSerializer(cart)
            return success_response(
                data=cart_serializer.data,
                message="Item added to cart successfully"
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

class UpdateCartItemView(APIView):
    """Update cart item"""
    permission_classes = [IsCustomer]
    
    def put(self, request, item_id):
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__customer=request.user,
                cart__is_active=True
            )
        except CartItem.DoesNotExist:
            return error_response('Cart item not found', status.HTTP_404_NOT_FOUND)
        
        try:
            serializer = UpdateCartItemSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)
            
            cart_item.quantity = serializer.validated_data['quantity']
            cart_item.item_weight = serializer.validated_data['item_weight']
            cart_item.item_special_instructions = serializer.validated_data.get('item_special_instructions', '')
            cart_item.save()
            
            # Return updated cart
            cart_serializer = CartSerializer(cart_item.cart)
            return success_response(
                data=cart_serializer.data,
                message='Cart item updated successfully'
            )
        except Exception as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)

class RemoveFromCartView(APIView):
    """Remove item from cart"""
    permission_classes = [IsCustomer]
    
    def delete(self, request, item_id):
        try:
            cart_item = CartItem.objects.get(
                id=item_id,
                cart__customer=request.user,
                cart__is_active=True
            )
            cart = cart_item.cart
            cart_item.delete()
            
            # If cart is empty, deactivate it
            if cart.items.count() == 0:
                cart.is_active = False
                cart.save()
                return Response({
                    'message': 'Item removed from cart. Cart is now empty.',
                    'cart': None
                })
            
            # Return updated cart
            cart_serializer = CartSerializer(cart)
            return Response({
                'message': 'Item removed from cart successfully',
                'cart': cart_serializer.data
            })
            
        except CartItem.DoesNotExist:
            return Response({
                'error': 'Cart item not found'
            }, status=status.HTTP_404_NOT_FOUND)

class ClearCartView(APIView):
    """Clear all items from cart"""
    permission_classes = [IsCustomer]
    
    def delete(self, request):
        try:
            cart = Cart.objects.get(customer=request.user, is_active=True)
            cart.clear()
            cart.is_active = False
            cart.save()
            
            return Response({
                'message': 'Cart cleared successfully'
            })
        except Cart.DoesNotExist:
            return Response({
                'message': 'No active cart found'
            }, status=status.HTTP_404_NOT_FOUND)

# Quotation Request Views (Customer)
class QuotationRequestCreateView(generics.CreateAPIView):
    """Customer creates a quotation request from cart"""
    serializer_class = CreateQuotationRequestSerializer
    permission_classes = [IsCustomer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quotation_request = serializer.save()
        
        # Return the created quotation request
        response_serializer = QuotationRequestSerializer(quotation_request)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class CustomerQuotationRequestsView(generics.ListAPIView):
    """List quotation requests for authenticated customer"""
    serializer_class = QuotationRequestSerializer
    permission_classes = [IsCustomer]
    
    def get_queryset(self):
        return QuotationRequest.objects.filter(
            customer=self.request.user,
            is_active=True
        ).order_by('-created_at')

class QuotationRequestDetailView(generics.RetrieveAPIView):
    """Get details of a specific quotation request"""
    serializer_class = QuotationRequestSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return QuotationRequest.objects.filter(customer=user, is_active=True)
        else:  # vendor
            return QuotationRequest.objects.filter(vendor=user, is_active=True)

# Quotation Views
class VendorQuotationRequestsView(generics.ListAPIView):
    """List quotation requests for vendor"""
    serializer_class = QuotationRequestSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return QuotationRequest.objects.filter(
            vendor=self.request.user,
            is_active=True
        ).order_by('-created_at')

class QuotationCreateView(APIView):
    """Vendor creates a quotation for a multi-truck request"""
    permission_classes = [IsVendor]

    def post(self, request):
        quotation_request_id = request.data.get('quotation_request_id')
        if not quotation_request_id:
            return Response({
                'error': 'quotation_request_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quotation_request = QuotationRequest.objects.get(
                id=quotation_request_id,
                vendor=request.user,
                is_active=True
            )
        except QuotationRequest.DoesNotExist:
            return Response({
                'error': 'Quotation request not found or you are not authorized'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if quotation already exists
        if Quotation.objects.filter(
            quotation_request=quotation_request,
            vendor=request.user
        ).exists():
            return Response({
                'error': 'You have already created a quotation for this request'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate quotation data
        required_fields = [
            'total_base_price', 'total_fuel_charges', 'total_toll_charges',
            'total_loading_charges', 'total_unloading_charges', 'total_additional_charges'
        ]
        
        for field in required_fields:
            if field not in request.data:
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate quotation items
        quotation_items_data = request.data.get('items', [])
        if not quotation_items_data:
            return Response({
                'error': 'Quotation items are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate that all requested trucks have quotation items
        request_items = quotation_request.items.all()
        request_truck_ids = set(item.truck.id for item in request_items)
        provided_truck_ids = set(item.get('truck_id') for item in quotation_items_data)
        
        if request_truck_ids != provided_truck_ids:
            return Response({
                'error': 'You must provide pricing for all requested trucks'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create quotation
        quotation = Quotation.objects.create(
            quotation_request=quotation_request,
            vendor=request.user,
            total_base_price=request.data['total_base_price'],
            total_fuel_charges=request.data['total_fuel_charges'],
            total_toll_charges=request.data['total_toll_charges'],
            total_loading_charges=request.data['total_loading_charges'],
            total_unloading_charges=request.data['total_unloading_charges'],
            total_additional_charges=request.data['total_additional_charges'],
            terms_and_conditions=request.data.get('terms_and_conditions', ''),
            validity_hours=request.data.get('validity_hours', 24),
            customer_suggested_price=quotation_request.suggested_total_price,
            vendor_response_to_suggestion=request.data.get('vendor_response_to_suggestion', ''),
            status='sent'
        )
        
        # Create quotation items
        for item_data in quotation_items_data:
            try:
                truck = Truck.objects.get(id=item_data['truck_id'], vendor=request.user)
                request_item = quotation_request.items.get(truck=truck)
                
                QuotationItem.objects.create(
                    quotation=quotation,
                    truck=truck,
                    quantity=request_item.quantity,
                    unit_base_price=item_data.get('unit_base_price', 0),
                    unit_fuel_charges=item_data.get('unit_fuel_charges', 0),
                    unit_toll_charges=item_data.get('unit_toll_charges', 0),
                    unit_loading_charges=item_data.get('unit_loading_charges', 0),
                    unit_unloading_charges=item_data.get('unit_unloading_charges', 0),
                    unit_additional_charges=item_data.get('unit_additional_charges', 0),
                    item_notes=item_data.get('item_notes', '')
                )
            except (Truck.DoesNotExist, QuotationRequestItem.DoesNotExist):
                quotation.delete()  # Cleanup
                return Response({
                    'error': f'Invalid truck_id: {item_data["truck_id"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Return created quotation
        serializer = QuotationSerializer(quotation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class QuotationListView(generics.ListAPIView):
    """List quotations for a specific quotation request"""
    serializer_class = QuotationSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        request_id = self.kwargs['request_id']
        user = self.request.user
        
        quotations = Quotation.objects.filter(
            quotation_request_id=request_id,
            is_active=True
        )
        
        # Filter based on user role
        if user.role == 'customer':
            quotations = quotations.filter(quotation_request__customer=user)
        elif user.role == 'vendor':
            quotations = quotations.filter(vendor=user)
            
        return quotations.order_by('-created_at')

class QuotationDetailView(generics.RetrieveAPIView):
    """Get details of a specific quotation"""
    serializer_class = QuotationSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Quotation.objects.filter(
                quotation_request__customer=user,
                is_active=True
            )
        else:  # vendor
            return Quotation.objects.filter(vendor=user, is_active=True)

class VendorQuotationsView(generics.ListAPIView):
    """List all quotations created by vendor"""
    serializer_class = QuotationSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Quotation.objects.filter(
            vendor=self.request.user,
            is_active=True
        ).order_by('-created_at')

class CustomerQuotationsView(generics.ListAPIView):
    """List all quotations received by customer"""
    serializer_class = QuotationSerializer
    permission_classes = [IsCustomer]
    
    def get_queryset(self):
        return Quotation.objects.filter(
            quotation_request__customer=self.request.user,
            is_active=True
        ).order_by('-created_at')

# Quotation Status Management
class QuotationAcceptView(APIView):
    """Customer accepts a quotation"""
    permission_classes = [IsCustomer]
    
    def post(self, request, quotation_id):
        try:
            quotation = Quotation.objects.get(
                id=quotation_id,
                quotation_request__customer=request.user,
                status__in=['sent', 'negotiating'],
                is_active=True
            )
            
            quotation.status = 'accepted'
            quotation.save()
            
            # Mark other quotations for the same request as rejected
            Quotation.objects.filter(
                quotation_request=quotation.quotation_request,
                is_active=True
            ).exclude(id=quotation.id).update(status='rejected')
            
            return Response({
                'message': 'Quotation accepted successfully',
                'quotation_id': quotation.id
            })
            
        except Quotation.DoesNotExist:
            return Response(
                {'error': 'Quotation not found or cannot be accepted'},
                status=status.HTTP_404_NOT_FOUND
            )

class QuotationRejectView(APIView):
    """Customer rejects a quotation"""
    permission_classes = [IsCustomer]
    
    def post(self, request, quotation_id):
        try:
            quotation = Quotation.objects.get(
                id=quotation_id,
                quotation_request__customer=request.user,
                status__in=['sent', 'negotiating'],
                is_active=True
            )
            
            quotation.status = 'rejected'
            quotation.save()
            
            return Response({'message': 'Quotation rejected successfully'})
            
        except Quotation.DoesNotExist:
            return Response(
                {'error': 'Quotation not found or cannot be rejected'},
                status=status.HTTP_404_NOT_FOUND
            )

# Negotiation Views
class NegotiationCreateView(generics.CreateAPIView):
    """Create a negotiation for a quotation"""
    serializer_class = NegotiationCreateSerializer
    permission_classes = [IsCustomerOrVendor]

class NegotiationListView(generics.ListAPIView):
    """List negotiations for a specific quotation"""
    serializer_class = QuotationNegotiationSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        quotation_id = self.kwargs['quotation_id']
        user = self.request.user
        
        # Ensure user has access to this quotation
        try:
            if user.role == 'customer':
                quotation = Quotation.objects.get(
                    id=quotation_id,
                    quotation_request__customer=user
                )
            else:  # vendor
                quotation = Quotation.objects.get(
                    id=quotation_id,
                    vendor=user
                )
        except Quotation.DoesNotExist:
            return QuotationNegotiation.objects.none()
        
        return QuotationNegotiation.objects.filter(
            quotation_id=quotation_id
        ).order_by('created_at')

class AcceptNegotiationView(APIView):
    """Accept a negotiation and update quotation"""
    permission_classes = [IsCustomerOrVendor]
    
    def post(self, request, negotiation_id):
        try:
            negotiation = QuotationNegotiation.objects.get(id=negotiation_id)
            quotation = negotiation.quotation
            user = request.user
            
            # Check if user is authorized to accept this negotiation
            if user.role == 'customer' and user != quotation.quotation_request.customer:
                raise permissions.PermissionDenied()
            elif user.role == 'vendor' and user != quotation.vendor:
                raise permissions.PermissionDenied()
            
            # Check if the negotiation was initiated by the other party
            if ((user.role == 'customer' and negotiation.initiated_by == 'customer') or
                (user.role == 'vendor' and negotiation.initiated_by == 'vendor')):
                return Response(
                    {'error': 'You cannot accept your own negotiation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update quotation with negotiated values
            quotation.total_base_price = negotiation.proposed_base_price or quotation.total_base_price
            quotation.total_fuel_charges = negotiation.proposed_fuel_charges or quotation.total_fuel_charges
            quotation.total_toll_charges = negotiation.proposed_toll_charges or quotation.total_toll_charges
            quotation.total_loading_charges = negotiation.proposed_loading_charges or quotation.total_loading_charges
            quotation.total_unloading_charges = negotiation.proposed_unloading_charges or quotation.total_unloading_charges
            quotation.total_additional_charges = negotiation.proposed_additional_charges or quotation.total_additional_charges
            quotation.status = 'sent'  # Back to sent status after accepting negotiation
            quotation.save()  # This will recalculate total_amount
            
            return Response({
                'message': 'Negotiation accepted and quotation updated',
                'new_total_amount': quotation.total_amount
            })
            
        except QuotationNegotiation.DoesNotExist:
            return Response(
                {'error': 'Negotiation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
