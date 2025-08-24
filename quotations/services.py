"""
Business logic services for quotations.
Centralizes complex business rules and workflows.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Quotation, QuotationRequest, QuotationNegotiation, QuotationItem
from orders.models import Order, OrderStatusHistory
from .enums import (
    QuotationStatus, NegotiationInitiator, BusinessRules, 
    ErrorMessages, ResponseMessages
)
from .validators import (
    QuotationBusinessValidator, QuotationStatusValidator, 
    BusinessRuleEngine
)

User = get_user_model()


class QuotationService:
    """Service class for quotation-related business logic"""
    
    @staticmethod
    def create_quotation_request_and_quotation(customer, quotation_data):
        """
        Enhanced quotation creation with advanced business rule validation.
        
        Args:
            customer: The customer user instance
            quotation_data: Dict containing all quotation creation data
            
        Returns:
            Dict with quotation_request, quotation, created_new_request, customer_negotiation, warnings
        """
        # Advanced business rule validation
        validation_result = BusinessRuleEngine.validate_quotation_workflow(
            customer, quotation_data
        )
        
        if not validation_result['is_valid']:
            raise ValidationError({
                'business_rules': validation_result['errors']
            })
        
        # Use validated/cleaned data
        cleaned_data = validation_result['data']
        vendor = cleaned_data['vendor_id']
        
        # Extract search parameters for QuotationRequest uniqueness (without urgency_level)
        quotation_request_data = {
            'customer': customer,
            'origin_pincode': cleaned_data['origin_pincode'],
            'destination_pincode': cleaned_data['destination_pincode'],
            'pickup_date': cleaned_data['pickup_date'].date(),
            'drop_date': cleaned_data['drop_date'].date(),
            'weight': Decimal(cleaned_data['weight']),
            'weight_unit': cleaned_data['weight_unit'],
            'vehicle_type': cleaned_data.get('vehicle_type', 'Mixed'),
        }
        
        # Get or create quotation request (based on business rule for uniqueness)
        quotation_request, created = QuotationRequest.objects.get_or_create(
            **quotation_request_data,
            defaults={'is_active': True}
        )
        
        # Validate pricing with business rules
        pricing_valid, pricing_error = QuotationBusinessValidator.validate_quotation_pricing(
            cleaned_data['total_amount'], 
            cleaned_data['items'],  # Pass raw items for validation
            cleaned_data.get('distance_km')
        )
        
        if not pricing_valid:
            raise ValidationError({'pricing': [pricing_error]})
        
        # Create vendor quotation for this request
        quotation = Quotation.objects.create(
            quotation_request=quotation_request,
            vendor=vendor,
            vendor_name=cleaned_data['vendor_name'],
            total_amount=cleaned_data['total_amount'],
            urgency_level=cleaned_data['urgency_level'],
            validity_hours=cleaned_data.get('validity_hours', BusinessRules.DEFAULT_QUOTATION_VALIDITY_HOURS),
            status=QuotationStatus.PENDING
        )
        
        # Create QuotationItem objects for each vehicle item
        quotation_items = QuotationService._create_quotation_items(quotation, cleaned_data['items'])
        
        # Create initial customer negotiation if provided
        customer_negotiation = QuotationService.create_initial_negotiation(
            quotation=quotation,
            customer_proposed_amount=cleaned_data.get('customer_proposed_amount'),
            customer_message=cleaned_data.get('customer_negotiation_message')
        )
        
        # Return with validation warnings if any
        result = {
            'quotation_request': quotation_request,
            'quotation': quotation,
            'quotation_items': quotation_items,
            'created_new_request': created,
            'customer_negotiation': customer_negotiation
        }
        
        if validation_result['warnings']:
            result['warnings'] = validation_result['warnings']
            
        return result

    @staticmethod
    def _create_quotation_items(quotation, items):
        """Create QuotationItem objects from frontend item data"""
        from trucks.models import Truck, TruckType
        
        quotation_items = []
        
        for item in items:
            # Determine if we have a specific truck or just a truck type
            truck = None
            truck_type = None
            
            # Try to find specific truck by ID or registration
            vehicle_id = item.get('vehicle_id')
            if vehicle_id:
                try:
                    # Try to find truck by ID first
                    if str(vehicle_id).isdigit():
                        truck = Truck.objects.get(id=int(vehicle_id), vendor=quotation.vendor)
                    else:
                        # Try to find by registration number
                        truck = Truck.objects.get(registration_number=vehicle_id, vendor=quotation.vendor)
                except Truck.DoesNotExist:
                    truck = None
            
            # If no specific truck found, use truck type
            if not truck:
                vehicle_type = item.get('vehicle_type', '')
                if vehicle_type:
                    try:
                        truck_type = TruckType.objects.get(name__icontains=vehicle_type)
                    except TruckType.DoesNotExist:
                        # Create a generic truck type if it doesn't exist
                        truck_type, created = TruckType.objects.get_or_create(
                            name=vehicle_type,
                            defaults={'description': f'Auto-created truck type: {vehicle_type}'}
                        )
            
            # Parse delivery date
            estimated_delivery = None
            if item.get('estimated_delivery'):
                try:
                    from datetime import datetime
                    if isinstance(item['estimated_delivery'], str):
                        estimated_delivery = datetime.strptime(
                            item['estimated_delivery'].split('T')[0], '%Y-%m-%d'
                        ).date()
                    else:
                        estimated_delivery = item['estimated_delivery']
                except (ValueError, AttributeError):
                    estimated_delivery = None
            
            # Create QuotationItem with only essential data
            quotation_item = QuotationItem.objects.create(
                quotation=quotation,
                truck=truck,
                truck_type=truck_type,
                quantity=item.get('quantity', 1),
                unit_price=item.get('unit_price', item.get('price_per_vehicle', 0)),
                estimated_delivery=estimated_delivery,
                pickup_locations=item.get('pickup_locations', []),
                drop_locations=item.get('drop_locations', []),
                special_instructions=item.get('special_instructions', '')
            )
            quotation_items.append(quotation_item)
            
        return quotation_items

    @staticmethod
    def _transform_vehicle_items(items):
        """
        Legacy method - now returns a simplified list for backwards compatibility.
        The actual data is stored in QuotationItem objects.
        """
        transformed_items = []
        for item in items:
            # Handle both nested vehicle format and direct format from frontend
            if 'vehicle' in item:
                # Legacy nested format
                vehicle_data = item.get('vehicle', {})
                vehicle_type = vehicle_data.get('vehicleType', '')
                capacity = vehicle_data.get('capacity', '')
            else:
                # Frontend direct format
                vehicle_type = item.get('vehicle_type', '')
                capacity = item.get('max_weight', '')
            
            transformed_item = {
                'quantity': item.get('quantity', 1),
                'vehicle': {
                    'vehicleType': vehicle_type,
                    'capacity': capacity,
                    'dimensions': item.get('dimensions', ''),
                    'features': item.get('features', [])
                },
                'vehicle_id': item.get('vehicle_id'),
                'vehicle_model': item.get('vehicle_model', ''),
                'gps_number': item.get('gps_number', ''),
                'estimated_delivery': item.get('estimated_delivery', ''),
                'pickup_locations': item.get('pickup_locations', []),
                'drop_locations': item.get('drop_locations', []),
                'price_per_vehicle': item.get('unit_price', item.get('price_per_vehicle', 0))
            }
            transformed_items.append(transformed_item)
            
        return transformed_items

    @staticmethod
    def create_initial_negotiation(quotation, customer_proposed_amount=None, customer_message=None):
        """
        Enhanced initial negotiation creation with business rule validation.
        If customer proposes different amount, mark quotation as 'negotiating'.
        """
        if customer_proposed_amount:
            # Validate negotiation sequence and amount
            seq_valid, seq_error = QuotationStatusValidator.can_transition_status(
                quotation, quotation.status, QuotationStatus.NEGOTIATING, 'customer'
            )
            if not seq_valid:
                raise ValidationError({'negotiation': [seq_error]})
            
            amount_valid, amount_error = QuotationBusinessValidator.validate_negotiation_amount_advanced(
                quotation, customer_proposed_amount, 'customer'
            )
            if not amount_valid:
                raise ValidationError({'amount': [amount_error]})
            
            # Customer has provided a different proposed amount
            negotiation_amount = customer_proposed_amount
            negotiation_message = customer_message or 'Customer price proposal'
            quotation.status = QuotationStatus.NEGOTIATING
        else:
            # Customer is requesting the vendor's price, create initial negotiation with vendor's amount
            negotiation_amount = quotation.total_amount
            negotiation_message = f'Initial quotation request for {quotation.vendor_name} vehicles'
        
        # Create the initial customer negotiation instance
        customer_negotiation = QuotationNegotiation.objects.create(
            quotation=quotation,
            initiated_by=NegotiationInitiator.CUSTOMER,
            proposed_amount=negotiation_amount,
            message=negotiation_message
        )
        
        # Save quotation with updated status
        quotation.save()
        
        return customer_negotiation


class NegotiationService:
    """Enhanced negotiation service with advanced business logic"""
    
    @staticmethod
    def can_negotiate(quotation, user_role):
        """
        Enhanced negotiation eligibility check with business rules.
        """
        # Check if quotation is in negotiable state
        if quotation.status not in [QuotationStatus.PENDING, QuotationStatus.SENT, QuotationStatus.NEGOTIATING]:
            return False, ErrorMessages.QUOTATION_NOT_NEGOTIABLE
        
        # Check expiry
        if QuotationStatusValidator.validate_quotation_expiry(quotation):
            return False, ErrorMessages.QUOTATION_EXPIRED
        
        # Advanced negotiation sequence validation
        seq_valid, seq_error = QuotationBusinessValidator.validate_negotiation_sequence(
            quotation, user_role
        )
        if not seq_valid:
            return False, seq_error
        
        return True, None

    @staticmethod
    def create_negotiation(quotation, user_role, proposed_amount, message=""):
        """
        Enhanced negotiation creation with advanced validation.
        """
        # Check if user can negotiate
        can_negotiate, error = NegotiationService.can_negotiate(quotation, user_role)
        if not can_negotiate:
            raise ValidationError({'negotiation': [error]})
        
        # Advanced amount validation
        amount_valid, amount_error = QuotationBusinessValidator.validate_negotiation_amount_advanced(
            quotation, proposed_amount, user_role
        )
        if not amount_valid:
            raise ValidationError({'amount': [amount_error]})
        
        # Determine initiator based on role
        if user_role == 'customer':
            initiated_by = NegotiationInitiator.CUSTOMER
        elif user_role == 'vendor':
            initiated_by = NegotiationInitiator.VENDOR
        else:
            raise ValidationError({'role': ['Invalid user role for negotiation']})
        
        # Create negotiation
        negotiation = QuotationNegotiation.objects.create(
            quotation=quotation,
            initiated_by=initiated_by,
            proposed_amount=proposed_amount,
            message=message
        )
        
        # Update quotation status
        quotation.status = QuotationStatus.NEGOTIATING
        quotation.save()
        
        return negotiation


class QuotationStatusService:
    """Enhanced status management service"""
    
    @staticmethod
    def update_status(quotation, new_status, user_role, notes=""):
        """
        Enhanced status update with business rule validation.
        """
        # Validate transition
        transition_valid, transition_error = QuotationStatusValidator.can_transition_status(
            quotation, quotation.status, new_status, user_role
        )
        if not transition_valid:
            raise ValidationError({'transition': [transition_error]})
        
        old_status = quotation.status
        quotation.status = new_status
        quotation.save()
        
        # Log status change (could be expanded to create audit trail)
        return {
            'old_status': old_status,
            'new_status': new_status,
            'changed_by_role': user_role,
            'notes': notes
        }

    @staticmethod
    def expire_quotations():
        """
        Enhanced batch expiry process with business logic.
        Returns count of expired quotations.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Find quotations that should be expired
        cutoff_time = timezone.now()
        
        expired_quotations = Quotation.objects.filter(
            status__in=[QuotationStatus.PENDING, QuotationStatus.SENT, QuotationStatus.NEGOTIATING],
            created_at__lt=cutoff_time
        )
        
        expired_count = 0
        for quotation in expired_quotations:
            # Check individual expiry based on validity_hours
            expiry_time = quotation.created_at + timedelta(hours=quotation.validity_hours)
            if timezone.now() > expiry_time:
                quotation.status = QuotationStatus.EXPIRED
                quotation.save()
                expired_count += 1
        
        return expired_count

    @staticmethod
    def accept_negotiation(negotiation, user):
        """
        Accept a negotiation and create an order using the new OrderCreationService.
        
        Args:
            negotiation: QuotationNegotiation instance to accept
            user: User accepting the negotiation (should be customer)
            
        Returns:
            Dict containing order creation results
        """
        from orders.services import OrderCreationService

        # Validate that user or vendor can accept this negotiation
        if negotiation.quotation.quotation_request.customer == user or negotiation.quotation.vendor == user:
            pass
        else:
            raise ValidationError("You can only accept negotiations for your own quotations")

        # Create order using the new centralized service
        order_result = OrderCreationService.create_order_from_negotiation(
            negotiation=negotiation,
            user=user
        )

        # Update quotation status to accepted
        quotation = negotiation.quotation
        quotation.status = QuotationStatus.ACCEPTED
        quotation.save()
        
        return {
            'success': True,
            'message': 'Negotiation accepted and order created successfully',
            'negotiation': negotiation,
            'order': order_result['order'],
            'order_metadata': order_result
        }

    @staticmethod
    def get_quotation_analytics(quotation):
        """
        Enhanced analytics for quotation performance.
        """
        from django.utils import timezone
        
        negotiations = quotation.negotiations.all()
        
        return {
            'total_negotiations': negotiations.count(),
            'customer_negotiations': negotiations.filter(initiated_by=NegotiationInitiator.CUSTOMER).count(),
            'vendor_negotiations': negotiations.filter(initiated_by=NegotiationInitiator.VENDOR).count(),
            'original_amount': quotation.total_amount,
            'latest_negotiated_amount': negotiations.last().proposed_amount if negotiations.exists() else quotation.total_amount,
            'negotiation_trend': 'decreasing' if negotiations.exists() and negotiations.last().proposed_amount < quotation.total_amount else 'stable',
            'is_expired': QuotationStatusValidator.validate_quotation_expiry(quotation),
            'status': quotation.status,
            'validity_remaining_hours': max(0, quotation.validity_hours - ((timezone.now() - quotation.created_at).total_seconds() / 3600))
        }
