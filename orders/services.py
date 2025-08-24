"""
Order Management Services
Centralized business logic for order creation, status management, and lifecycle tracking.
"""
import random
import string
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Order, OrderStatusHistory, OrderDocument
from quotations.models import Quotation, QuotationNegotiation
from trucks.models import Truck, Driver
from project.utils import success_response, error_response

User = get_user_model()


class OrderCreationService:
    """
    Centralized service for creating orders from quotations.
    Handles automatic OrderStatusHistory creation and business validation.
    """
    
    @staticmethod
    @transaction.atomic
    def create_order_from_quotation(quotation: Quotation, user: User, **kwargs) -> Dict[str, Any]:
        """
        Create an order from an accepted quotation with automatic status tracking.
        
        Args:
            quotation: The accepted quotation
            user: The user creating the order (should be customer)
            **kwargs: Additional order data (delivery_instructions, special_instructions, etc.)
            
        Returns:
            Dict containing order instance and metadata
            
        Raises:
            ValidationError: If business rules are violated
        """
        # Business rule validation
        OrderCreationService._validate_order_creation(quotation, user)
        
        # Extract quotation request data
        quotation_request = quotation.quotation_request
        
        # Generate delivery OTP
        delivery_otp = OrderCreationService._generate_delivery_otp()
        
        # Create order instance
        order = Order.objects.create(
            quotation=quotation,
            customer=quotation_request.customer,
            vendor=quotation.vendor,
            truck=None,  # Truck will be assigned later during status updates
            
            # Location data from quotation request - ensure non-empty values
            pickup_address=quotation_request.pickup_address or f"Pickup location - Pincode: {quotation_request.origin_pincode}",
            delivery_address=quotation_request.delivery_address or f"Delivery location - Pincode: {quotation_request.destination_pincode}",
            pickup_latitude=quotation_request.pickup_latitude or Decimal('0.0'),
            pickup_longitude=quotation_request.pickup_longitude or Decimal('0.0'),
            delivery_latitude=quotation_request.delivery_latitude or Decimal('0.0'),
            delivery_longitude=quotation_request.delivery_longitude or Decimal('0.0'),
            
            # Scheduling - ensure datetime objects
            scheduled_pickup_date=OrderCreationService._ensure_datetime(quotation_request.pickup_date),
            scheduled_delivery_date=OrderCreationService._ensure_datetime(quotation_request.drop_date),
            
            # Financial data
            total_amount=quotation.total_amount,
            
            # Cargo details - ensure non-empty values
            cargo_description=quotation.cargo_description or quotation_request.vehicle_type or "Cargo transportation",
            estimated_weight=quotation_request.weight or Decimal('0.0'),
            
            # Instructions
            special_instructions=kwargs.get('special_instructions', ''),
            delivery_instructions=kwargs.get('delivery_instructions', ''),
            
            # OTP verification
            delivery_otp=delivery_otp,
            is_otp_verified=False,
            
            # Status
            status='created'
        )
        
        # Create initial status history entry
        OrderStatusTrackingService.create_status_entry(
            order=order,
            new_status='created',
            updated_by=user,
            notes='Order created from accepted quotation',
            auto_generated=True
        )
        
        # Update truck availability if truck is assigned
        if order.truck:
            OrderCreationService._update_truck_availability(order.truck, 'busy')
            truck_updated = True
        else:
            truck_updated = False
        
        # Mark quotation as converted to order
        quotation.save()  # Ensure any status updates are saved
        
        return {
            'order': order,
            'delivery_otp': delivery_otp,
            'truck_updated': truck_updated,
            'status_history_created': True
        }
    
    @staticmethod
    @transaction.atomic
    def create_order_from_negotiation(negotiation: QuotationNegotiation, user: User) -> Dict[str, Any]:
        """
        Create an order from an accepted negotiation with the final negotiated amount.
        
        Args:
            negotiation: The accepted negotiation
            user: The user accepting the negotiation
            
        Returns:
            Dict containing order and acceptance details
        """
        quotation = negotiation.quotation
        
        # Update quotation with negotiated amount
        original_amount = quotation.total_amount
        quotation.total_amount = negotiation.proposed_amount
        quotation.status = 'accepted'
        quotation.save()
        
        # Create order from updated quotation
        order_result = OrderCreationService.create_order_from_quotation(
            quotation=quotation,
            user=user,
            special_instructions=f"Negotiated from ₹{original_amount} to ₹{negotiation.proposed_amount}"
        )
        
        # Add negotiation-specific metadata
        order_result.update({
            'negotiation_id': negotiation.id,
            'original_amount': original_amount,
            'final_amount': negotiation.proposed_amount,
            'savings': original_amount - negotiation.proposed_amount,
            'negotiation_accepted': True
        })
        
        return order_result
    
    @staticmethod
    def _validate_order_creation(quotation: Quotation, user: User) -> None:
        """Validate business rules for order creation."""
        # Check if user is the customer for this quotation or vendor
        if quotation.quotation_request.customer == user or quotation.vendor == user:
            pass
        else:
            raise ValidationError("You can only create orders for your own quotations")
        
        # Check if quotation is in acceptable state
        if quotation.status not in ['accepted', 'negotiating']:
            raise ValidationError(f"Cannot create order from quotation with status: {quotation.status}")
        
        # Check if order already exists
        if hasattr(quotation, 'order'):
            raise ValidationError("Order already exists for this quotation")
        
        # Check quotation expiry
        if quotation.created_at:
            expiry_time = quotation.created_at + timezone.timedelta(hours=quotation.validity_hours)
            if timezone.now() > expiry_time:
                raise ValidationError("Quotation has expired")
    
    @staticmethod
    def _generate_delivery_otp() -> str:
        """Generate a 6-digit delivery OTP."""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def _update_truck_availability(truck: Truck, status: str) -> None:
        """Update truck availability status."""
        truck.availability_status = status
        truck.save()
    
    @staticmethod
    def _ensure_datetime(date_value):
        """Convert date to datetime if needed."""
        if hasattr(date_value, 'hour'):
            # Already a datetime
            return date_value
        else:
            # Convert date to datetime
            import datetime
            return timezone.make_aware(
                datetime.datetime.combine(date_value, datetime.time(9, 0))  # Default to 9 AM
            )


