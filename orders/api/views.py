from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.utils import timezone
from orders.models import Order, OrderStatusHistory, OrderDocument
from orders.api.serializers import (
    OrderSerializer, OrderCreateSerializer, OrderStatusUpdateSerializer,
    OrderStatusHistorySerializer, OrderDocumentSerializer,
    OrderDocumentUploadSerializer, DeliveryVerificationSerializer, 
    AssignDriverSerializer, OrderListSerializer
)
from project.utils import success_response, error_response, validation_error_response, StandardizedResponseMixin
from project.permissions import IsCustomer, IsVendor, IsCustomerOrVendor

# Order Creation
class OrderCreateView(StandardizedResponseMixin, generics.CreateAPIView):
    """Customer creates an order from accepted quotation"""
    serializer_class = OrderCreateSerializer
    permission_classes = [IsCustomer]

# Order Listing and Details
class CustomerOrdersView(StandardizedResponseMixin, generics.ListAPIView):
    """List orders for authenticated customer"""
    serializer_class = OrderListSerializer
    permission_classes = [IsCustomer]
    
    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user,
            is_active=True
        ).order_by('-created_at')

class VendorOrdersView(StandardizedResponseMixin, generics.ListAPIView):
    """List orders for authenticated vendor"""
    serializer_class = OrderListSerializer
    permission_classes = [IsVendor]
    
    def get_queryset(self):
        return Order.objects.filter(
            vendor=self.request.user,
            is_active=True
        ).order_by('-created_at')

class OrderDetailView(generics.RetrieveAPIView):
    """Get details of a specific order"""
    serializer_class = OrderSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'customer':
            return Order.objects.filter(customer=user, is_active=True)
        else:  # vendor
            return Order.objects.filter(vendor=user, is_active=True)

class OrderStatusUpdateView(APIView):
    """Update order status using centralized OrderStatusTrackingService"""
    permission_classes = [IsVendor]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(
                id=order_id,
                vendor=request.user,
                is_active=True
            )
            
            serializer = OrderStatusUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            
            # Use centralized status tracking service
            from orders.services import OrderStatusTrackingService
            
            status_result = OrderStatusTrackingService.update_order_status(
                order=order,
                new_status=data['status'],
                updated_by=request.user,
                notes=data.get('notes', ''),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                driver_id=data.get('driver_id'),
                actual_weight=data.get('actual_weight')
            )
            
            return success_response(
                data={
                    'order_id': order.id,
                    'previous_status': status_result['previous_status'],
                    'new_status': status_result['new_status'],
                    'status_history_id': status_result['status_history'].id,
                    'context': status_result['context']
                },
                message=f'Order status updated to {data["status"]}'
            )
            
        except Order.DoesNotExist:
            return error_response(
                'Order not found or not owned by you',
                status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return error_response(
                str(e),
                status.HTTP_400_BAD_REQUEST
            )

    def _is_valid_status_transition(self, current, new):
        """DEPRECATED: Use OrderStatusTrackingService.VALID_TRANSITIONS instead"""
        # Keep for backward compatibility if needed elsewhere
        valid_transitions = {
            'created': ['confirmed', 'cancelled'],
            'confirmed': ['driver_assigned', 'cancelled'],
            'driver_assigned': ['pickup', 'cancelled'],
            'pickup': ['picked_up', 'cancelled'],
            'picked_up': ['in_transit'],
            'in_transit': ['delivered'],
            'delivered': ['completed'],
            'completed': [],
            'cancelled': []
        }
        return new in valid_transitions.get(current, [])

class AssignDriverView(APIView):
    """Assign driver to an order"""
    permission_classes = [IsVendor]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(
                id=order_id,
                vendor=request.user,
                status='confirmed',
                is_active=True
            )
            
            serializer = AssignDriverSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            driver = serializer.validated_data['driver_id']
            order.driver = driver
            order.status = 'driver_assigned'
            order.save()
            
            # Update driver availability
            driver.is_available = False
            driver.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                previous_status='confirmed',
                new_status='driver_assigned',
                updated_by=request.user,
                notes=f'Driver {driver.name} assigned to order'
            )
            
            return Response({
                'message': 'Driver assigned successfully',
                'driver_name': driver.name,
                'order_status': 'driver_assigned'
            })
            
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found, not confirmed, or not owned by you'},
                status=status.HTTP_404_NOT_FOUND
            )

# Order Status History
class OrderStatusHistoryView(generics.ListAPIView):
    """Get status history for an order"""
    serializer_class = OrderStatusHistorySerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        order_id = self.kwargs['order_id']
        user = self.request.user
        
        # Verify user has access to this order
        try:
            if user.role == 'customer':
                order = Order.objects.get(id=order_id, customer=user)
            else:  # vendor
                order = Order.objects.get(id=order_id, vendor=user)
        except Order.DoesNotExist:
            return OrderStatusHistory.objects.none()
        
        return OrderStatusHistory.objects.filter(order_id=order_id).order_by('timestamp')

# Delivery Verification
class DeliveryVerificationView(APIView):
    """Verify delivery using OTP (customer)"""
    permission_classes = [IsCustomer]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(
                id=order_id,
                customer=request.user,
                status='delivered',
                is_active=True
            )
            
            serializer = DeliveryVerificationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            data = serializer.validated_data
            
            if order.delivery_otp != data['otp']:
                return Response(
                    {'error': 'Invalid OTP'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark as verified and completed
            order.is_otp_verified = True
            order.status = 'completed'
            if 'actual_weight' in data:
                order.actual_weight = data['actual_weight']
            order.save()
            
            # Update truck and driver availability
            order.truck.availability_status = 'available'
            order.truck.save()
            
            if order.driver:
                order.driver.is_available = True
                order.driver.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                previous_status='delivered',
                new_status='completed',
                updated_by=request.user,
                notes=f"Delivery verified with OTP. {data.get('delivery_notes', '')}"
            )
            
            return Response({
                'message': 'Delivery verified successfully',
                'order_status': 'completed'
            })
            
        except Order.DoesNotExist:
            return Response(
                {'error': 'Order not found or not in delivered status'},
                status=status.HTTP_404_NOT_FOUND
            )

# Document Management
class OrderDocumentListView(generics.ListAPIView):
    """List documents for an order"""
    serializer_class = OrderDocumentSerializer
    permission_classes = [IsCustomerOrVendor]
    
    def get_queryset(self):
        order_id = self.kwargs['order_id']
        user = self.request.user
        
        # Verify user has access to this order
        try:
            if user.role == 'customer':
                order = Order.objects.get(id=order_id, customer=user)
            else:  # vendor
                order = Order.objects.get(id=order_id, vendor=user)
        except Order.DoesNotExist:
            return OrderDocument.objects.none()
        
        return OrderDocument.objects.filter(order_id=order_id).order_by('-uploaded_at')

class OrderDocumentUploadView(generics.CreateAPIView):
    """Upload documents for an order"""
    serializer_class = OrderDocumentUploadSerializer
    permission_classes = [IsCustomerOrVendor]

    def perform_create(self, serializer):
        order = serializer.validated_data['order']
        user = self.request.user
        
        # Verify user has access to this order
        if user.role == 'customer' and order.customer != user:
            raise permissions.PermissionDenied()
        elif user.role == 'vendor' and order.vendor != user:
            raise permissions.PermissionDenied()
        
        serializer.save()
