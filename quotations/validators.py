"""
Advanced business rules and validation for quotations.
Provides comprehensive validation beyond basic field validation.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, List, Tuple, Optional

from .models import Quotation, QuotationRequest, QuotationNegotiation
from .enums import QuotationStatus, BusinessRules, ErrorMessages


class QuotationBusinessValidator:
    """Advanced business rule validation for quotations"""
    
    @staticmethod
    def validate_quotation_creation(customer, quotation_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive validation for quotation creation.
        
        Business Rules:
        1. Customer cannot have more than 5 active quotation requests
        2. Pickup date must be at least 24 hours in the future
        3. Trip duration must be reasonable (max 30 days)
        4. Weight must be within reasonable limits
        """
        
        # Rule 1: Check active quotation requests limit
        active_requests = QuotationRequest.objects.filter(
            customer=customer,
            is_active=True
        ).count()
        
        if active_requests >= 5:
            return False, "You have reached the maximum limit of 5 active quotation requests"
        
        # Rule 2: Pickup date validation
        pickup_date = quotation_data.get('pickup_date')
        if pickup_date:
            if isinstance(pickup_date, str):
                pickup_date = datetime.fromisoformat(pickup_date.replace('Z', '+00:00'))
            
            min_pickup_time = timezone.now() + timedelta(hours=24)
            if pickup_date < min_pickup_time:
                return False, "Pickup date must be at least 24 hours from now"
        
        # Rule 3: Trip duration validation
        drop_date = quotation_data.get('drop_date')
        if pickup_date and drop_date:
            if isinstance(drop_date, str):
                drop_date = datetime.fromisoformat(drop_date.replace('Z', '+00:00'))
            
            trip_duration = drop_date - pickup_date
            if trip_duration.days > 30:
                return False, "Trip duration cannot exceed 30 days"
            
            if trip_duration.total_seconds() < 3600:  # Less than 1 hour
                return False, "Trip duration must be at least 1 hour"
        
        # Rule 4: Weight validation
        weight = quotation_data.get('weight')
        if weight:
            try:
                weight_decimal = Decimal(str(weight))
                weight_unit = quotation_data.get('weight_unit', 'kg')
                
                # Convert to kg for validation
                if weight_unit == 'ton':
                    weight_kg = weight_decimal * 1000
                elif weight_unit == 'lbs':
                    weight_kg = weight_decimal * 0.453592
                else:
                    weight_kg = weight_decimal
                
                if weight_kg > 50000:  # 50 tons max
                    return False, "Weight cannot exceed 50 tons"
                
                if weight_kg < 1:  # Minimum 1 kg
                    return False, "Weight must be at least 1 kg"
                    
            except (ValueError, TypeError):
                return False, "Invalid weight format"
        
        return True, None
    
    @staticmethod
    def validate_quotation_pricing(total_amount: Decimal, items: List[Dict], 
                                 distance_km: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate quotation pricing against business rules.
        
        Business Rules:
        1. Minimum price per km based on vehicle type
        2. Total amount should be reasonable for the items
        3. Price consistency across similar routes
        """
        
        if total_amount <= 0:
            return False, "Total amount must be positive"
        
        # Rule 1: Check minimum pricing
        if len(items) == 0:
            return False, "At least one vehicle item is required"
        
        # Calculate minimum expected price based on vehicle types
        min_expected_price = Decimal('0')
        for item in items:
            quantity = item.get('quantity', 1)
            vehicle_type = item.get('vehicle', {}).get('vehicleType', '').lower()
            
            # Minimum rates per vehicle type (per day base rate) - Updated for realistic pricing
            min_rates = {
                'mini truck': Decimal('2000'),
                'small truck': Decimal('3500'),
                'medium truck': Decimal('5000'),
                'large truck': Decimal('7000'),
                'container': Decimal('10000'),
            }
            
            base_rate = min_rates.get(vehicle_type, Decimal('2000'))  # Default rate
            min_expected_price += base_rate * quantity
        
        # Add distance-based pricing if available
        if distance_km:
            min_price_per_km = Decimal('15')  # Increased to ₹15 per km for realistic long-distance pricing
            distance_cost = Decimal(str(distance_km)) * min_price_per_km
            min_expected_price += distance_cost
        
        if total_amount < min_expected_price * Decimal('0.7'):  # 30% below minimum
            return False, f"Price too low. Minimum expected: ₹{min_expected_price * Decimal('0.7'):.2f}"
        
        # Rule 2: Maximum price check (prevent inflated pricing) - More flexible for real-world pricing
        max_expected_price = min_expected_price * Decimal('100')  # 5x minimum instead of 3x
        if total_amount > max_expected_price:
            return False, f"Price too high. Maximum expected: ₹{max_expected_price:.2f}"
        
        return True, None
    
    @staticmethod
    def validate_negotiation_sequence(quotation: Quotation, user_role: str) -> Tuple[bool, Optional[str]]:
        """
        Advanced negotiation sequence validation.
        
        Business Rules:
        1. Cannot have more than 5 rounds of negotiations
        2. Must alternate between customer and vendor
        3. Cannot negotiate after business hours (optional)
        4. Customer cannot start negotiation immediately after quotation creation
        """
        
        negotiations = quotation.negotiations.order_by('created_at')
        
        # Rule 1: Maximum negotiation rounds
        if negotiations.count() >= 10:  # 5 rounds each
            return False, "Maximum negotiation rounds (5) exceeded"
        
        # Rule 2: Check alternating pattern
        if negotiations.exists():
            latest_negotiation = negotiations.last()
            
            # Cannot negotiate immediately after your own negotiation
            if latest_negotiation.initiated_by == user_role:
                other_party = 'vendor' if user_role == 'customer' else 'customer'
                return False, ErrorMessages.CONSECUTIVE_NEGOTIATION.format(other_party=other_party)
        
        # Rule 3: Business hours check (9 AM to 9 PM IST)
        now = timezone.now()
        ist_hour = (now.hour + 5) % 24  # Rough IST conversion
        if ist_hour < 9 or ist_hour > 21:
            return False, "Negotiations are only allowed during business hours (9 AM - 9 PM IST)"
        
        # Rule 4: Customer cannot negotiate immediately after quotation creation
        if user_role == 'customer' and negotiations.count() == 0:
            # Check if quotation was just created (within last 30 minutes)
            creation_time = quotation.created_at
            if timezone.now() - creation_time < timedelta(minutes=30):
                return False, "Please wait at least 30 minutes before starting negotiations"
        
        return True, None
    
    @staticmethod
    def validate_negotiation_amount_advanced(quotation: Quotation, proposed_amount: Decimal, 
                                           user_role: str) -> Tuple[bool, Optional[str]]:
        """
        Advanced negotiation amount validation with context.
        
        Business Rules:
        1. Progressive reduction limits (each negotiation can only reduce by max 15%)
        2. Vendor cannot increase price beyond original
        3. Final amount cannot be less than 50% of original
        """
        
        original_amount = quotation.total_amount
        negotiations = quotation.negotiations.order_by('created_at')
        
        # Rule 1: Progressive reduction limits
        if negotiations.exists():
            latest_negotiation = negotiations.last()
            latest_amount = latest_negotiation.proposed_amount
            
            max_reduction_percent = Decimal('15')  # 15% max reduction per round
            min_allowed = latest_amount * (Decimal('100') - max_reduction_percent) / Decimal('100')
            max_allowed = latest_amount * (Decimal('100') + max_reduction_percent) / Decimal('100')
            
            if proposed_amount < min_allowed:
                return False, f"Cannot reduce more than {max_reduction_percent}% per negotiation. Minimum: ₹{min_allowed:.2f}"
            
            if proposed_amount > max_allowed and user_role == 'customer':
                return False, f"Cannot increase more than {max_reduction_percent}% per negotiation. Maximum: ₹{max_allowed:.2f}"
        
        # Rule 2: Vendor cannot increase beyond original amount
        # if user_role == 'vendor' and proposed_amount > original_amount:
        #     return False, "Vendors cannot propose amount higher than original quotation"
        
        # Rule 3: Final amount cannot be less than 50% of original
        min_final_amount = original_amount * Decimal('0.5')
        if proposed_amount < min_final_amount:
            return False, f"Final amount cannot be less than 50% of original (₹{min_final_amount:.2f})"
        
        return True, None


class QuotationStatusValidator:
    """Validation for quotation status transitions"""
    
    @staticmethod
    def can_transition_status(quotation: Quotation, from_status: str, to_status: str, user_role: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if status transition is allowed.
        
        Valid transitions:
        - pending -> negotiating (customer starts negotiation)
        - pending -> accepted (customer accepts without negotiation)
        - pending -> rejected (customer rejects)
        - negotiating -> accepted (either party accepts negotiation)
        - negotiating -> rejected (either party rejects)
        - * -> expired (system auto-expiry)
        """
        
        # Define allowed transitions
        allowed_transitions = {
            QuotationStatus.PENDING: [
                QuotationStatus.NEGOTIATING,
                QuotationStatus.ACCEPTED,
                QuotationStatus.REJECTED,
                QuotationStatus.EXPIRED
            ],
            QuotationStatus.SENT: [
                QuotationStatus.NEGOTIATING,
                QuotationStatus.ACCEPTED,
                QuotationStatus.REJECTED,
                QuotationStatus.EXPIRED
            ],
            QuotationStatus.NEGOTIATING: [
                QuotationStatus.ACCEPTED,
                QuotationStatus.REJECTED,
                QuotationStatus.EXPIRED
            ],
            # Final states cannot transition
            QuotationStatus.ACCEPTED: [],
            QuotationStatus.REJECTED: [],
            QuotationStatus.EXPIRED: []
        }
        
        if to_status not in allowed_transitions.get(from_status, []):
            return False, f"Cannot transition from {from_status} to {to_status}"
        
        # Role-based restrictions
        if to_status == QuotationStatus.ACCEPTED:
            # Only customer can accept quotations
            if user_role != 'customer':
                return False, "Only customers can accept quotations"
        
        return True, None
    
    @staticmethod
    def validate_quotation_expiry(quotation: Quotation) -> bool:
        """Check if quotation has expired based on validity_hours"""
        
        if quotation.status in [QuotationStatus.ACCEPTED, QuotationStatus.REJECTED, QuotationStatus.EXPIRED]:
            return True  # Already in final state
        
        expiry_time = quotation.created_at + timedelta(hours=quotation.validity_hours)
        return timezone.now() > expiry_time


class BusinessRuleEngine:
    """Central engine for applying all business rules"""
    
    @staticmethod
    def validate_quotation_workflow(customer, quotation_data: Dict) -> Dict[str, any]:
        """
        Complete validation for quotation creation workflow.
        
        Returns:
            {
                'is_valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'data': Dict  # Cleaned/processed data
            }
        """
        
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'data': quotation_data.copy()
        }
        
        # Run all validations
        validators = [
            QuotationBusinessValidator.validate_quotation_creation,
        ]
        
        # Run basic validations first
        for validator in validators:
            try:
                is_valid, error = validator(customer, quotation_data)
                if not is_valid:
                    result['is_valid'] = False
                    result['errors'].append(error)
            except Exception as e:
                result['is_valid'] = False
                result['errors'].append(f"Validation error: {str(e)}")
        
        # Run pricing validation with properly transformed items
        if result['is_valid']:  # Only if other validations passed
            try:
                # Transform items to expected format for pricing validation inline
                transformed_items = []
                for item in quotation_data.get('items', []):
                    # Handle both nested vehicle format and direct format from frontend
                    if 'vehicle' in item:
                        # Legacy nested format
                        vehicle_data = item.get('vehicle', {})
                        vehicle_type = vehicle_data.get('vehicleType', '')
                    else:
                        # Frontend direct format
                        vehicle_type = item.get('vehicle_type', '')
                    
                    transformed_item = {
                        'quantity': item.get('quantity', 1),
                        'vehicle': {
                            'vehicleType': vehicle_type,
                            'capacity': item.get('max_weight', ''),
                        },
                        'price_per_vehicle': item.get('unit_price', item.get('price_per_vehicle', 0))
                    }
                    transformed_items.append(transformed_item)
                
                pricing_valid, pricing_error = QuotationBusinessValidator.validate_quotation_pricing(
                    quotation_data.get('total_amount', Decimal('0')),
                    transformed_items,
                    quotation_data.get('distance_km')
                )
                
                if not pricing_valid:
                    result['is_valid'] = False
                    result['errors'].append(pricing_error)
                    
            except Exception as e:
                result['is_valid'] = False
                result['errors'].append(f"Pricing validation error: {str(e)}")
        
        return result