class OrderStatusTrackingService:
    """
    Centralized service for managing order status transitions and automatic history tracking.
    """
    
    # Define valid status transitions
    VALID_TRANSITIONS = {
        'created': ['confirmed', 'cancelled'],
        'confirmed': ['driver_assigned', 'cancelled'],
        'driver_assigned': ['pickup', 'cancelled'],
        'pickup': ['picked_up', 'cancelled'],
        'picked_up': ['in_transit'],
        'in_transit': ['delivered'],
        'delivered': ['completed'],
        'completed': [],  # Final state
        'cancelled': []   # Final state
    }
    
    @staticmethod
    @transaction.atomic
    def update_order_status(
        order: Order, 
        new_status: str, 
        updated_by: User, 
        notes: str = "",
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        auto_generated: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update order status with automatic validation and history tracking.
        
        Args:
            order: Order instance to update
            new_status: New status to transition to
            updated_by: User making the change
            notes: Optional notes about the status change
            latitude/longitude: Optional location data
            auto_generated: Whether this is an automatic system update
            **kwargs: Additional context (driver_id, actual_weight, etc.)
            
        Returns:
            Dict containing update results and metadata
        """
        # Validate status transition
        OrderStatusTrackingService._validate_status_transition(order, new_status, updated_by)
        
        # Store previous status
        previous_status = order.status
        
        # Update order status
        order.status = new_status
        
        # Handle status-specific business logic
        status_context = OrderStatusTrackingService._handle_status_specific_logic(
            order, new_status, updated_by, **kwargs
        )
        
        # Save order changes
        order.save()
        
        # Create status history entry
        status_history = OrderStatusTrackingService.create_status_entry(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            updated_by=updated_by,
            notes=notes,
            latitude=latitude,
            longitude=longitude,
            auto_generated=auto_generated
        )
        
        return {
            'order': order,
            'previous_status': previous_status,
            'new_status': new_status,
            'status_history': status_history,
            'context': status_context,
            'transition_valid': True
        }
    
    @staticmethod
    def create_status_entry(
        order: Order,
        new_status: str,
        updated_by: User,
        previous_status: str = "",
        notes: str = "",
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        auto_generated: bool = False
    ) -> OrderStatusHistory:
        """
        Create an OrderStatusHistory entry.
        
        This is the centralized method for ALL status history creation.
        """
        return OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=new_status,
            updated_by=updated_by,
            notes=notes or (f"Status automatically updated to {new_status}" if auto_generated else f"Status updated to {new_status}"),
            location_latitude=latitude,
            location_longitude=longitude,
            timestamp=timezone.now()
        )
    
    @staticmethod
    def _validate_status_transition(order: Order, new_status: str, user: User) -> None:
        """Validate if the status transition is allowed."""
        current_status = order.status
        
        # Check if transition is valid
        valid_next_statuses = OrderStatusTrackingService.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next_statuses:
            raise ValidationError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
                f"Valid transitions: {valid_next_statuses}"
            )
        
        # Role-based validation
        OrderStatusTrackingService._validate_user_permissions(order, new_status, user)
    
    @staticmethod
    def _validate_user_permissions(order: Order, new_status: str, user: User) -> None:
        """Validate user permissions for specific status changes."""
        user_role = user.role
        
        # Define role-based permissions for status changes
        role_permissions = {
            'customer': ['cancelled'],  # Customers can only cancel
            'vendor': ['confirmed', 'driver_assigned', 'pickup', 'picked_up', 'in_transit', 'delivered', 'cancelled'],
            'driver': ['pickup', 'picked_up', 'in_transit', 'delivered'],
            'manager': ['confirmed', 'cancelled'],  # Managers can confirm or cancel
            'admin': list(OrderStatusTrackingService.VALID_TRANSITIONS.keys())  # Admins can do anything
        }
        
        allowed_statuses = role_permissions.get(user_role, [])
        if new_status not in allowed_statuses:
            raise ValidationError(f"User role '{user_role}' cannot set status to '{new_status}'")
        
        # Additional ownership validation
        if user_role == 'customer' and order.customer != user:
            raise ValidationError("You can only modify your own orders")
        elif user_role == 'vendor' and order.vendor != user:
            raise ValidationError("You can only modify orders for your trucks")
    
    @staticmethod
    def _handle_status_specific_logic(order: Order, new_status: str, user: User, **kwargs) -> Dict[str, Any]:
        """Handle business logic specific to each status."""
        context = {}
        
        if new_status == 'driver_assigned':
            # Assign driver if provided
            driver_id = kwargs.get('driver_id')
            if driver_id:
                try:
                    driver = Driver.objects.get(id=driver_id, vendor=order.vendor)
                    order.driver = driver
                    context['driver_assigned'] = driver.name
                except Driver.DoesNotExist:
                    raise ValidationError("Invalid driver ID or driver not owned by vendor")
        
        elif new_status == 'delivered':
            # Set actual delivery date
            order.actual_delivery_date = timezone.now()
            context['delivered_at'] = order.actual_delivery_date
            
            # Update actual weight if provided
            actual_weight = kwargs.get('actual_weight')
            if actual_weight:
                order.actual_weight = actual_weight
                context['actual_weight'] = actual_weight
        
        elif new_status == 'picked_up':
            # Set actual pickup date
            order.actual_pickup_date = timezone.now()
            context['picked_up_at'] = order.actual_pickup_date
        
        elif new_status == 'completed':
            # Mark order as completed and free up truck
            if order.truck:
                OrderCreationService._update_truck_availability(order.truck, 'available')
                context['truck_freed'] = True
            
            # Mark OTP as verified if delivery was successful
            order.is_otp_verified = True
            context['otp_verified'] = True
        
        elif new_status == 'cancelled':
            # Free up truck if order is cancelled
            if order.truck:
                OrderCreationService._update_truck_availability(order.truck, 'available')
                context['truck_freed'] = True
        
        return context


class OrderDocumentService:
    """Service for managing order-related documents."""
    
    @staticmethod
    def add_document(
        order: Order, 
        document_type: str, 
        file, 
        uploaded_by: User, 
        description: str = ""
    ) -> OrderDocument:
        """Add a document to an order with automatic tracking."""
        document = OrderDocument.objects.create(
            order=order,
            document_type=document_type,
            file=file,
            description=description,
            uploaded_by=uploaded_by
        )
        
        # Create status entry for document upload
        OrderStatusTrackingService.create_status_entry(
            order=order,
            new_status=order.status,  # Keep same status
            updated_by=uploaded_by,
            notes=f"Document uploaded: {document_type} - {description}",
            auto_generated=True
        )
        
        return document


class OrderAnalyticsService:
    """Service for order analytics and reporting."""
    
    @staticmethod
    def get_order_analytics(order: Order) -> Dict[str, Any]:
        """Get comprehensive analytics for an order."""
        status_history = order.status_history.all().order_by('timestamp')
        
        return {
            'order_id': order.id,
            'order_number': order.order_number,
            'current_status': order.status,
            'total_status_changes': status_history.count(),
            'status_timeline': [
                {
                    'status': entry.new_status,
                    'timestamp': entry.timestamp,
                    'updated_by': entry.updated_by.name,
                    'notes': entry.notes
                }
                for entry in status_history
            ],
            'is_completed': order.status == 'completed',
            'is_active': order.is_active,
            'documents_count': order.documents.count(),
            'estimated_vs_actual': {
                'pickup_scheduled': order.scheduled_pickup_date,
                'pickup_actual': order.actual_pickup_date,
                'delivery_scheduled': order.scheduled_delivery_date,
                'delivery_actual': order.actual_delivery_date,
                'weight_estimated': order.estimated_weight,
                'weight_actual': order.actual_weight
            }
        }
